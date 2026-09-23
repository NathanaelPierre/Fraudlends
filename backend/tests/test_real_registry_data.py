"""
Tests against the real registry data (registry_data.py, compiled from
Bank of Mauritius's own official participant list) and the known-alias
resolution feature, as opposed to test_entity_matcher.py's synthetic
seeded_db fixture, which tests the matching algorithm in isolation.

These tests specifically caught two real bugs when run against actual
data (not hand-picked test entities), both fixed and encoded here:

1. Common public abbreviations ("MCB", "HSBC", "SBM") did not reliably
   match their much longer formal legal names in the registry, for
   example "MCB" scored only 42.9 percent against "The Mauritius
   Commercial Bank Ltd", even though these are the names real
   Mauritian users would actually type. Fixed by loading known aliases
   as additional searchable registry entries.

2. Short legitimate names sharing a common word could still trigger a
   false name_mismatch against a different real entity: "Absa Bank"
   scored 76.2 percent against "AfrAsia Bank Limited". Fixed with a
   minimum claim length before allowing name_mismatch classification.
"""
import pytest
from app.registry_sync import sync_registry
from app.entity_matcher import match_entity


@pytest.fixture()
def real_registry_db(db_session, monkeypatch):
    """
    Runs the actual sync_registry() against the test database, so
    these tests exercise the real data pipeline end-to-end rather than
    hand-picked synthetic entities.
    """
    import app.registry_sync as registry_sync_module
    monkeypatch.setattr(registry_sync_module, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    sync_registry()
    return db_session


def test_real_registry_loads_expected_entity_count(real_registry_db):
    from app import models
    count = real_registry_db.query(models.RegistryEntity).count()
    assert count >= 60


def test_common_bank_abbreviation_mcb_verifies(real_registry_db):
    result = match_entity(real_registry_db, "MCB")
    assert result["status"] == "verified"
    assert result["matched_entity"] == "The Mauritius Commercial Bank Ltd"


def test_common_bank_abbreviation_hsbc_verifies(real_registry_db):
    result = match_entity(real_registry_db, "HSBC")
    assert result["status"] == "verified"


def test_common_bank_abbreviation_sbm_verifies(real_registry_db):
    result = match_entity(real_registry_db, "SBM")
    assert result["status"] == "verified"


def test_real_fake_entity_from_bom_alert_not_found(real_registry_db):
    """
    "Tranz Digital Bank" is the actual fake entity named in Bank of
    Mauritius's real January 2026 public alert about an unlicensed
    entity impersonating a digital bank. It must correctly show as not
    found in the real registry, not accidentally match anything.
    """
    result = match_entity(real_registry_db, "Tranz Digital Bank")
    assert result["status"] == "not_found"


def test_short_legitimate_bank_name_does_not_false_flag_against_different_bank(real_registry_db):
    result = match_entity(real_registry_db, "Absa Bank")
    assert result["status"] != "name_mismatch"


def test_full_legal_name_verifies_against_real_data(real_registry_db):
    result = match_entity(real_registry_db, "Mauritius Telecom Ltd")
    assert result["status"] == "verified"


def test_plausible_fake_name_riffing_on_real_brand_not_falsely_verified(real_registry_db):
    """
    A plausible-sounding fake name that isn't literally a typo of a
    real entity, for example a scammer inventing "MyT Rebate Services"
    to sound related to Mauritius Telecom, should not be verified. It
    is reasonable for this to report as not_found rather than
    name_mismatch, since the registry check alone cannot distinguish a
    genuinely new, unrelated small business from an invented scam
    name, that distinction is what the AI layer is for.
    """
    result = match_entity(real_registry_db, "MyT Rebate Services")
    assert result["status"] != "verified"


def test_fsc_licensed_forex_broker_verifies(real_registry_db):
    """
    Confirms the FSC (non-bank financial services) data actually
    loaded and matches — a genuinely current, real-world example of an
    FSC-licensed forex broker, distinct from BoM's bank-only list.
    """
    result = match_entity(real_registry_db, "Exinity Limited")
    assert result["status"] == "verified"
    assert result["source"] == "FSC"


def test_fxtm_brand_name_resolves_to_formal_licensed_entity(real_registry_db):
    """
    Regression test for the same class of gap found earlier with "MCB":
    the globally-recognized consumer brand "FXTM" does not literally
    match its formal FSC-licensed entity name "Exinity Limited" via
    fuzzy matching alone, and needed the same known-alias treatment.
    """
    result = match_entity(real_registry_db, "FXTM")
    assert result["status"] == "verified"
    assert result["matched_entity"] == "Exinity Limited"


def test_revoked_fsc_entity_returns_revoked_not_verified_or_not_found(real_registry_db):
    """
    A real, named entity from an actual dated FSC public notice about
    a surrendered or revoked license must surface as its own distinct
    "revoked" status, not silently pass as "verified" (which would
    wrongly imply an active license) or be discarded as "not_found"
    (which would lose the real, sourced fact that this specific
    license is no longer active).
    """
    result = match_entity(real_registry_db, "Trade T Capital Markets")
    assert result["status"] == "revoked"
    assert result["matched_entity"] == "Trade T Capital Markets"
    assert result["status_detail"] is not None
    assert "surrendered" in result["status_detail"].lower() or "2026" in result["status_detail"]


def test_another_revoked_entity_from_2025(real_registry_db):
    result = match_entity(real_registry_db, "Paka Group")
    assert result["status"] == "revoked"
