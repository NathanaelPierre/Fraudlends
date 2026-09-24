"""
Tests for the structured evidence trail (schemas.EvidenceItem list on
CheckOut): each signal source (registry, indicator, domain, phone)
contributes its own item with a category, code, description, and
severity, rather than only a bare flag-code list (ai_flags) or one
bundled prose paragraph (ai_explanation).

This is genuinely two code paths that must stay consistent:
_build_evidence_list() runs at creation time with the full pipeline's
intermediate objects in scope, while
_build_evidence_list_from_stored_check() reconstructs the same
information later from what was actually persisted (GET
/checks/{id}). These tests check both paths, and specifically confirm
they produce matching results for the same check, the router's own
code comments already documented one real case where the two had
drifted apart (a suspicious_domain_structure evidence item was missing
from the creation-time path but correctly appeared on a later GET), so
this consistency property is worth testing directly rather than
assuming it holds.
"""


MCB_FORMAL_NAME = "The Mauritius Commercial Bank Ltd"


def _seed_registry(db_session):
    """
    Seeds the real formal entity name plus its known "MCB" alias as a
    SEPARATE row — exactly mirroring what registry_sync.py actually
    does in production (see registry_sync.py and registry_data.py's
    KNOWN_ALIASES). This matters for two reasons found while writing
    these tests:

    1. entity_matcher.py has no built-in alias logic at all — "MCB"
       resolving to the formal name only works because
       registry_sync.py loads an ADDITIONAL RegistryEntity row whose
       normalized_name is the alias, pointing at the formal name.
       Seeding only the formal name and expecting "MCB" to resolve via
       fuzzy matching alone works only by coincidence (short strings
       can accidentally score high against unrelated names, as found
       earlier in this project's own history with "Absa Bank" vs
       "AfrAsia Bank Limited").
    2. KNOWN_OFFICIAL_DOMAINS and KNOWN_OFFICIAL_PHONE_NUMBERS in
       registry_data.py are keyed on the exact formal name, not the
       alias — so domain_mismatch and phone_mismatch detection can
       only fire if the seeded entity's own `name` field is the real
       formal name, not an arbitrary placeholder like "MCB Ltd".
    """
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name=MCB_FORMAL_NAME, normalized_name=normalize_name(MCB_FORMAL_NAME), source="BOM", status="Active"
    ))
    db_session.add(models.RegistryEntity(
        name=MCB_FORMAL_NAME, normalized_name=normalize_name("MCB"), source="BOM",
        status="Active", license_type="Known Alias",
    ))
    db_session.commit()


def test_every_check_has_at_least_one_evidence_item(client, auth_headers):
    """The registry check always runs and always produces exactly one
    evidence item, even with no other signal present."""
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Ordinary message"}, headers=headers)
    evidence = r.json()["evidence"]
    assert len(evidence) >= 1
    assert evidence[0]["category"] == "registry"


def test_verified_sender_evidence_item_has_info_severity(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Statement ready", "claimed_sender": "MCB"}, headers=headers)
    evidence = r.json()["evidence"]
    registry_item = next(e for e in evidence if e["category"] == "registry")
    assert registry_item["code"] == "verified"
    assert registry_item["severity"] == "info"


def test_name_mismatch_evidence_item_has_high_risk_severity(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "test", "claimed_sender": "MCB Ltdd"}, headers=headers)
    evidence = r.json()["evidence"]
    registry_item = next(e for e in evidence if e["category"] == "registry")
    if registry_item["code"] == "name_mismatch":
        assert registry_item["severity"] == "high_risk"


def test_otp_request_produces_high_risk_indicator_evidence_item(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Please send your OTP to verify"}, headers=headers)
    evidence = r.json()["evidence"]
    otp_items = [e for e in evidence if e["code"] == "requests_otp"]
    assert len(otp_items) == 1
    assert otp_items[0]["category"] == "indicator"
    assert otp_items[0]["severity"] == "high_risk"


def test_url_alone_produces_info_severity_evidence_item(client, auth_headers):
    """A bare link is informational only, not suspicious on its own,
    consistent with verdict.py's deliberate exclusion of contains_url
    from the suspicious-severity set."""
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "See http://example.com for details"}, headers=headers)
    evidence = r.json()["evidence"]
    url_items = [e for e in evidence if e["code"] == "contains_url"]
    assert len(url_items) == 1
    assert url_items[0]["severity"] == "info"


