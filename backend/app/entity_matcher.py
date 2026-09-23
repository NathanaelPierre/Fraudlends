"""
Registry entity matching, the core FraudLens mechanic. Takes a claimed
sender name (extracted from or provided alongside a suspicious
message) and checks it against the locally-cached snapshot of the FSC
Register of Licensees and Bank of Mauritius licensed banks list.

This is deliberately deterministic, explainable code, not an AI call.
The whole point of this feature is to give a factual answer ("this
entity is/isn't in the official registry") rather than a probabilistic
one, which is what the AI layer (added later) is for instead. Same
separation of concerns as a statistical fraud layer versus an optional
LLM escalation: the fact-based check always runs and never depends on
an LLM being available or working.

Match statuses, in order of how they're determined:
  no_sender_given  - the check did not include a claimed sender at all
  verified         - high-confidence match to an entity currently marked active
  revoked          - high-confidence match to a real entity whose license is
                     no longer active (surrendered, revoked) — a specific,
                     sourced fact worth surfacing differently from either a
                     genuine verification or an unrelated unknown name
  name_mismatch    - a close-but-not-exact match exists (e.g. a likely typo
                     or impersonation attempt of a real entity's name)
  not_found        - no meaningful match in the registry at all
"""
import re
from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session
from app import models

EXACT_MATCH_THRESHOLD = 98.0
MISMATCH_THRESHOLD = 75.0

# Below this normalized-claim length (in characters), fuzzy matching is
# too unreliable to confidently call something an impersonation attempt
# vs. a coincidentally-similar short name. Found during testing: "Absa
# Bank" (9 chars normalized) scored 76.2% against "AfrAsia Bank
# Limited" purely because both are short, two-word strings sharing the
# word "bank" — well above the 75% mismatch threshold, despite the two
# banks having no real relationship a person would confuse. Short
# claims below this length that don't hit the (much higher) exact-match
# threshold are reported as "not_found" rather than the more alarming
# "name_mismatch", since the evidence for impersonation specifically
# isn't strong enough at this length.
MIN_LENGTH_FOR_MISMATCH_DETECTION = 12

# token_sort_ratio, not WRatio (rapidfuzz's default in process.extractOne).
# WRatio includes partial/substring matching, which badly overmatches
# short institution names sharing common words: "Tranz Digital Bank"
# scored 85.5 against "AfrAsia Bank Limited" under WRatio purely
# because both contain "bank" as a substring, even though the two names
# share no real similarity a human would recognize. token_sort_ratio
# (order-independent whole-token comparison) scored the same pair at a
# far more honest 40. Verified directly against real entity names and
# the real "Tranz Digital Bank" impersonation case from Bank of
# Mauritius's own January 2026 alert before choosing this scorer —
# see tests/test_entity_matcher.py.
MATCH_SCORER = fuzz.token_sort_ratio


def normalize_name(name: str) -> str:
    """
    Lowercases, strips common corporate suffixes and punctuation, so
    "Absa Bank (Mauritius) Ltd." and "ABSA BANK MAURITIUS LIMITED" both
    normalize to the same comparable string. Runs on both sides of the
    comparison: when building the registry snapshot and when checking
    a claimed sender.
    """
    name = name.lower().strip()
    name = re.sub(r"[.,()]", "", name)
    name = re.sub(r"\b(ltd|limited|inc|incorporated|plc|corp|corporation)\b", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def match_entity(db: Session, claimed_sender):
    """
    Returns a dict with the match result: status, matched_entity,
    score (0-1 confidence or None), and source (FSC or BOM).
    """
    if not claimed_sender or not claimed_sender.strip():
        return {"status": "no_sender_given", "matched_entity": None, "score": None, "source": None, "status_detail": None}

    normalized_claim = normalize_name(claimed_sender)

    entities = db.query(models.RegistryEntity).all()
    if not entities:
        # Registry not populated yet. Fail safe rather than silently
        # claim "not found" for every check, which would look like a
        # real result instead of a data problem.
        return {"status": "registry_unavailable", "matched_entity": None, "score": None, "source": None, "status_detail": None}

    choices = {e.normalized_name: e for e in entities}
    result = process.extractOne(normalized_claim, choices.keys(), scorer=MATCH_SCORER)

    if result is None:
        return {"status": "not_found", "matched_entity": None, "score": 0.0, "source": None, "status_detail": None}

    matched_normalized, score, _ = result
    matched_entity = choices[matched_normalized]
    confidence = score / 100.0

    if score >= EXACT_MATCH_THRESHOLD:
        if matched_entity.status and matched_entity.status != "Active":
            # A real entity, exactly matched by name, but whose license
            # is no longer active — a more specific, more useful fact
            # than either "verified" (would wrongly imply currently
            # licensed) or "not_found" (would discard the real,
            # sourced information that this name once had, and has
            # since lost, a license).
            return {
                "status": "revoked",
                "matched_entity": matched_entity.name,
                "score": confidence,
                "source": matched_entity.source,
                "status_detail": matched_entity.status,
            }
        return {
            "status": "verified",
            "matched_entity": matched_entity.name,
            "score": confidence,
            "source": matched_entity.source,
            "status_detail": matched_entity.status,
        }
    elif score >= MISMATCH_THRESHOLD and len(normalized_claim) >= MIN_LENGTH_FOR_MISMATCH_DETECTION:
        # Close enough to be a plausible impersonation of a real entity
        # (a near-identical name) — this is a MORE concerning result
        # than "not found at all", since it suggests deliberate
        # name-spoofing, not just an unrelated stranger. Gated on
        # claim length (see MIN_LENGTH_FOR_MISMATCH_DETECTION) so a
        # short, generic claim isn't over-confidently flagged as
        # impersonating a specific entity.
        return {
            "status": "name_mismatch",
            "matched_entity": matched_entity.name,
            "score": confidence,
            "source": matched_entity.source,
            "status_detail": None,
        }
    else:
        return {"status": "not_found", "matched_entity": None, "score": confidence, "source": None, "status_detail": None}
