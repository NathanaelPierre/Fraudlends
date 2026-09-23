"""
Entity matcher tests, the core FraudLens differentiator. These
specifically encode two real bugs found and fixed during development,
so they can never silently regress:

1. rapidfuzz's default WRatio scorer does partial or substring
   matching, which badly overmatches short institution names sharing
   common words such as "Bank" or "Limited". "Tranz Digital Bank"
   scored 85.5 percent against "AfrAsia Bank Limited" under WRatio
   despite sharing no real similarity. Fixed by switching to
   token_sort_ratio.

2. Even with the corrected scorer, a 95 percent verified threshold was
   too permissive for single-character typos on short strings.
   "Absaa Bank Mauritius" (one extra letter versus the real "Absa Bank
   Mauritius") scored 97.4 percent, above the old threshold, and would
   have incorrectly confirmed a likely-impersonation name as fully
   verified. Fixed by raising the threshold to 98 percent.
"""
import pytest
from app.entity_matcher import match_entity, normalize_name


@pytest.fixture()
def seeded_db(db_session):
    from app import models

    entities = [
        ("Absa Bank (Mauritius) Limited", "BOM"),
        ("MCB Ltd", "BOM"),
        ("AfrAsia Bank Limited", "BOM"),
        ("Bank One Limited", "BOM"),
    ]
    for name, source in entities:
        db_session.add(models.RegistryEntity(
            name=name, normalized_name=normalize_name(name), source=source, status="Active"
        ))
    db_session.commit()
    return db_session


def test_no_sender_given(seeded_db):
    result = match_entity(seeded_db, None)
    assert result["status"] == "no_sender_given"


def test_empty_string_sender_treated_as_no_sender(seeded_db):
    result = match_entity(seeded_db, "   ")
    assert result["status"] == "no_sender_given"


def test_exact_name_verifies(seeded_db):
    result = match_entity(seeded_db, "MCB Ltd")
    assert result["status"] == "verified"
    assert result["matched_entity"] == "MCB Ltd"


def test_legitimate_variation_with_punctuation_verifies(seeded_db):
    result = match_entity(seeded_db, "ABSA BANK (MAURITIUS) LTD.")
    assert result["status"] == "verified"
    assert result["matched_entity"] == "Absa Bank (Mauritius) Limited"


def test_legitimate_short_form_verifies(seeded_db):
    result = match_entity(seeded_db, "Absa Bank Mauritius")
    assert result["status"] == "verified"


def test_completely_unrelated_fake_name_not_found(seeded_db):
    """
    Regression test for the WRatio substring-matching bug: this exact
    name, "Tranz Digital Bank", the real fake entity named in Bank of
    Mauritius's January 2026 alert, previously scored 85.5 percent
    against "AfrAsia Bank Limited" purely because both contain "bank"
    as a substring, incorrectly returning name_mismatch. It must be
    correctly recognized as unrelated.
    """
    result = match_entity(seeded_db, "Tranz Digital Bank")
    assert result["status"] == "not_found"


def test_unrelated_generic_name_not_found(seeded_db):
    result = match_entity(seeded_db, "Random Fake Crypto Co")
    assert result["status"] == "not_found"


def test_obvious_typo_of_real_name_flagged_as_mismatch(seeded_db):
    result = match_entity(seeded_db, "AfrAsia Bnak Limited")
    assert result["status"] == "name_mismatch"
    assert result["matched_entity"] == "AfrAsia Bank Limited"


def test_single_character_typo_flagged_as_mismatch_not_verified(seeded_db):
    """
    Regression test for the threshold bug: a single added character,
    "Absaa" versus "Absa", scored 97.4 percent, above the original 95
    percent threshold, and would have been incorrectly marked as a
    fully verified match to the real entity rather than flagged as a
    suspicious near-typo. This is precisely the kind of one-character
    impersonation a scammer would actually use, so it must not
    silently verify.
    """
    result = match_entity(seeded_db, "Absaa Bank Mauritius")
    assert result["status"] == "name_mismatch"
    assert result["matched_entity"] == "Absa Bank (Mauritius) Limited"


def test_short_names_sharing_a_common_word_do_not_false_flag_as_mismatch(seeded_db):
    """
    Regression test found against the real registry data: "Absa Bank"
    (a legitimate short form of a real bank) scored 76.2 percent
    against the unrelated "AfrAsia Bank Limited" purely because both
    are short, two-word strings sharing the word "bank" once
    normalized. This must not be flagged as a suspicious impersonation
    of AfrAsia, since Absa is itself a real, different, legitimate
    bank. Fixed by requiring a minimum claim length before allowing a
    name_mismatch classification.
    """
    result = match_entity(seeded_db, "Absa Bank")
    assert result["status"] != "name_mismatch"


def test_empty_registry_returns_registry_unavailable(db_session):
    """If the registry has not been synced or seeded yet, the matcher
    must say so explicitly rather than silently return not_found for
    every check, which would look like a real finding instead of a
    data problem."""
    result = match_entity(db_session, "Any Bank Name")
    assert result["status"] == "registry_unavailable"


def test_normalize_name_strips_suffixes_and_punctuation():
    assert normalize_name("Absa Bank (Mauritius) Ltd.") == normalize_name("ABSA BANK MAURITIUS LIMITED")


def test_normalize_name_collapses_whitespace():
    assert normalize_name("MCB   Ltd") == normalize_name("MCB Ltd")
