"""
The core FraudLens endpoint: submit a suspicious message, get back a
registry-verified, explained result.

AI INTEGRATION POINT: this router currently only runs the registry
check (entity_matcher.py) - deterministic, always available, no
external dependency. The AI pattern-match layer (analyzing message
text for scam language, separate from the sender-name registry check)
is intentionally not wired in yet. See the AI HOOK comment below for
exactly where it plugs in once ready - the Check model, schema, and
verdict logic are already built to accept it (ai_risk_score, ai_flags,
ai_explanation, explanation_source), so wiring it in later should not
require changing this router's structure, only filling in one section.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas, security
from app.entity_matcher import match_entity
from app.verdict import derive_verdict
from app.checks_rate_limit import check_and_record_check_call, MAX_CHECKS_PER_WINDOW, WINDOW_MINUTES
from app.pii_scrubber import scrub_message
from app.indicator_extractor import extract_indicators
from app.domain_analyzer import analyze_domain
from app.phone_analyzer import analyze_phone
from app.url_fetcher import fetch_url_text, UnsafeUrlError, FetchError
from app.ocr import extract_text_from_image, InvalidImageError
from app.repeat_sender import build_repeat_sender_summary
from app.event_bus import bus

router = APIRouter(prefix="/checks", tags=["checks"])


def _attach_repeat_sender_summary(db: Session, check: models.Check) -> models.Check:
    """
    Computed fresh on every read/creation rather than stored on the
    Check row — a summary computed at creation time would go stale the
    moment a LATER check against the same sender is submitted, since
    it needs to reflect all history up to "now", not just history that
    existed at the moment this particular check was created. Attached
    as a transient (non-persisted) attribute, matching CheckOut's
    repeat_sender_summary field, which Pydantic reads via
    from_attributes.
    """
    check.repeat_sender_summary = build_repeat_sender_summary(
        db, check.user_id, check.claimed_sender, exclude_check_id=check.id
    )
    return check


REGISTRY_EXPLANATIONS = {
    "verified": "The sender you named matches an entity in the Bank of Mauritius registry snapshot used by FraudLens.",
    "not_found": "The sender you named was not found in the Bank of Mauritius registry snapshot used by FraudLens (banks and other regulated financial participants). This does not prove the sender doesn't exist anywhere, many legitimate senders such as courier services, retailers, or individuals are not financial institutions and wouldn't be expected to appear in this registry. But if this message claims to be from a bank or financial institution, that specific claim could not be confirmed against the registry snapshot.",
    "no_sender_given": "No sender name was provided, so no registry check could be performed.",
    "registry_unavailable": "The financial institution registry snapshot has not been loaded yet, so this check could not be completed. Contact an administrator.",
}


def _build_revoked_explanation(matched_entity: str, status_detail: str) -> str:
    """
    A distinct, more specific explanation than either "verified" or
    "not_found": this claimed sender exactly matches a real entity's
    name, but that entity's license is no longer active. This is a
    genuinely different, more useful fact than a generic not_found —
    the entity WAS real, and that specific status (surrendered,
    revoked, with the sourced detail) is worth stating plainly rather
    than discarding.
    """
    return (
        f"The sender you named exactly matches \"{matched_entity}\" in the registry snapshot, "
        f"but this entity's license status is recorded as: {status_detail}. A message claiming "
        f"to be from an entity whose license is no longer active is a real reason for caution, "
        f"even though the name itself is genuine rather than fabricated."
    )


def _build_name_mismatch_explanation(matched_entity: str) -> str:
    """
    Unlike the other statuses, name_mismatch explanations must name
    the specific real entity the claimed sender resembles, that's the
    actionable detail this feature exists to provide. A generic
    template here would silently discard the one fact ("this looks
    like an impersonation of X") that makes the result useful, even
    though registry_matched_entity is already stored on the Check
    record, the explanation text itself needs to say it too, since
    that's what's actually shown to the user.

    Phrased as "potential impersonation" rather than a confirmed
    impersonation attempt: a close name match is evidence worth
    flagging, not proof of intent. Overstating what a fuzzy string
    match can actually establish would make this feature LESS
    defensible under scrutiny, not more, which cuts directly against
    its whole "fact, not a guess" premise.
    """
    return (
        f"The sender you named closely resembles \"{matched_entity}\", an entity in the "
        f"Bank of Mauritius registry snapshot, but does not exactly match it. This is a "
        f"potential impersonation pattern: a name that looks almost right is a common "
        f"tactic used in real cases Mauritius has seen, such as Bank of Mauritius's 2026 "
        f"alert about a fake 'digital bank' using a near-identical name to a real one. A "
        f"close name match is evidence worth treating with caution, not proof of intent."
    )


_INDICATOR_DESCRIPTIONS = {
    "requests_otp": "asks you to send or enter a one-time password or verification code",
    "requests_card_details": "asks for card details such as a card number or CVV",
    "urgency": "uses urgent language (e.g. an account suspension deadline) to pressure a quick response",
    "payment_request": "asks you to send money or make a payment",
    "investment_promise": "promises guaranteed or unusually high investment returns",
    "contains_url": "contains a link",
}


def _build_indicator_summary(indicators) -> str:
    """
    Turns the deterministic indicator flags into a short, plain-language
    sentence appended to the registry explanation — this is what makes
    the indicator signal visible to the user, rather than only silently
    affecting the numeric verdict. Returns an empty string if nothing
    was found, so callers can skip appending anything.
    """
    if not indicators.flags:
        return ""

    descriptions = [_INDICATOR_DESCRIPTIONS[f] for f in indicators.flags if f in _INDICATOR_DESCRIPTIONS]
    if not descriptions:
        return ""

    if len(descriptions) == 1:
        joined = descriptions[0]
    else:
        joined = "; ".join(descriptions[:-1]) + f"; and {descriptions[-1]}"

    return f"This message also {joined}."


def _build_domain_summary(domain_mismatches) -> str:
    """
    Turns detected domain mismatches into a short, plain-language
    sentence — the specific, sourced fact ("this link's domain is not
    one MCB is known to use") is exactly the kind of concrete evidence
    this project is built to surface instead of a vague AI guess.
    """
    if not domain_mismatches:
        return ""

    parts = []
    for d in domain_mismatches:
        parts.append(f'the link to "{d.domain}" is not a known domain for {d.matched_entity}')

    return f"Also worth noting: {'; '.join(parts)}."


def _run_check_pipeline(
    db: Session,
    current_user: models.User,
    message_text: str,
    claimed_sender: Optional[str],
    save_check: bool,
) -> models.Check:
    """
    The actual analysis pipeline, factored out so every input mode
    (pasted text, a fetched URL's content, OCR-extracted text from an
    image) converges here and gets IDENTICAL treatment — registry
    check, indicator extraction, domain analysis, verdict — rather
    than each endpoint re-implementing its own version of this logic
    with a chance of silently drifting apart.
    """
    registry_result = match_entity(db, claimed_sender)

    indicators = extract_indicators(message_text)

    domain_results = [
        analyze_domain(url, registry_result.get("matched_entity"))
        for url in indicators.urls
    ]
    domain_mismatches = [d for d in domain_results if d.status == "known_domain_mismatch"]
    domain_structural_flags = [f for d in domain_results for f in d.suspicious_reasons]

    # Phone number analysis — the exact same pattern as domain
    # analysis above, checked against known official numbers rather
    # than a live lookup.
    phone_results = [
        analyze_phone(phone, registry_result.get("matched_entity"))
        for phone in indicators.phone_numbers
    ]
    phone_mismatches = [p for p in phone_results if p.status == "known_number_mismatch"]

    # AI HOOK: once the AI layer exists, call analyze_message() with
    # scrubbed_message_text (never the raw message_text directly) —
    # PII must be masked before anything leaves this process toward a
    # third-party model, or a local model process. Consider also
    # passing `indicators` to the AI layer as extra context rather
    # than making the model re-derive facts a regex already
    # established with full confidence.
    scrubbed_message_text = scrub_message(message_text)
    ai_risk_score = None
    ai_flags = None
    ai_explanation = None
    explanation_source = "registry_and_indicators"

    combined_flags = list(indicators.flags)
    if domain_mismatches:
        combined_flags.append("domain_mismatch")
    if domain_structural_flags:
        combined_flags.append("suspicious_domain_structure")
    if phone_mismatches:
        combined_flags.append("phone_mismatch")

    overall_verdict = derive_verdict(registry_result, ai_risk_score, combined_flags)

    if registry_result["status"] == "name_mismatch":
        default_explanation = _build_name_mismatch_explanation(registry_result["matched_entity"])
    elif registry_result["status"] == "revoked":
        default_explanation = _build_revoked_explanation(
            registry_result["matched_entity"], registry_result.get("status_detail")
        )
    else:
        default_explanation = REGISTRY_EXPLANATIONS.get(registry_result["status"])

    indicator_summary = _build_indicator_summary(indicators)
    if indicator_summary:
        default_explanation = f"{default_explanation} {indicator_summary}"

    domain_summary = _build_domain_summary(domain_mismatches)
    if domain_summary:
        default_explanation = f"{default_explanation} {domain_summary}"

    phone_summary = _build_phone_summary(phone_mismatches)
    if phone_summary:
        default_explanation = f"{default_explanation} {phone_summary}"

    check = models.Check(
        user_id=current_user.id,
        message_text=scrubbed_message_text,
        claimed_sender=claimed_sender,
        registry_match_status=registry_result["status"],
        registry_matched_entity=registry_result["matched_entity"],
        registry_match_score=registry_result["score"],
        ai_risk_score=ai_risk_score,
        ai_flags=ai_flags or (combined_flags or None),
        ai_explanation=ai_explanation or default_explanation,
        explanation_source=explanation_source,
        overall_verdict=overall_verdict,
    )

    # Live SIEM feed: verdict + registry status + claimed sender only —
    # deliberately never message_text, saved or not, matching this
    # project's existing PII-minimization stance (see pii_scrubber.py).
    bus.publish(
        "check_created",
        {
            "user_id": current_user.id,
            "email": getattr(current_user, "email", None),
            "claimed_sender": claimed_sender,
            "registry_match_status": registry_result["status"],
            "overall_verdict": overall_verdict,
            "flags": combined_flags,
            "saved": save_check,
        },
    )

    if not save_check:
        check.id = 0
        check.created_at = datetime.utcnow()
        # exclude_check_id=None here (not 0) — an unsaved check was
        # never written, so there's nothing with id=0 in the database
        # to accidentally exclude from its own history query, unlike
        # the saved case below where the just-created check's real id
        # must be excluded from its own repeat-sender count.
        check.repeat_sender_summary = build_repeat_sender_summary(db, current_user.id, claimed_sender)
        return check

    db.add(check)
    db.commit()
    db.refresh(check)
    return _attach_repeat_sender_summary(db, check)


def _build_phone_summary(phone_mismatches) -> str:
    """
    Same pattern as _build_domain_summary — a specific, sourced fact
    about a phone number not matching the claimed sender's known
    contact numbers.
    """
    if not phone_mismatches:
        return ""

    parts = []
    for p in phone_mismatches:
        parts.append(f'the phone number "{p.phone}" is not a known contact number for {p.matched_entity}')

    return f"Also worth noting: {'; '.join(parts)}."


@router.post("/", response_model=schemas.CheckOut)
def create_check(
    check_in: schemas.CheckCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if not check_and_record_check_call(db, current_user):
        raise HTTPException(
            status_code=429,
            detail=f"Too many checks submitted. Limit is {MAX_CHECKS_PER_WINDOW} per {WINDOW_MINUTES} minutes.",
        )

    if check_in.source_url:
        try:
            message_text = fetch_url_text(check_in.source_url)
        except UnsafeUrlError as e:
            raise HTTPException(status_code=400, detail=f"This URL could not be analyzed for safety reasons: {e}")
        except FetchError as e:
            raise HTTPException(status_code=422, detail=f"Could not retrieve content from this URL: {e}")

        if not message_text.strip():
            raise HTTPException(status_code=422, detail="No readable text content was found at this URL.")
    else:
        message_text = check_in.message_text

    return _run_check_pipeline(db, current_user, message_text, check_in.claimed_sender, check_in.save_check)


@router.post("/from-image", response_model=schemas.CheckOut)
async def create_check_from_image(
    image: UploadFile = File(...),
    claimed_sender: Optional[str] = Form(default=None),
    save_check: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    The third input mode: upload a screenshot (an SMS, WhatsApp
    message, or email) instead of pasting text. OCR-extracts the text
    locally (app/ocr.py, no external API), then runs it through the
    exact same _run_check_pipeline() as pasted text or a fetched URL.
    """
    if not check_and_record_check_call(db, current_user):
        raise HTTPException(
            status_code=429,
            detail=f"Too many checks submitted. Limit is {MAX_CHECKS_PER_WINDOW} per {WINDOW_MINUTES} minutes.",
        )

    image_bytes = await image.read()

    try:
        ocr_result = extract_text_from_image(image_bytes)
    except InvalidImageError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not ocr_result.text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in this image. Try a clearer screenshot, or paste the text directly.",
        )

    check = _run_check_pipeline(db, current_user, ocr_result.text, claimed_sender, save_check)

    if ocr_result.is_low_confidence:
        # A genuinely important caveat: the analysis is only as
        # reliable as the text it was given. Appended after the fact
        # rather than baked into _run_check_pipeline()'s explanation
        # logic, since this is specific to HOW the text was obtained
        # (a possibly-unreliable OCR read), not a finding about the
        # message's content itself.
        check.ai_explanation = (
            f"{check.ai_explanation} Note: the text extracted from your image had low OCR confidence "
            f"({ocr_result.average_confidence:.0f}%) — double-check that the extracted text above "
            f"accurately reflects the original image before relying on this result."
        )

    return check


@router.get("/", response_model=List[schemas.CheckOut])
def list_my_checks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    verdict: Optional[str] = Query(default=None),
):
    query = db.query(models.Check).filter(models.Check.user_id == current_user.id)
    if verdict:
        query = query.filter(models.Check.overall_verdict == verdict)

    return (
        query
        .order_by(models.Check.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.get("/{check_id}", response_model=schemas.CheckOut)
def get_check(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    check = (
        db.query(models.Check)
        .filter(models.Check.id == check_id, models.Check.user_id == current_user.id)
        .first()
    )
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")
    return _attach_repeat_sender_summary(db, check)


@router.post("/{check_id}/feedback", response_model=schemas.CheckOut)
def submit_check_feedback(
    check_id: int,
    feedback_in: schemas.CheckFeedbackIn,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Lets a user mark whether a past verdict was correct — a real,
    honest mechanism for describing improvement over time (see
    README's "Roadmap" section), rather than an unverifiable claim
    about a model getting better with more data. Same per-user
    isolation as get_check: a user can only give feedback on their own
    checks, enforced the same way (404, not 403, for someone else's
    check — see test_security.py for why this project treats
    cross-user access as "not found" rather than "forbidden").
    """
    check = (
        db.query(models.Check)
        .filter(models.Check.id == check_id, models.Check.user_id == current_user.id)
        .first()
    )
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")

    check.user_feedback = "correct" if feedback_in.is_correct else "incorrect"
    db.add(check)
    db.commit()
    db.refresh(check)
    return check
