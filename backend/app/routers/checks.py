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
import csv
import io
from fastapi.responses import StreamingResponse
from app.ocr import extract_text_from_image, InvalidImageError
from app.stt import transcribe_audio, InvalidAudioError, TranscriptionError
from app.tts import synthesize_speech, build_spoken_summary, TtsError
from app.repeat_sender import build_repeat_sender_summary
from app.event_bus import bus
from app.sender_extractor import extract_sender_from_text
from app import explanations_i18n

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

# Severity for each indicator flag, mirroring verdict.py's own
# HIGH_RISK_INDICATOR_FLAGS / SUSPICIOUS_INDICATOR_FLAGS sets — kept as
# a separate mapping here (rather than importing verdict.py's sets
# directly) because this dict also needs an "info" tier for flags that
# exist for informational value but never affect the verdict at all
# (none currently, but keeping the shape open for one), whereas
# verdict.py's sets are specifically "what counts as suspicious/high
# risk", a narrower purpose than "what severity to LABEL this evidence
# item for display".
_INDICATOR_SEVERITY = {
    "requests_otp": "high_risk",
    "requests_card_details": "high_risk",
    "urgency": "suspicious",
    "payment_request": "suspicious",
    "investment_promise": "suspicious",
    "contains_url": "info",
}


def _build_evidence_list(language: str, registry_result: dict, indicators, domain_mismatches, domain_structural_flags, phone_mismatches) -> list:
    """
    Builds the structured evidence trail (schemas.EvidenceItem list)
    from every signal source computed in _run_check_pipeline —
    registry, deterministic indicators, domain analysis, phone
    analysis. This is what lets a frontend render a real evidence list
    (each item with its own category/description/severity) instead of
    only having a bare list of internal flag codes (Check.ai_flags) or
    one bundled prose paragraph (Check.ai_explanation) to work with.

    Always includes exactly one registry item (the registry check
    always runs and always produces SOME result, even "no sender
    given"), plus zero or more items for whatever the indicator,
    domain, and phone layers actually found.

    `language` must be the SAME value used to build the check's main
    ai_explanation (indicators.detected_language) — see
    _build_evidence_list_from_stored_check()'s consistency requirement
    with this function, already the subject of one real bug found via
    live testing (see that function's docstring).
    """
    evidence = []

    registry_status = registry_result["status"]
    registry_severity = {
        "verified": "info",
        "not_found": "suspicious",
        "revoked": "suspicious",
        "name_mismatch": "high_risk",
        "no_sender_given": "info",
        "registry_unavailable": "info",
    }.get(registry_status, "info")

    registry_description = explanations_i18n.build_registry_evidence_description(
        language, registry_status,
        entity=registry_result.get("matched_entity"),
        detail=registry_result.get("status_detail"),
    )

    evidence.append(schemas.EvidenceItem(
        category="registry", code=registry_status, description=registry_description, severity=registry_severity,
    ))

    for flag in indicators.flags:
        if flag in _INDICATOR_DESCRIPTIONS:
            evidence.append(schemas.EvidenceItem(
                category="indicator",
                code=flag,
                description=explanations_i18n.build_indicator_evidence_description(language, flag),
                severity=_INDICATOR_SEVERITY.get(flag, "info"),
            ))

    for d in domain_mismatches:
        evidence.append(schemas.EvidenceItem(
            category="domain",
            code="domain_mismatch",
            description=explanations_i18n.build_domain_evidence_description(
                language, "mismatch", domain=d.domain, entity=d.matched_entity
            ),
            severity="high_risk",
        ))

    # Found via live testing: this branch was missing entirely, unlike
    # _build_evidence_list_from_stored_check()'s equivalent handling —
    # a structurally suspicious domain (uncommon TLD, excessive
    # subdomain nesting) that ISN'T a known-entity mismatch was
    # silently dropped from the creation-time evidence list, even
    # though it correctly appeared in the stored ai_flags and was
    # correctly reconstructed on a later GET. The two builders had
    # drifted apart; this makes them consistent.
    if domain_structural_flags:
        evidence.append(schemas.EvidenceItem(
            category="domain",
            code="suspicious_domain_structure",
            description=explanations_i18n.build_domain_evidence_description(language, "structure"),
            severity="suspicious",
        ))

    for p in phone_mismatches:
        evidence.append(schemas.EvidenceItem(
            category="phone",
            code="phone_mismatch",
            description=explanations_i18n.build_phone_evidence_description(language, p.phone, p.matched_entity),
            severity="high_risk",
        ))

    return evidence


