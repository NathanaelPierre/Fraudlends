"""
Phone number analysis tests. Two real, related bugs were found and
fixed while building the underlying data (registry_data.py's
KNOWN_OFFICIAL_PHONE_NUMBERS), not the matching logic itself:

1. A data-entry typo: MCB's number was stored with an extra digit,
   causing the real number to fail to match and be reported as a
   mismatch against itself.
2. Investigating that typo surfaced a more serious underlying problem:
   the stored number was also simply wrong, MCB's actually-sourced
   number is +230 202 5000, not the number originally entered. A
   second entry (for Bank One) had no real source citation behind it
   at all and had been fabricated rather than found. Both are fixed:
   MCB's number now matches its real source citation, and the
   unsourced Bank One entry was removed entirely rather than guessed
   at, exactly the kind of unverified claim this project's whole
   registry-verification philosophy exists to avoid making.
"""
from app.phone_analyzer import analyze_phone, normalize_phone

MCB = "The Mauritius Commercial Bank Ltd"


def test_normalize_phone_strips_all_non_digits():
    assert normalize_phone("+230 202 5000") == "2302025000"
    assert normalize_phone("230-202-5000") == "2302025000"
    assert normalize_phone("(230) 202-5000") == "2302025000"


def test_real_number_with_plus_prefix_matches_claimed_entity():
    result = analyze_phone("+230 202 5000", MCB)
    assert result.status == "matches_claimed_entity"


def test_real_number_with_dashes_matches_claimed_entity():
    result = analyze_phone("230-202-5000", MCB)
    assert result.status == "matches_claimed_entity"


def test_real_number_with_no_formatting_matches_claimed_entity():
    result = analyze_phone("2302025000", MCB)
    assert result.status == "matches_claimed_entity"


def test_fake_number_claiming_to_be_mcb_flagged_as_mismatch():
    result = analyze_phone("+230 999 9999", MCB)
    assert result.status == "known_number_mismatch"
    assert result.matched_entity == MCB


def test_different_real_banks_number_flagged_as_mismatch_not_matched():
    result = analyze_phone("+230 402 1000", MCB)
    assert result.status == "known_number_mismatch"


def test_empty_phone_returns_no_phone_status():
    result = analyze_phone("", MCB)
    assert result.status == "no_phone"


def test_claimed_entity_with_no_known_numbers_does_not_error():
    result = analyze_phone("+230 555 5555", "Some Entity With No Known Number")
    assert result.status == "unknown_number"


def test_unknown_number_with_no_claimed_sender():
    result = analyze_phone("+230 555 5555", None)
    assert result.status == "unknown_number"


def test_known_number_belonging_to_a_different_entity_flagged():
    result = analyze_phone("+230 402 1000", None)
    assert result.status == "known_number_mismatch"
    assert result.matched_entity == "Absa Bank (Mauritius) Limited"
