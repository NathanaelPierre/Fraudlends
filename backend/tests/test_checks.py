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


def test_registry_status_detail_is_a_structured_field_not_only_in_prose(client, auth_headers, db_session):
    """
    registry_status_detail must appear as its own structured field in
    the API response, not only embedded in the free-text
    ai_explanation string, so a frontend or future feature can
    filter/query on it without parsing prose.
    """
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="Trade T Capital Markets",
        normalized_name=normalize_name("Trade T Capital Markets"),
        source="FSC",
        status="Surrendered — Global Business & Investment Dealer licence, 30 June 2026",
    ))
    db_session.commit()

    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "Invest with us", "claimed_sender": "Trade T Capital Markets"},
        headers=headers,
    )
    body = r.json()
    assert body["registry_match_status"] == "revoked"
    assert body["registry_status_detail"] is not None
    assert "Surrendered" in body["registry_status_detail"]


def test_registry_status_detail_reflects_actual_stored_status_for_verified_entities(client, auth_headers, db_session):
    """
    status_detail always reflects the registry's real stored status
    value, including "Active" for an ordinary verified match — this is
    more consistent than special-casing it to None outside the
    "revoked" case, since the field's whole purpose is to expose
    whatever status the registry actually has on file, not just the
    cases considered noteworthy.
    """
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post("/checks/", json={"message_text": "Statement", "claimed_sender": "MCB Ltd"}, headers=headers)
    assert r.json()["registry_status_detail"] == "Active"


def test_single_box_input_auto_detects_sender_from_message_text(client, auth_headers, db_session):
    """
    The core single-box flow: no claimed_sender provided at all, the
    sender is inferred from the message's own text (see
    app/sender_extractor.py) and the registry check runs against it.
    """
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "MCB Ltd: Your account will be suspended. Verify your OTP now."},
        headers=headers,
    )
    body = r.json()
    assert body["claimed_sender"] == "MCB Ltd"
    assert body["sender_auto_detected"] is True
    assert body["sender_detection_source_text"] is not None
    assert body["registry_match_status"] == "verified"


def test_auto_detection_reasoning_appears_in_explanation_text(client, auth_headers, db_session):
    """The detection must be visible reasoning in the prose
    explanation, not only a structured field a UI might not render."""
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "MCB Ltd: verify your OTP now."},
        headers=headers,
    )
    explanation = r.json()["ai_explanation"]
    assert "Klaro noticed" in explanation
    assert "MCB Ltd" in explanation


def test_explicit_claimed_sender_is_not_marked_auto_detected(client, auth_headers, db_session):
    """When the caller DOES provide claimed_sender explicitly (the
    still-supported original flow), sender_auto_detected must be
    False, no detection reasoning should be fabricated for something
    the user stated directly."""
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Your account is ready", "claimed_sender": "MCB Ltd"},
        headers=headers,
    )
    body = r.json()
    assert body["sender_auto_detected"] is False
    assert body["sender_detection_source_text"] is None
    assert "Klaro noticed" not in body["ai_explanation"]


def test_no_detectable_sender_still_produces_a_valid_check(client, auth_headers):
    """A message naming no known institution at all must still
    complete normally (registry status: no_sender_given), not error."""
    headers = auth_headers()

    r = client.post("/checks/", json={"message_text": "Hey, are we still on for lunch?"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["claimed_sender"] is None
    assert body["sender_auto_detected"] is False
    assert body["registry_match_status"] == "no_sender_given"


def test_french_message_produces_french_explanation_and_evidence(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "URGENT: Votre compte MCB Ltd sera suspendu. Veuillez envoyer votre OTP pour confirmer."},
        headers=headers,
    )
    body = r.json()
    assert body["detected_language"] == "fr"
    assert "expéditeur" in body["ai_explanation"].lower() or "correspond" in body["ai_explanation"].lower()
    assert any("expéditeur" in e["description"].lower() or "correspond" in e["description"].lower() for e in body["evidence"])


def test_kreol_message_produces_kreol_explanation_and_evidence(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Irzan: kont MCB Ltd ou pou sispann. Anvoy OTP-la pou konfirm."},
        headers=headers,
    )
    body = r.json()
    assert body["detected_language"] == "cr"
    assert "expediter" in body["ai_explanation"].lower() or "matche" in body["ai_explanation"].lower()


def test_creation_time_and_read_time_evidence_stay_in_the_same_language(client, auth_headers, db_session):
    """
    The core consistency property for multilingual evidence: GET
    /checks/{id} must reconstruct evidence in the SAME language the
    check was originally created and explained in, not silently
    default back to English — verified live during development, this
    encodes it as a permanent regression test.
    """
    _seed_registry(db_session)
    headers = auth_headers()

    r1 = client.post(
        "/checks/",
        json={"message_text": "Irzan: kont MCB Ltd ou pou sispann. Anvoy OTP-la pou konfirm."},
        headers=headers,
    )
    check_id = r1.json()["id"]
    creation_descriptions = [e["description"] for e in r1.json()["evidence"]]

    r2 = client.get(f"/checks/{check_id}", headers=headers)
    read_descriptions = [e["description"] for e in r2.json()["evidence"]]

    assert creation_descriptions == read_descriptions
    assert r2.json()["detected_language"] == "cr"


def test_english_message_still_produces_english_explanation_after_i18n_refactor(client, auth_headers, db_session):
    """The multilingual restructure of routers/checks.py's explanation
    building must not change any existing English behavior."""
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "URGENT: Your MCB Ltd account will be suspended. Send your OTP now.", "claimed_sender": "MCB Ltd"},
        headers=headers,
    )
    body = r.json()
    assert body["detected_language"] == "en"
    assert "sender you named" in body["ai_explanation"].lower()
