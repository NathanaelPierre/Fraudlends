"""
Phone number analysis: given a phone number found in a message (see
app/indicator_extractor.py, which already extracts these), checks
whether it plausibly belongs to whichever institution the message
claims to be from.

The exact same pattern and reasoning as app/domain_analyzer.py: a
small, curated table of known official phone numbers
(registry_data.py's KNOWN_OFFICIAL_PHONE_NUMBERS), checked instantly
and locally, rather than a live lookup against a phone directory
service (slow, unreliable, and reintroducing the external network
dependency this project avoids elsewhere).
"""
import re
from dataclasses import dataclass
from typing import Optional

from app.registry_data import KNOWN_OFFICIAL_PHONE_NUMBERS

_PHONE_TO_ENTITY = {}
for _entity_name, _numbers in KNOWN_OFFICIAL_PHONE_NUMBERS.items():
    for _number in _numbers:
        _PHONE_TO_ENTITY[_number] = _entity_name


@dataclass
class PhoneAnalysisResult:
    phone: str
    normalized: Optional[str] = None
    status: str = "no_phone"
    matched_entity: Optional[str] = None


def normalize_phone(phone: str) -> str:
    """
    Strips everything except digits, so "+230 402 1000", "230-402-1000",
    and "2304021000" all compare equal. This mirrors
    entity_matcher.py's normalize_name(), both exist so the same
    real-world value, written in different but equally valid ways,
    reliably matches the stored canonical form.
    """
    return re.sub(r"\D", "", phone)


def analyze_phone(phone: str, claimed_sender_entity: Optional[str] = None) -> PhoneAnalysisResult:
    """
    claimed_sender_entity is the registry-matched entity name (from
    entity_matcher.match_entity()'s "matched_entity" field), same
    convention as analyze_domain() in domain_analyzer.py.
    """
    if not phone or not phone.strip():
        return PhoneAnalysisResult(phone=phone, status="no_phone")

    normalized = normalize_phone(phone)
    if not normalized:
        return PhoneAnalysisResult(phone=phone, status="no_phone")

    owning_entity = _PHONE_TO_ENTITY.get(normalized)

    if claimed_sender_entity and owning_entity == claimed_sender_entity:
        return PhoneAnalysisResult(
            phone=phone, normalized=normalized, status="matches_claimed_entity", matched_entity=owning_entity
        )

    if claimed_sender_entity and claimed_sender_entity in KNOWN_OFFICIAL_PHONE_NUMBERS:
        return PhoneAnalysisResult(
            phone=phone, normalized=normalized, status="known_number_mismatch", matched_entity=claimed_sender_entity
        )

    if owning_entity:
        return PhoneAnalysisResult(
            phone=phone, normalized=normalized, status="known_number_mismatch", matched_entity=owning_entity
        )

    return PhoneAnalysisResult(phone=phone, normalized=normalized, status="unknown_number")
