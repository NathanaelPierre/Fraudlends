"""
Deterministic indicator extraction: pulls structured, checkable
signals out of a message's text, URLs, phone numbers, OTP or
credential requests, urgency language, payment requests, before any AI
model sees it.

This is deliberately its own layer, separate from both
entity_matcher.py (which only ever looks at the claimed sender field)
and the eventual AI layer (which reasons over free text). The
motivation is the same "AI explains, code decides" principle used
throughout this project: whether a message contains something
OTP-shaped is a fact a regex can establish with full confidence, it
doesn't need, and shouldn't wait for, a language model's opinion.

MULTILINGUAL: keyword patterns exist for English, French, and Kreol
Morisyen (see app/language_detector.py for how the language itself is
determined). The three languages' patterns are NOT literal translations
of each other, each was written to match how these scam tactics
actually get phrased in that language, which sometimes differs in
structure, not just vocabulary. For example, English's OTP-REQUEST
distinction (a request verb near "OTP") uses "verify" as a request
verb; French's uses "vérifier" similarly, but Kreol commonly phrases
the same request as "montre" or "donn" (show/give) rather than a
direct verify-style construction, so the Kreol pattern reflects that
real difference rather than mechanically mirroring English's word list.

These non-English patterns are new and have had less real-world
exposure than the English ones (which went through several rounds of
bug-fixing against live testing, see the OTP-notice-vs-OTP-request
distinction below). They should be treated as a solid first pass, not
as exhaustively battle-tested as the English patterns, see this
project's README for this stated honestly as a known limitation.
"""
import re
from dataclasses import dataclass, field
from typing import List

from app.language_detector import detect_language


@dataclass
class IndicatorResult:
    urls: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    requests_otp: bool = False
    requests_card_details: bool = False
    creates_urgency: bool = False
    requests_money_transfer: bool = False
    mentions_investment_returns: bool = False
    detected_language: str = "en"

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
# URL/phone extraction is language-independent (digits and URL syntax
# don't change across languages), so these two patterns are shared
# across all three languages rather than duplicated per-language.


# ---------------------------------------------------------------------------
# English patterns (the original, most-tested set)
# ---------------------------------------------------------------------------

