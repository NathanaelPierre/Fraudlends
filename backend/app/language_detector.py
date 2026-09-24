"""
Language detection for incoming message text: English, French, or
Kreol Morisyen (Mauritian Creole).

Important, found during development: the general-purpose langdetect
library has no trained category for Kreol Morisyen at all, it is a
low-resource language with no dedicated model in that library's
training data. Tested directly against real Kreol phrases ("Kont ou
pou sispann zordi", "Anvoy OTP-la tousuit") and both were misclassified
as French, since Kreol is French-lexified and shares substantial
vocabulary with it. A generic detector cannot be trusted to
distinguish the two.

The fix here is a small, targeted marker-word list: spellings and
words that are distinctively Kreol Morisyen and essentially never
appear in standard written French (e.g. "zot", "nou" as a subject
pronoun in this context, "bizin", "morisien" itself). If enough of
these markers appear, the text is classified as Kreol before
langdetect ever runs, langdetect is only used to distinguish English
from French once Kreol has been ruled out, since it handles that
distinction reliably (confirmed directly above).

This is deliberately a real, if imperfect, heuristic, not a claim of
linguistic authority. Mauritian Kreol has no single standardized
spelling system, and this list reflects common informal spelling
patterns rather than an academic orthography. It is expected to
improve over time as more real user text is seen, and is intentionally
kept in one place (KREOL_MARKERS below) so it's easy to extend.
"""
import re
from langdetect import detect, LangDetectException

SupportedLanguage = str  # "en" | "fr" | "cr"

KREOL_MARKERS = {
    "zot", "nou", "sanla", "kifer", "kouma", "kot",
    "morisien", "morisyen", "pou", "gagn", "bizin", "ankor",
    "zordi", "aster", "labank", "tousuit", "kominike", "kass",
    "ki", "sa", "la", "mo", "to", "li", "dimoune", "dimounn",
    # Added after real Kreol scam-phrasing examples were found to be
    # under-detected: "Irzan: kont ou pou sispann dan 24 er" had only
    # one marker match ("pou"), below the 2-marker threshold, despite
    # containing several distinctively Kreol spellings. "ou" and "se"
    # were tried here too but REVERTED — both are also common, ambiguous
    # French words ("ou" = "or", "se" = reflexive pronoun), and adding
    # them caused a real false positive: "Il se dirige vers la banque"
    # (ordinary French) started misclassifying as Kreol. Only genuinely
    # distinctive spellings are kept.
    "irzan", "sispann", "dan", "kont", "konfirm",
    "ferme", "bloke", "montre", "donn", "neseser", "anvoy",
}

_WORD_RE = re.compile(r"[a-zA-Zàâäéèêëïîôöùûüÿçñ]+", re.IGNORECASE)

MIN_KREOL_MARKER_MATCHES = 2


def detect_language(text: str) -> SupportedLanguage:
    """
    Returns "en", "fr", or "cr". Defaults to "en" for empty or
    undetectable text, matching the project's existing English-first
    defaults elsewhere (indicator_extractor.py's keyword lists, etc.)
    rather than guessing.
    """
    if not text or not text.strip():
        return "en"

    words = {w.lower() for w in _WORD_RE.findall(text)}
    marker_matches = words & KREOL_MARKERS

    if len(marker_matches) >= MIN_KREOL_MARKER_MATCHES:
        return "cr"

    try:
        detected = detect(text)
    except LangDetectException:
        return "en"

    if detected == "fr":
        return "fr"
    return "en"
