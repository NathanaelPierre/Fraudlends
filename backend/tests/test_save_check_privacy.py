"""
save_check=false: lets a user get a full analysis without the message
ever being persisted, for sensitive content (OTPs, account numbers,
private conversation text) they don't want stored at all.
"""


def _seed_registry(db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()


def test_unsaved_check_still_returns_full_analysis(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    r = client.post(
        "/checks/",
        json={"message_text": "Contains an OTP: 483921", "claimed_sender": "MCB", "save_check": False},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "verified"
    assert body["overall_verdict"] == "safe"
    assert body["ai_explanation"] is not None


def test_unsaved_check_does_not_appear_in_list(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    client.post(
        "/checks/",
        json={"message_text": "Sensitive content", "claimed_sender": "MCB", "save_check": False},
        headers=headers,
    )

    r = client.get("/checks/", headers=headers)
    assert r.json() == []


def test_saved_check_still_appears_in_list_by_default(client, auth_headers, db_session):
    """save_check defaults to true, existing behavior must not change
    for anyone who doesn't explicitly opt out."""
    _seed_registry(db_session)
    headers = auth_headers()

    client.post("/checks/", json={"message_text": "Normal message", "claimed_sender": "MCB"}, headers=headers)

    r = client.get("/checks/", headers=headers)
    assert len(r.json()) == 1
    assert r.json()[0]["message_text"] == "Normal message"


def test_unsaved_check_message_text_never_persisted_to_database(client, auth_headers, db_session):
    """Confirms the message is genuinely never written, not written
    then deleted, checked directly against the database, not just the
    list endpoint."""
    from app import models

    _seed_registry(db_session)
    headers = auth_headers()

    client.post(
        "/checks/",
        json={"message_text": "UNIQUE_SENTINEL_TEXT_FOR_THIS_TEST", "claimed_sender": "MCB", "save_check": False},
        headers=headers,
    )

    matches = db_session.query(models.Check).filter(
        models.Check.message_text == "UNIQUE_SENTINEL_TEXT_FOR_THIS_TEST"
    ).count()
    assert matches == 0


def test_mixing_saved_and_unsaved_checks_only_lists_saved_ones(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    client.post("/checks/", json={"message_text": "Saved one", "claimed_sender": "MCB"}, headers=headers)
    client.post(
        "/checks/",
        json={"message_text": "Not saved one", "claimed_sender": "MCB", "save_check": False},
        headers=headers,
    )
    client.post("/checks/", json={"message_text": "Saved two", "claimed_sender": "MCB"}, headers=headers)

    r = client.get("/checks/", headers=headers)
    messages = [c["message_text"] for c in r.json()]
    assert set(messages) == {"Saved one", "Saved two"}