_EN_OTP_REQUEST_KEYWORDS = re.compile(
    r"\b(?:send|reply (?:with|to)|share|provide|enter|confirm (?:with|using)|"
    r"give (?:us|me)|verify)\b[^.!?]{0,40}\b(?:otp|one[- ]time (?:password|pin|code)|"
    r"verification code|security code)\b"
    r"|"
    r"\b(?:otp|one[- ]time (?:password|pin|code)|verification code|security code)\b"
    r"[^.!?]{0,40}\b(?:to (?:us|verify|confirm)|required|needed)\b",
    re.IGNORECASE,
)
_EN_CARD_KEYWORDS = re.compile(r"\b(card number|cvv|card details|pin number|expiry date)\b", re.IGNORECASE)
_EN_URGENCY_KEYWORDS = re.compile(
    r"\b(urgent|immediately|act now|expire[sd]? (?:today|soon|in \d+)|last chance|"
    r"account (?:will be |has been )?(?:suspended|blocked|closed|frozen)|"
    r"within \d+ (?:hours?|minutes?))\b",
    re.IGNORECASE,
)
_EN_MONEY_TRANSFER_KEYWORDS = re.compile(
    r"\b(send money|transfer (?:funds|money)|wire transfer|pay(?:ment)? (?:now|immediately|required)|"
    r"deposit (?:required|now))\b",
    re.IGNORECASE,
)
_EN_INVESTMENT_KEYWORDS = re.compile(
    r"\b(guaranteed returns?|double your (?:money|investment)|risk[- ]free|"
    r"investment opportunity|high returns?|crypto investment)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# French patterns
# ---------------------------------------------------------------------------

_FR_OTP_REQUEST_KEYWORDS = re.compile(
    r"\b(?:envoyez?|renvoyez?|partagez?|indiquez?|entrez?|confirmez?|"
    r"donnez[- ]nous|v[ée]rifiez?)\b[^.!?]{0,40}\b(?:otp|code (?:unique|de v[ée]rification|"
    r"de s[ée]curit[ée])|mot de passe (?:unique|à usage unique))\b"
    r"|"
    r"\b(?:otp|code (?:unique|de v[ée]rification|de s[ée]curit[ée]))\b"
    r"[^.!?]{0,40}\b(?:requis|n[ée]cessaire|pour (?:v[ée]rifier|confirmer))\b",
    re.IGNORECASE,
)
_FR_CARD_KEYWORDS = re.compile(
    r"\b(num[ée]ro de carte|cvv|d[ée]tails? (?:de |du )?carte|code pin|date d'expiration)\b",
    re.IGNORECASE,
)
_FR_URGENCY_KEYWORDS = re.compile(
    r"\b(urgent|imm[ée]diatement|agissez maintenant|expire (?:aujourd'hui|bient[ôo]t)|"
    r"derni[èe]re chance|compte (?:sera |a [ée]t[ée] )?(?:suspendu|bloqu[ée]|ferm[ée]|gel[ée])|"
    r"dans les? \d+ (?:heures?|minutes?))\b",
    re.IGNORECASE,
)
_FR_MONEY_TRANSFER_KEYWORDS = re.compile(
    r"\b(envoyez? (?:de l'argent|des fonds)|virement (?:bancaire|imm[ée]diat)|"
    r"paiement (?:maintenant|imm[ée]diat|requis)|d[ée]p[ôo]t (?:requis|maintenant))\b",
    re.IGNORECASE,
)
_FR_INVESTMENT_KEYWORDS = re.compile(
    r"\b(rendements? garantis?|doublez votre (?:argent|investissement)|sans risque|"
    r"opportunit[ée] d'investissement|rendements? [ée]lev[ée]s?|investissement crypto)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Kreol Morisyen patterns
# ---------------------------------------------------------------------------

_CR_OTP_REQUEST_KEYWORDS = re.compile(
    r"\b(?:anvoy|donn|montre|konfirm)\b[^.!?]{0,40}\b(?:otp|kod)\b"
    r"|"
    r"\b(?:otp|kod)\b[^.!?]{0,40}\b(?:pou verifie|bizin|neseser)\b",
    re.IGNORECASE,
)
_CR_CARD_KEYWORDS = re.compile(r"\b(nimero kart|kod pin|dat ekspirasion)\b", re.IGNORECASE)
_CR_URGENCY_KEYWORDS = re.compile(
    r"\b(irzan|tousuit|zordi mem|dernie sans|"
    r"kont (?:pou |finn )?(?:sispann|bloke|ferme)|"
    r"dan \d+ (?:er|minit))\b",
    re.IGNORECASE,
)
_CR_MONEY_TRANSFER_KEYWORDS = re.compile(
    r"\b(anvoy larzan|transfer larzan|peyman (?:tousuit|neseser))\b",
    re.IGNORECASE,
)
_CR_INVESTMENT_KEYWORDS = re.compile(
    r"\b(garanti retour|dibout ou larzan|san risk|"
    r"opportinite investisman|gro profi)\b",
    re.IGNORECASE,
)


_PATTERNS_BY_LANGUAGE = {
    "en": {
        "otp": _EN_OTP_REQUEST_KEYWORDS,
        "card": _EN_CARD_KEYWORDS,
        "urgency": _EN_URGENCY_KEYWORDS,
        "money": _EN_MONEY_TRANSFER_KEYWORDS,
        "investment": _EN_INVESTMENT_KEYWORDS,
    },
    "fr": {
        "otp": _FR_OTP_REQUEST_KEYWORDS,
        "card": _FR_CARD_KEYWORDS,
        "urgency": _FR_URGENCY_KEYWORDS,
        "money": _FR_MONEY_TRANSFER_KEYWORDS,
        "investment": _FR_INVESTMENT_KEYWORDS,
    },
    "cr": {
        "otp": _CR_OTP_REQUEST_KEYWORDS,
        "card": _CR_CARD_KEYWORDS,
        "urgency": _CR_URGENCY_KEYWORDS,
        "money": _CR_MONEY_TRANSFER_KEYWORDS,
        "investment": _CR_INVESTMENT_KEYWORDS,
    },
}


def extract_indicators(message_text: str) -> IndicatorResult:
    """
    Pure function except for the language-detection step, which is
    itself deterministic (same input always detects the same
    language). Matches this project's "explanations a person can
    audit" principle from entity_matcher.py.

    Detects the message's language first (see app/language_detector.py)
    and applies that language's keyword patterns, a French message is
    checked against French urgency/OTP/etc. phrasing, not English.
    Falls back to English's patterns if the detected language somehow
    isn't in _PATTERNS_BY_LANGUAGE (should not happen given
    detect_language()'s three-value contract, but fails toward the
    most-tested pattern set rather than crashing).
    """
    language = detect_language(message_text)
    patterns = _PATTERNS_BY_LANGUAGE.get(language, _PATTERNS_BY_LANGUAGE["en"])

    return IndicatorResult(
        urls=_URL_RE.findall(message_text),
        phone_numbers=_PHONE_RE.findall(message_text),
        requests_otp=bool(patterns["otp"].search(message_text)),
        requests_card_details=bool(patterns["card"].search(message_text)),
        creates_urgency=bool(patterns["urgency"].search(message_text)),
        requests_money_transfer=bool(patterns["money"].search(message_text)),
        mentions_investment_returns=bool(patterns["investment"].search(message_text)),
        detected_language=language,
    )