def _build_evidence_list_from_stored_check(check: models.Check) -> list:
    """
    Rebuilds the evidence list from an already-stored Check row, for
    GET /checks/{id} — unlike _build_evidence_list() above (used at
    creation time, with the full pipeline's intermediate objects still
    in scope), this reconstructs from what was persisted:
    registry_match_status/matched_entity/status_detail, the combined
    ai_flags list, and evidence_detail (the specific domain/phone
    values behind a domain_mismatch or phone_mismatch flag — see
    models.Check.evidence_detail's docstring). A check created before
    evidence_detail existed falls back to a generic description for
    those two flag types rather than crashing.

    Uses check.detected_language (stored at creation time) rather than
    re-detecting from check.message_text — the stored text is already
    PII-scrubbed, which can remove words a fresh detection would need,
    so re-detecting here could silently disagree with the language the
    check was actually explained in originally.
    """
    evidence = []
    language = check.detected_language or "en"

    registry_status = check.registry_match_status
    registry_severity = {
        "verified": "info",
        "not_found": "suspicious",
        "revoked": "suspicious",
        "name_mismatch": "high_risk",
        "no_sender_given": "info",
        "registry_unavailable": "info",
    }.get(registry_status, "info")

    registry_description = explanations_i18n.build_registry_evidence_description(
        language, registry_status,
        entity=check.registry_matched_entity,
        detail=check.registry_status_detail,
    )

    evidence.append(schemas.EvidenceItem(
        category="registry", code=registry_status, description=registry_description, severity=registry_severity,
    ))

    evidence_detail = check.evidence_detail or {}
    domain_mismatch_details = iter(evidence_detail.get("domain_mismatches", []))
    phone_mismatch_details = iter(evidence_detail.get("phone_mismatches", []))

    fallback_descriptions = {
        "en": {
            "domain": "A link in this message does not match a known domain for the claimed sender.",
            "phone": "A phone number in this message does not match a known contact number for the claimed sender.",
        },
        "fr": {
            "domain": "Un lien dans ce message ne correspond pas à un domaine connu pour l'expéditeur indiqué.",
            "phone": "Un numéro de téléphone dans ce message ne correspond pas à un numéro de contact connu pour l'expéditeur indiqué.",
        },
        "cr": {
            "domain": "Enn lien dan sa mesaz la pa matche avek enn domenn nou konnen pou expediter la.",
            "phone": "Enn nimero telefonn dan sa mesaz la pa matche avek enn nimero kontakt nou konnen pou expediter la.",
        },
    }.get(language, {
        "domain": "A link in this message does not match a known domain for the claimed sender.",
        "phone": "A phone number in this message does not match a known contact number for the claimed sender.",
    })

    for flag in (check.ai_flags or []):
        if flag in _INDICATOR_DESCRIPTIONS:
            evidence.append(schemas.EvidenceItem(
                category="indicator",
                code=flag,
                description=explanations_i18n.build_indicator_evidence_description(language, flag),
                severity=_INDICATOR_SEVERITY.get(flag, "info"),
            ))
        elif flag == "domain_mismatch":
            detail = next(domain_mismatch_details, None)
            description = (
                explanations_i18n.build_domain_evidence_description(
                    language, "mismatch", domain=detail["domain"], entity=detail["matched_entity"]
                )
                if detail
                # Fallback for a Check row created before evidence_detail
                # existed, or in the unlikely case the stored detail is
                # somehow shorter than the flag count — never crash,
                # degrade to a generic wording instead.
                else fallback_descriptions["domain"]
            )
            evidence.append(schemas.EvidenceItem(
                category="domain", code="domain_mismatch", description=description, severity="high_risk",
            ))
        elif flag == "phone_mismatch":
            detail = next(phone_mismatch_details, None)
            description = (
                explanations_i18n.build_phone_evidence_description(language, detail["phone"], detail["matched_entity"])
                if detail
                else fallback_descriptions["phone"]
            )
            evidence.append(schemas.EvidenceItem(
                category="phone", code="phone_mismatch", description=description, severity="high_risk",
            ))
        elif flag == "suspicious_domain_structure":
            evidence.append(schemas.EvidenceItem(
                category="domain",
                code="suspicious_domain_structure",
                description=explanations_i18n.build_domain_evidence_description(language, "structure"),
                severity="suspicious",
            ))

    return evidence


