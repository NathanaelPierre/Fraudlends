"""
Sender extraction tests. One real bug was found and fixed during
development: matched_text originally always showed the registry's
formal entity name, never the user's own typed words ("MCB"), because
the fallback logic tried to re-find the formal name's own words inside
the original text, which never matches when the user typed an alias
rather than the formal name. Fixed by building the search pattern from
each candidate registry row's own normalized name or alias and
searching the original text directly, so the actual matched substring
(the user's own words) is captured at match time, not reconstructed
afterward.
"""
from app.sender_extractor import extract_sender_from_text


def _seed_registry(db_session):
    from app import models
    from app.entity_matcher import normalize_name

    entities = [
        ("The Mauritius Commercial Bank Ltd", "BOM"),
        ("Absa Bank (Mauritius) Limited", "BOM"),
        ("AfrAsia Bank Limited", "BOM"),
        ("Mauritius Telecom Ltd", "BOM"),
    ]
    for name, source in entities:
        db_session.add(models.RegistryEntity(
            name=name, normalized_name=normalize_name(name), source=source, status="Active"
        ))
    db_session.add(models.RegistryEntity(
        name="The Mauritius Commercial Bank Ltd", normalized_name=normalize_name("MCB"),
        source="BOM", status="Active", license_type="Known Alias",
    ))
    db_session.commit()


def test_no_sender_in_ordinary_message(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "Hey, are we still on for lunch tomorrow?")
    assert result.detected_sender is None
    assert result.matched_text is None


def test_alias_detected_and_resolved_to_formal_name(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "MCB: Your account will be suspended.")
    assert result.detected_sender == "The Mauritius Commercial Bank Ltd"


def test_matched_text_shows_the_users_own_words_not_the_formal_name(db_session):
    """
    Regression test for the real bug found during development:
    matched_text must reflect what the user actually typed ("MCB"),
    not the registry's formal name, so a "shown as reasoning" UI can
    quote the user's own words back to them.
    """
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "MCB: Your account will be suspended.")
    assert result.matched_text == "MCB"
    assert result.matched_text != result.detected_sender


def test_formal_name_typed_directly_is_also_detected(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "The Mauritius Commercial Bank Ltd requires verification")
    assert result.detected_sender == "The Mauritius Commercial Bank Ltd"
    assert "Mauritius Commercial Bank" in result.matched_text


def test_case_insensitive_matching(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "AFRASIA BANK: urgent action required")
    assert result.detected_sender == "AfrAsia Bank Limited"
    assert result.matched_text == "AFRASIA BANK"


def test_short_alias_does_not_match_inside_an_unrelated_word(db_session):
    """
    Word-boundary safety: "MCB" must not match as a substring of a
    longer, unrelated word like "MCBX" — a false positive with no
    basis, exactly the class of bug entity_matcher.py has already had
    to guard against elsewhere in this project.
    """
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "MCBX Corp sent me an email")
    assert result.detected_sender is None


def test_empty_message_returns_no_sender(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "")
    assert result.detected_sender is None


def test_whitespace_only_message_returns_no_sender(db_session):
    _seed_registry(db_session)
    result = extract_sender_from_text(db_session, "   ")
    assert result.detected_sender is None


def test_empty_registry_returns_no_sender_gracefully(db_session):
    """No registry data loaded at all must not error, same fail-honest
    posture as entity_matcher.py's registry_unavailable status, just
    returning "nothing detected" rather than crashing."""
    result = extract_sender_from_text(db_session, "MCB: verify your account")
    assert result.detected_sender is None


def test_longest_match_wins_when_multiple_candidates_present(db_session):
    """
    A message mentioning both a short alias and a longer formal name
    should resolve to the longer, more specific match — the same
    "longer match is more reliable" principle already used in
    entity_matcher.py's threshold design.
    """
    _seed_registry(db_session)
    result = extract_sender_from_text(
        db_session, "Regarding MCB and also The Mauritius Commercial Bank Ltd directly"
    )
    assert result.detected_sender == "The Mauritius Commercial Bank Ltd"
    assert len(result.matched_text) > len("MCB")


def test_documented_limitation_mentioning_an_entity_is_not_the_same_as_being_from_it(db_session):
    """
    Honest limitation, not a bug: this module detects a known entity
    name appearing anywhere in the text, it cannot distinguish "this
    message is from X" from "this message merely mentions X". A
    message that references an institution in passing will still
    "detect" that institution as the claimed sender. This is exactly
    why the frontend surfaces the detection as visible reasoning (the
    user's own words, quoted back) rather than silently acting on it
    as a confirmed fact.
    """
    _seed_registry(db_session)
    result = extract_sender_from_text(
        db_session, "I work at a small startup, not at Mauritius Telecom or any big company"
    )
    assert result.detected_sender == "Mauritius Telecom Ltd"
