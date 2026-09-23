"""
deterministic indicator extraction: pulls structured, checkable
signals out of a message's text, URLs, phone numbers, OTP or
credential requests, urgency language, payment requests, before any AI
model sees it.

this is deliberately its own layer, separate from both
entity_matcher.py (which only ever looks at the claimed sender field)
and the eventual AI layer (which reasons over free text). the
motivation is the same "AI explains, code decides" principle used
throughout this project: whether a message contains something
OTP-shaped is a fact a regex can establish with full confidence, it
doesn't need, and shouldn't wait for, a language model's opinion. his
also means the demo has a second, fully-working, zero-GPU-required
layer of analysis today, not just the registry check.

the eventual AI layer's job is different and complementary: reasoning
about tone, implication, and context a regex can't reliably capture,
not re-detecting things this module already establishes deterministically.
"""

#note for future me, implement ai layers after fronytend
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class IndicatorResult:
    urls: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    requests_otp: bool = False
    requests_card_details: bool = False
    creates_urgency: bool = False
    requests_money_transfer: bool = False
    mentions_investment_returns: bool = False

    @property
    def flags(self) -> List[str]:
        """
        A flat list of triggered indicator names, in a stable order,
        this is the shape stored on Check.ai_flags and shown to the
        user, matching the structured-evidence pattern (flags as a
        list of short identifiers, not free text) used throughout this
        project's explanation design.
        """
        result = []
        if self.requests_otp:
            result.append("requests_otp")
        if self.requests_card_details:
            result.append("requests_card_details")
        if self.creates_urgency:
            result.append("urgency")
        if self.requests_money_transfer:
            result.append("payment_request")
        if self.mentions_investment_returns:
            result.append("investment_promise")
        if self.urls:
            result.append("contains_url")
        return result


_URL_RE = re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")

_OTP_KEYWORDS = re.compile(r"\b(otp|one[- ]time (?:password|pin|code)|verification code|security code)\b", re.IGNORECASE)

# Genuinely important distinction found during testing: a message
# containing the word "OTP" is ambiguous on its own — "Your OTP is
# 483921" (a bank legitimately notifying you of your own one-time
# code, completely normal) and "Reply with your OTP to verify" (a
# scammer asking you to hand yours over, a real red flag) both matched
# the same broad keyword identically, even though they are opposite
# situations. Only the second is actually suspicious. This pattern
# specifically requires a REQUEST verb near the OTP mention (send,
# reply, share, provide, enter, confirm with) — a bare OTP mention
# alone is not flagged.
_OTP_REQUEST_KEYWORDS = re.compile(
    r"\b(?:send|reply (?:with|to)|share|provide|enter|confirm (?:with|using)|"
    r"give (?:us|me)|verify)\b[^.!?]{0,40}\b(?:otp|one[- ]time (?:password|pin|code)|"
    r"verification code|security code)\b"
    r"|"
    r"\b(?:otp|one[- ]time (?:password|pin|code)|verification code|security code)\b"
    r"[^.!?]{0,40}\b(?:to (?:us|verify|confirm)|required|needed)\b",
    re.IGNORECASE,
)
_CARD_KEYWORDS = re.compile(r"\b(card number|cvv|card details|pin number|expiry date)\b", re.IGNORECASE)
_URGENCY_KEYWORDS = re.compile(
    r"\b(urgent|immediately|act now|expire[sd]? (?:today|soon|in \d+)|last chance|"
    r"account (?:will be |has been )?(?:suspended|blocked|closed|frozen)|"
    r"within \d+ (?:hours?|minutes?))\b",
    re.IGNORECASE,
)
_MONEY_TRANSFER_KEYWORDS = re.compile(
    r"\b(send money|transfer (?:funds|money)|wire transfer|pay(?:ment)? (?:now|immediately|required)|"
    r"deposit (?:required|now))\b",
    re.IGNORECASE,
)
_INVESTMENT_KEYWORDS = re.compile(
    r"\b(guaranteed returns?|double your (?:money|investment)|risk[- ]free|"
    r"investment opportunity|high returns?|crypto investment)\b",
    re.IGNORECASE,
)


def extract_indicators(message_text: str) -> IndicatorResult:
    """
    Pure function: same input always produces the same output, no
    external state, no AI call, matches this project's "explanations a
    person can audit" principle from entity_matcher.py.
    """
    return IndicatorResult(
        urls=_URL_RE.findall(message_text),
        phone_numbers=_PHONE_RE.findall(message_text),
        requests_otp=bool(_OTP_REQUEST_KEYWORDS.search(message_text)),
        requests_card_details=bool(_CARD_KEYWORDS.search(message_text)),
        creates_urgency=bool(_URGENCY_KEYWORDS.search(message_text)),
        requests_money_transfer=bool(_MONEY_TRANSFER_KEYWORDS.search(message_text)),
        mentions_investment_returns=bool(_INVESTMENT_KEYWORDS.search(message_text)),
    )
