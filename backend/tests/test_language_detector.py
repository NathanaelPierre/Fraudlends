"""
Language detection tests. The core finding this module exists to
address: the general-purpose langdetect library has no trained
category for Kreol Morisyen at all and misclassifies real Kreol text
as French (confirmed directly: "Kont ou pou sispann zordi" and "Anvoy
OTP-la tousuit" both came back "fr" from langdetect alone). Fixed with
a targeted Kreol marker-word check that runs before langdetect.
"""
from app.language_detector import detect_language


def test_english_detected():
    assert detect_language("Your account will be suspended today") == "en"


def test_english_otp_message_detected():
    assert detect_language("Verify your OTP now") == "en"


def test_french_detected():
    assert detect_language("Votre compte sera suspendu aujourd'hui") == "fr"


def test_french_formal_message_detected():
    assert detect_language("Veuillez vérifier votre code de sécurité") == "fr"


def test_kreol_detected_where_langdetect_alone_would_fail():
    """
    Regression test for the core bug this module exists to fix:
    langdetect alone classifies this as French. It must be correctly
    identified as Kreol via the marker-word check.
    """
    result = detect_language("Kont ou pou sispann zordi si ou pa verifie")
    assert result == "cr"


def test_another_real_kreol_scam_style_message_detected():
    result = detect_language("Anvoy OTP-la tousuit avan nou bloke kont ou")
    assert result == "cr"


def test_kreol_with_common_short_words_detected():
    result = detect_language("Bizin verifie kont labank ou zordi mem")
    assert result == "cr"


def test_short_ambiguous_text_defaults_to_english():
    assert detect_language("MCB") == "en"


def test_empty_string_defaults_to_english():
    assert detect_language("") == "en"


def test_whitespace_only_defaults_to_english():
    assert detect_language("   ") == "en"


def test_french_sentence_with_single_incidental_marker_word_stays_french():
    """
    A legitimate French sentence containing exactly one word that
    happens to overlap with the Kreol marker list ("la" as a normal
    French article) must not be misclassified, a single marker match
    is not strong enough evidence on its own, hence the
    MIN_KREOL_MARKER_MATCHES threshold of 2.
    """
    result = detect_language("La banque a confirmé la transaction")
    assert result == "fr"


def test_french_sentence_with_sa_stays_french():
    result = detect_language("Sa y est, tout est fini")
    assert result == "fr"


def test_kreol_with_multiple_short_common_words_detected():
    result = detect_language("Nou fer sa ansam")
    assert result == "cr"


def test_kreol_urgency_phrase_with_only_one_original_marker_now_detected():
    """
    Regression test: this phrase originally had only one marker match
    ("pou"), below the threshold, despite containing several genuinely
    Kreol-specific words (irzan, sispann, dan, kont). Fixed by adding
    those words to the marker list.
    """
    result = detect_language("Irzan: kont ou pou sispann dan 24 er")
    assert result == "cr"


def test_french_reflexive_sentence_does_not_false_positive_as_kreol():
    """
    Regression test for a real bug found while extending the marker
    list: adding "ou" and "se" as markers (to catch more Kreol
    phrasing) caused this completely ordinary French sentence to
    misclassify as Kreol, since both words are also common, ambiguous
    French words ("ou" = "or", "se" = reflexive pronoun). Fixed by
    reverting those two specific additions.
    """
    result = detect_language("Il se dirige vers la banque")
    assert result == "fr"


def test_french_with_ou_as_conjunction_stays_french():
    result = detect_language("Vous ou votre famille pouvez nous contacter")
    assert result == "fr"
