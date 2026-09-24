"""
Sender extraction: scans a message's own text for a plausible claimed
sender, so a user can submit a single box of text with no separate
"who is this from" field, and the registry check still has something
to work with.

This is deliberately deterministic, not an AI call, the same "AI
explains, code decides" principle used throughout this project.
Scanning for a known registry name or alias inside the message text is
a simple substring search, not a guess, and it costs nothing to run on
every check. It has a real, honest limitation: it can only detect a
sender whose name is already in the registry snapshot or its alias
table (see registry_data.py), a fabricated institution name that
sounds plausible but isn't a real entity won't be pulled out by this
method, since there is nothing in the database for it to match
against. That gap is intentionally left for the future AI layer to
close (see the AI HOOK comment in routers/checks.py) rather than
papered over with a fragile heuristic (e.g. "the first capitalized
word") that would misfire constantly on ordinary text.
"""
import re
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from app import models
from app.entity_matcher import normalize_name


@dataclass
class SenderExtractionResult:
    detected_sender: Optional[str]
    matched_text: Optional[str]


def extract_sender_from_text(db: Session, message_text: str) -> SenderExtractionResult:
    """
    Looks for any known registry entity name or alias appearing as a
    substring of message_text (case-insensitive, punctuation-tolerant).
    When multiple candidates match, the longest matched substring wins,
    a longer match is more specific and less likely to be a
    coincidental short-string collision.

    Returns detected_sender=None if nothing in the registry snapshot
    appears in the text at all, this is a normal, common outcome (most
    messages don't name a specific institution), not an error.
    """
    if not message_text or not message_text.strip():
        return SenderExtractionResult(detected_sender=None, matched_text=None)

    entities = db.query(models.RegistryEntity).all()
    if not entities:
        return SenderExtractionResult(detected_sender=None, matched_text=None)

    best_entity = None
    best_matched_text = None
    best_length = 0

    for entity in entities:
        # Each registry row's OWN name is searched for directly against
        # the ORIGINAL message text — this includes alias rows, whose
        # `name` field holds the formal name but whose row exists
        # specifically because the ALIAS ("MCB") is what a real user
        # would type. Searching entity.name against the raw message
        # would miss "MCB" entirely (the text never contains the full
        # formal name); the fix is to build each candidate pattern from
        # whichever string this row's normalized_name represents,
        # recovered via the same normalize_name() transform, tolerant
        # of punctuation/spacing differences, applied here to the
        # CANDIDATE string rather than to the message.
        candidate_source = entity.normalized_name
        if not candidate_source or len(candidate_source) < 3:
            continue

        # Build a loose regex from the normalized candidate itself
        # (already lowercase, punctuation-stripped words separated by
        # single spaces), tolerant of the original text's own
        # punctuation/spacing/casing around those same words.
        words = candidate_source.split(" ")
        loose_pattern = r"\b" + r"[\s.,]*".join(re.escape(w) for w in words) + r"\b"

        match = re.search(loose_pattern, message_text, re.IGNORECASE)
        if match and len(candidate_source) > best_length:
            best_entity = entity
            best_matched_text = match.group()
            best_length = len(candidate_source)

    if best_entity is None:
        return SenderExtractionResult(detected_sender=None, matched_text=None)

    return SenderExtractionResult(detected_sender=best_entity.name, matched_text=best_matched_text)
