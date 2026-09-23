"""
End-to-end tests for the core /checks endpoint: submitting a message,
getting a registry-checked verdict back, listing and retrieving past
checks, and confirming per-user isolation.
"""
from app.entity_matcher import normalize_name


def _seed_registry(db_session):
    from app import models

    entities = [
        ("Absa Bank (Mauritius) Limited", "BOM"),
        ("MCB Ltd", "BOM"),
        ("AfrAsia Bank Limited", "BOM"),
    ]
    for name, source in entities:
        db_session.add(models.RegistryEntity(
            name=name, normalized_name=normalize_name(name), source=source, status="Active"
        ))
    db_session.commit()


def test_create_check_with_verified_sender(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Your account statement is ready", "claimed_sender": "MCB Ltd"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "verified"
    assert body["overall_verdict"] == "safe"
    assert body["explanation_source"] == "registry_and_indicators"


def test_create_check_with_impersonation_style_name(client, auth_headers, db_session):
    """The real-world case this feature exists for: a name that looks
    almost right but doesn't exactly match a licensed entity."""
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Urgent: verify your account now", "claimed_sender": "AfrAsia Bnak Limited"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "name_mismatch"
    assert body["overall_verdict"] == "high_risk"
    assert "AfrAsia Bank Limited" in body["ai_explanation"]


def test_create_check_with_unrelated_fake_sender(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Invest now for guaranteed returns", "claimed_sender": "Definitely Not A Real Bank"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "not_found"
    assert body["overall_verdict"] == "suspicious"


def test_create_check_with_no_sender_given(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Some message with no claimed sender"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "no_sender_given"
    assert body["overall_verdict"] == "safe"


def test_create_check_before_registry_seeded(client, auth_headers):
    """No registry data at all, the honest registry_unavailable
    outcome, not a false not_found."""
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Test message", "claimed_sender": "Any Bank"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "registry_unavailable"


def test_create_check_requires_auth(client):
    r = client.post("/checks/", json={"message_text": "Test", "claimed_sender": "MCB"})
    assert r.status_code == 401


def test_create_check_rejects_empty_message(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": ""}, headers=headers)
    assert r.status_code == 422


def test_list_checks_returns_own_only(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers_a = auth_headers(email="checka@fraudlens.mu")
    headers_b = auth_headers(email="checkb@fraudlens.mu")

    client.post("/checks/", json={"message_text": "A's message", "claimed_sender": "MCB Ltd"}, headers=headers_a)
    client.post("/checks/", json={"message_text": "B's message", "claimed_sender": "MCB Ltd"}, headers=headers_b)

    r = client.get("/checks/", headers=headers_a)
    messages = [c["message_text"] for c in r.json()]
    assert "A's message" in messages
    assert "B's message" not in messages


def test_get_single_check_by_id(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post("/checks/", json={"message_text": "Specific check", "claimed_sender": "MCB Ltd"}, headers=headers)
    check_id = r.json()["id"]

    r2 = client.get(f"/checks/{check_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["message_text"] == "Specific check"


def test_get_check_rejects_cross_user_access(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers_a = auth_headers(email="crossa@fraudlens.mu")
    headers_b = auth_headers(email="crossb@fraudlens.mu")

    r = client.post("/checks/", json={"message_text": "A's private check", "claimed_sender": "MCB Ltd"}, headers=headers_a)
    check_id = r.json()["id"]

    r2 = client.get(f"/checks/{check_id}", headers=headers_b)
    assert r2.status_code == 404


def test_get_nonexistent_check_returns_404(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/999999", headers=headers)
    assert r.status_code == 404


def test_filter_checks_by_verdict(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    client.post("/checks/", json={"message_text": "Safe one", "claimed_sender": "MCB Ltd"}, headers=headers)
    client.post("/checks/", json={"message_text": "Suspicious one", "claimed_sender": "Fake Co"}, headers=headers)

    r = client.get("/checks/?verdict=safe", headers=headers)
    assert all(c["overall_verdict"] == "safe" for c in r.json())


def test_pii_is_scrubbed_from_the_stored_and_returned_check(client, auth_headers, db_session):
    """
    End-to-end confirmation that PII scrubbing actually fires through
    the real /checks endpoint, not just in isolation (see
    test_pii_scrubber.py for the scrubber's own unit tests).
    """
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={
            "message_text": "MCB: verify your OTP 483921 immediately",
            "claimed_sender": "MCB Ltd",
        },
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "483921" not in body["message_text"]
    assert "[REDACTED CODE]" in body["message_text"]


def test_pii_is_scrubbed_even_when_save_check_is_false(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={
            "message_text": "Card 4111 1111 1111 1111 was charged",
            "claimed_sender": "MCB Ltd",
            "save_check": False,
        },
        headers=headers,
    )
    body = r.json()
    assert "4111 1111 1111 1111" not in body["message_text"]
    assert "[CARD ENDING 1111]" in body["message_text"]