def _attach_evidence_from_stored_check(check: models.Check) -> models.Check:
    check.evidence = _build_evidence_list_from_stored_check(check)
    return check


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
    sender_auto_detected = False
    sender_detection_source_text = None

    if not claimed_sender or not claimed_sender.strip():
        # No explicit sender given (the single-box input flow) — scan
        # the message's own text for a known registry name/alias
        # before running the registry check, so the deterministic
        # match still has something to work with. See
        # app/sender_extractor.py for the honest limitation this
        # carries: it can only detect a sender ALREADY in the registry
        # snapshot, not a fabricated name that merely sounds plausible.
        extraction = extract_sender_from_text(db, message_text)
        if extraction.detected_sender:
            claimed_sender = extraction.detected_sender
            sender_auto_detected = True
            sender_detection_source_text = extraction.matched_text

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

    # Captures the SPECIFIC values behind domain_mismatch/phone_mismatch
    # flags (which domain/number, which entity it doesn't match) — see
    # models.Check.evidence_detail's docstring for why this is stored
    # rather than only kept in local scope: without it, a later GET
    # could only reconstruct a generic evidence description, not the
    # specific one shown at creation time.
    evidence_detail = {}
    if domain_mismatches:
        evidence_detail["domain_mismatches"] = [
            {"domain": d.domain, "matched_entity": d.matched_entity} for d in domain_mismatches
        ]
    if phone_mismatches:
        evidence_detail["phone_mismatches"] = [
            {"phone": p.phone, "matched_entity": p.matched_entity} for p in phone_mismatches
        ]

    language = indicators.detected_language

    if registry_result["status"] == "name_mismatch":
        default_explanation = explanations_i18n.build_name_mismatch_explanation(
            language, registry_result["matched_entity"]
        )
    elif registry_result["status"] == "revoked":
        default_explanation = explanations_i18n.build_revoked_explanation(
            language, registry_result["matched_entity"], registry_result.get("status_detail")
        )
    else:
        lang_explanations = explanations_i18n.REGISTRY_EXPLANATIONS.get(language, explanations_i18n.REGISTRY_EXPLANATIONS["en"])
        default_explanation = lang_explanations.get(registry_result["status"]) or explanations_i18n.REGISTRY_EXPLANATIONS["en"].get(registry_result["status"])

    if sender_auto_detected and sender_detection_source_text:
        # Shown as visible reasoning, not a silent decision — the user
        # gets to see exactly what text triggered the registry check,
        # in their own words, so an incorrect detection is obvious
        # rather than hidden inside an opaque verdict.
        detection_note = explanations_i18n.build_sender_detection_note(
            language, sender_detection_source_text, claimed_sender
        )
        default_explanation = f"{detection_note} {default_explanation}"

    indicator_summary = explanations_i18n.build_indicator_summary(language, indicators.flags)
    if indicator_summary:
        default_explanation = f"{default_explanation} {indicator_summary}"

    domain_summary = explanations_i18n.build_domain_summary(language, domain_mismatches)
    if domain_summary:
        default_explanation = f"{default_explanation} {domain_summary}"

    phone_summary = explanations_i18n.build_phone_summary(language, phone_mismatches)
    if phone_summary:
        default_explanation = f"{default_explanation} {phone_summary}"

    check = models.Check(
        user_id=current_user.id,
        message_text=scrubbed_message_text,
        claimed_sender=claimed_sender,
        sender_auto_detected=sender_auto_detected,
        sender_detection_source_text=sender_detection_source_text,
        detected_language=language,
        registry_match_status=registry_result["status"],
        registry_matched_entity=registry_result["matched_entity"],
        registry_match_score=registry_result["score"],
        registry_status_detail=registry_result.get("status_detail"),
        evidence_detail=evidence_detail or None,
        ai_risk_score=ai_risk_score,
        ai_flags=ai_flags or (combined_flags or None),
        ai_explanation=ai_explanation or default_explanation,
        explanation_source=explanation_source,
        overall_verdict=overall_verdict,
    )

    # Live SIEM feed: verdict + registry status + claimed sender only —
    # deliberately never message_text, saved or not, matching this
    # project's existing PII-minimization stance (see pii_scrubber.py).
    try:
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
    except Exception:
        pass

    # Attached as a transient attribute, same pattern as
    # repeat_sender_summary — computed fresh every time, not a stored
    # column, since it's fully derivable from data already on the
    # Check record (or, for the unsaved case below, from the pipeline's
    # local variables directly).
    check.evidence = _build_evidence_list(language, registry_result, indicators, domain_mismatches, domain_structural_flags, phone_mismatches)

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
    check.evidence = _build_evidence_list(language, registry_result, indicators, domain_mismatches, domain_structural_flags, phone_mismatches)
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


