"""
PII scrubbing: masks obvious sensitive identifiers in message text
before it's stored or sent to any AI model. This is regex-based
pattern detection, not a general PII-detection model, it catches
common, structurally-recognizable patterns (OTP-shaped digit codes,
card numbers, phone numbers, emails), not every possible kind of
sensitive data. It is a real, useful mitigation, not a complete
guarantee, and the README should not overstate it.

This runs on a copy of the message used for storage/AI, never on the
copy returned in the immediate API response, the person submitting a
check about their own message already has that text in front of them
on their own phone, so masking it back to them in the same response
would be pointless friction. The point of masking is what persists
afterward and what leaves the server toward a third party.
"""
import re

# The card-number pattern must end on a DIGIT, not on the optional
# separator that can follow one — (?:\d[ -]?){13,19} was found to
# greedily consume one trailing space/hyphen past the last real digit
# (e.g. matching "4111 1111 1111 1111 " with a trailing space before
# "expires"), which corrupted the surrounding text once replaced.
# Ending the pattern on a bare \d fixes this: exactly one separator is
# allowed BETWEEN digit groups, never after the final one.
_CARD_NUMBER_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
_OTP_RE = re.compile(r"\b\d{4,8}\b")
_PHONE_RE = re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def _mask_card_number(match: re.Match) -> str:
    digits_only = re.sub(r"[ -]", "", match.group())
    if len(digits_only) < 13:
        return match.group()
    last_four = digits_only[-4:]
    return f"[CARD ENDING {last_four}]"


def _mask_otp(match: re.Match) -> str:
    return "[REDACTED CODE]"


def _mask_phone(match: re.Match) -> str:
    return "[REDACTED PHONE]"


def _mask_email(match: re.Match) -> str:
    local, domain = match.group().split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 1)
    return f"{masked_local}@{domain}"


def scrub_message(text: str) -> str:
    """
    Returns a copy of `text` with obvious PII patterns masked. Applied
    before persistence and before any text is sent to an AI provider.
    Does not claim to catch every form of sensitive data, see this
    module's docstring, and is not a substitute for save_check=false
    when a user knows their message contains something specific they
    don't want stored at all.

    Finds all matches against the ORIGINAL text in one pass per
    pattern, then applies replacements back-to-front by position —
    NOT by running each regex sequentially over the previous pass's
    output. Running sequentially was tried first and had a real bug:
    the OTP pattern would re-match digits that appeared INSIDE an
    already-inserted card-mask placeholder (e.g. "[CARD ENDING 1111]"
    getting its own "1111" re-redacted as an OTP, producing
    "[CARD ENDING [REDACTED CODE]]"). Matching only against the
    original text avoids this category of bug entirely, since no
    pattern ever sees another pattern's replacement text.

    Priority order when spans overlap (e.g. a phone-shaped run of
    digits that's actually part of a longer card number): card number,
    then email, then phone, then OTP — the longer, more specific
    patterns take precedence over shorter, more general ones.
    """
    patterns_in_priority_order = [
        (_CARD_NUMBER_RE, _mask_card_number),
        (_EMAIL_RE, _mask_email),
        (_PHONE_RE, _mask_phone),
        (_OTP_RE, _mask_otp),
    ]

    # Collect every match against the untouched original text, tagged
    # with which masker produced it.
    all_matches = []
    for pattern, masker in patterns_in_priority_order:
        for match in pattern.finditer(text):
            all_matches.append((match.start(), match.end(), match, masker))

    # Drop any match whose span overlaps a higher-priority match found
    # earlier in patterns_in_priority_order (already in all_matches
    # ahead of it, since we appended in priority order).
    accepted = []
    for start, end, match, masker in all_matches:
        overlaps = any(not (end <= a_start or start >= a_end) for a_start, a_end, _, _ in accepted)
        if not overlaps:
            accepted.append((start, end, match, masker))

    # Apply replacements back-to-front so earlier spans' positions
    # stay valid as later (in text order, but already-processed)
    # replacements change the string length.
    accepted.sort(key=lambda item: item[0], reverse=True)
    result = text
    for start, end, match, masker in accepted:
        result = result[:start] + masker(match) + result[end:]

    return result