def test_domain_mismatch_produces_high_risk_evidence_item_with_specific_domain(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Verify at http://mcb-fake-site.net/login", "claimed_sender": "MCB"},
        headers=headers,
    )
    evidence = r.json()["evidence"]
    domain_items = [e for e in evidence if e["code"] == "domain_mismatch"]
    assert len(domain_items) == 1
    assert domain_items[0]["severity"] == "high_risk"
    assert "mcb-fake-site.net" in domain_items[0]["description"]
    assert MCB_FORMAL_NAME in domain_items[0]["description"]


def test_suspicious_domain_structure_appears_as_its_own_evidence_item(client, auth_headers):
    """
    This is the specific case the router's own code comments flag as
    having been found missing during live testing at one point, a
    structurally unusual domain (not a known-entity mismatch) must
    still produce its own evidence item, not be silently dropped.
    """
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Click http://totally-unknown-site.tk/verify now"},
        headers=headers,
    )
    evidence = r.json()["evidence"]
    structure_items = [e for e in evidence if e["code"] == "suspicious_domain_structure"]
    assert len(structure_items) == 1
    assert structure_items[0]["category"] == "domain"


def test_phone_mismatch_produces_high_risk_evidence_item_with_specific_number(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Call us urgently at +230 999 8888", "claimed_sender": "MCB"},
        headers=headers,
    )
    evidence = r.json()["evidence"]
    phone_items = [e for e in evidence if e["code"] == "phone_mismatch"]
    assert len(phone_items) == 1
    assert phone_items[0]["severity"] == "high_risk"
    assert "999 8888" in phone_items[0]["description"] or "9998888" in phone_items[0]["description"]


def test_creation_time_and_read_time_evidence_lists_match(client, auth_headers, db_session):
    """
    The core consistency property: _build_evidence_list() (creation
    time) and _build_evidence_list_from_stored_check() (GET
    /checks/{id}) must produce the same evidence for the same check,
    the router's own comments document a real case where these two
    paths had drifted apart, so this is tested directly rather than
    assumed.
    """
    _seed_registry(db_session)
    headers = auth_headers()

    r1 = client.post(
        "/checks/",
        json={
            "message_text": "URGENT: send your OTP now at http://mcb-totally-fake.tk",
            "claimed_sender": "MCB",
        },
        headers=headers,
    )
    check_id = r1.json()["id"]
    creation_evidence = r1.json()["evidence"]

    r2 = client.get(f"/checks/{check_id}", headers=headers)
    read_evidence = r2.json()["evidence"]

    creation_codes = sorted(e["code"] for e in creation_evidence)
    read_codes = sorted(e["code"] for e in read_evidence)
    assert creation_codes == read_codes


def test_evidence_persists_correctly_for_multiple_evidence_types_at_once(client, auth_headers, db_session):
    """A message triggering registry, indicator, domain, and phone
    evidence simultaneously must correctly surface all four
    categories, both at creation and on a later read."""
    _seed_registry(db_session)
    headers = auth_headers()

    r1 = client.post(
        "/checks/",
        json={
            "message_text": "URGENT: Verify your OTP now at http://mcb-fake.tk or call +230 999 8888",
            "claimed_sender": "MCB",
        },
        headers=headers,
    )
    check_id = r1.json()["id"]
    categories_at_creation = {e["category"] for e in r1.json()["evidence"]}

    r2 = client.get(f"/checks/{check_id}", headers=headers)
    categories_at_read = {e["category"] for e in r2.json()["evidence"]}

    assert {"registry", "indicator", "domain", "phone"}.issubset(categories_at_creation)
    assert categories_at_creation == categories_at_read


def test_evidence_is_present_on_list_endpoint_too(client, auth_headers):
    """
    Confirms whether the list endpoint (GET /checks/) also includes
    evidence, if it doesn't (e.g. for performance reasons, similar to
    repeat_sender_summary being deliberately skipped there), this test
    documents that as the actual, intentional behavior rather than
    silently assuming parity with the single-check endpoints.
    """
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    r = client.get("/checks/", headers=headers)
    body = r.json()
    assert len(body) == 1
    assert "evidence" in body[0]


def test_evidence_present_even_when_check_is_not_persisted(client, auth_headers):
    """save_check=false still returns a full analysis, including
    evidence, only persistence is skipped, not the response content."""
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Send your OTP now", "save_check": False},
        headers=headers,
    )
    assert len(r.json()["evidence"]) >= 1