@router.post("/from-audio", response_model=schemas.CheckOut)
async def create_check_from_audio(
    audio: UploadFile = File(...),
    claimed_sender: Optional[str] = Form(default=None),
    save_check: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    The fourth input mode: upload a spoken audio clip instead of typed
    text — someone reading out a suspicious voicemail or phone call
    script, for instance. Transcribes locally (app/stt.py, no external
    API), then runs the transcript through the exact same
    _run_check_pipeline() as every other input mode.

    IMPORTANT: the local speech recognition engine (CMU Sphinx) has
    meaningfully lower accuracy than a modern option like Whisper —
    confirmed directly during development (see app/stt.py's module
    docstring for specifics: a real test phrase had its brand name
    transcribed entirely wrong, and pure silence was once hallucinated
    into a word). Every result from this endpoint is treated as
    lower-confidence input and carries an explicit caveat, the same
    honest-caveat pattern already used for low-confidence OCR results.
    """
    if not check_and_record_check_call(db, current_user):
        raise HTTPException(
            status_code=429,
            detail=f"Too many checks submitted. Limit is {MAX_CHECKS_PER_WINDOW} per {WINDOW_MINUTES} minutes.",
        )

    audio_bytes = await audio.read()

    try:
        stt_result = transcribe_audio(audio_bytes)
    except InvalidAudioError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except TranscriptionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not stt_result.text.strip():
        raise HTTPException(
            status_code=422,
            detail="No speech could be transcribed from this audio. Try a clearer recording, or type the message directly.",
        )

    check = _run_check_pipeline(db, current_user, stt_result.text, claimed_sender, save_check)

    if stt_result.is_low_reliability_engine:
        check.ai_explanation = (
            f"{check.ai_explanation} Note: this result was transcribed from spoken audio using a "
            f"local, offline speech recognition engine that can make real transcription errors, "
            f"especially with brand or institution names. Please verify that the transcribed text "
            f'("{stt_result.text}") accurately reflects what was actually said before relying on this result.'
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


@router.get("/export")
def export_checks_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Exports the current user's own check history as a CSV file. This
    is the realistic, buildable version of "report to authorities" —
    rather than a real government/bank reporting integration (out of
    scope for this build), a user gets a structured record of their
    checks they can forward or attach themselves. Registered before
    /{check_id} for the same routing reason as /summary above.

    Deliberately does not include claimed_sender's associated
    message_text in a way that assumes it's already scrubbed of PII —
    it IS (see app/pii_scrubber.py, applied before storage), but this
    endpoint doesn't re-scrub, it exports exactly what's already
    stored, so its output inherits the same privacy guarantee as the
    stored records themselves.
    """
    checks = (
        db.query(models.Check)
        .filter(models.Check.user_id == current_user.id)
        .order_by(models.Check.created_at.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "created_at", "claimed_sender", "message_text",
        "registry_match_status", "registry_matched_entity",
        "overall_verdict", "ai_flags", "user_feedback",
    ])
    for check in checks:
        writer.writerow([
            check.id,
            check.created_at.isoformat(),
            check.claimed_sender or "",
            check.message_text,
            check.registry_match_status,
            check.registry_matched_entity or "",
            check.overall_verdict,
            ";".join(check.ai_flags) if check.ai_flags else "",
            check.user_feedback or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fraudlens_checks_export.csv"},
    )


@router.get("/summary", response_model=schemas.CheckSummary)
def get_checks_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    A dashboard-style rollup of a user's own check history — total
    counts by verdict, feedback given so far, and which claimed
    senders have been checked most often. Registered before
    /{check_id} below so the literal path "/summary" is matched first;
    otherwise FastAPI would try to parse "summary" as an integer
    check_id and 422 instead of returning this.

    Scoped strictly to the current user's own checks, same isolation
    guarantee as every other endpoint here — see test_security.py.
    """
    all_checks = db.query(models.Check).filter(models.Check.user_id == current_user.id).all()

    verdict_counts = {"safe": 0, "suspicious": 0, "high_risk": 0}
    feedback_correct = 0
    feedback_incorrect = 0
    sender_counts: dict = {}

    for check in all_checks:
        if check.overall_verdict in verdict_counts:
            verdict_counts[check.overall_verdict] += 1

        if check.user_feedback == "correct":
            feedback_correct += 1
        elif check.user_feedback == "incorrect":
            feedback_incorrect += 1

        if check.claimed_sender:
            sender_counts[check.claimed_sender] = sender_counts.get(check.claimed_sender, 0) + 1

    most_checked = sorted(sender_counts.items(), key=lambda item: item[1], reverse=True)[:5]

    return schemas.CheckSummary(
        total_checks=len(all_checks),
        safe_count=verdict_counts["safe"],
        suspicious_count=verdict_counts["suspicious"],
        high_risk_count=verdict_counts["high_risk"],
        checks_with_feedback=feedback_correct + feedback_incorrect,
        feedback_marked_correct=feedback_correct,
        feedback_marked_incorrect=feedback_incorrect,
        most_checked_senders=[{"sender": sender, "count": count} for sender, count in most_checked],
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
    check = _attach_evidence_from_stored_check(check)
    return _attach_repeat_sender_summary(db, check)


@router.get("/{check_id}/speak")
def speak_check_result(
    check_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """
    Returns a spoken-audio (WAV) version of a check's verdict and
    explanation — an accessibility feature for someone with low
    literacy, a visual impairment, or reacting under stress to a
    suspicious call, who needs to hear "this is high risk, don't send
    money" rather than read a text screen. Uses a local, offline TTS
    engine (app/tts.py) — no external API call.

    Same per-user isolation as every other check-scoped endpoint:
    404, not 403, for another user's check (see test_security.py for
    why this project treats cross-user access as "not found").
    """
    check = (
        db.query(models.Check)
        .filter(models.Check.id == check_id, models.Check.user_id == current_user.id)
        .first()
    )
    if check is None:
        raise HTTPException(status_code=404, detail="Check not found")

    spoken_text = build_spoken_summary(check.overall_verdict, check.ai_explanation or "")

    try:
        tts_result = synthesize_speech(spoken_text)
    except TtsError as e:
        raise HTTPException(status_code=503, detail=f"Could not generate spoken audio: {e}")

    return StreamingResponse(
        io.BytesIO(tts_result.audio_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": f"inline; filename=check_{check_id}_result.wav"},
    )


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
    return _attach_evidence_from_stored_check(check)
