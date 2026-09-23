"""
Repeat-sender detection: surfaces a user's own history of checks
against the same claimed sender. Scoped strictly to one user's own
history, never a cross-user signal.
"""


def test_first_check_on_a_sender_has_no_summary(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "First message", "claimed_sender": "New Sender"}, headers=headers)
    assert r.json()["repeat_sender_summary"] is None


def test_second_check_on_same_sender_shows_history(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "First", "claimed_sender": "Repeat Corp"}, headers=headers)
    r = client.post("/checks/", json={"message_text": "Second", "claimed_sender": "Repeat Corp"}, headers=headers)

    summary = r.json()["repeat_sender_summary"]
    assert summary is not None
    assert "Repeat Corp" in summary
    assert "1 time" in summary


def test_summary_correctly_counts_flagged_vs_safe(client, auth_headers, db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()

    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Statement ready", "claimed_sender": "MCB"}, headers=headers)
    client.post("/checks/", json={"message_text": "Send your OTP now", "claimed_sender": "MCB"}, headers=headers)

    r = client.post("/checks/", json={"message_text": "Third check", "claimed_sender": "MCB"}, headers=headers)
    summary = r.json()["repeat_sender_summary"]
    assert "2 times" in summary
    assert "1 of those were flagged" in summary


def test_all_safe_history_phrased_correctly(client, auth_headers, db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()

    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Statement 1", "claimed_sender": "MCB"}, headers=headers)

    r = client.post("/checks/", json={"message_text": "Statement 2", "claimed_sender": "MCB"}, headers=headers)
    summary = r.json()["repeat_sender_summary"]
    assert "all came back safe" in summary


def test_all_flagged_history_phrased_correctly(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Send your OTP now", "claimed_sender": "Scam Co"}, headers=headers)

    r = client.post("/checks/", json={"message_text": "Send your OTP again", "claimed_sender": "Scam Co"}, headers=headers)
    summary = r.json()["repeat_sender_summary"]
    assert "all were flagged" in summary


def test_different_senders_are_tracked_separately(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "First", "claimed_sender": "Sender A"}, headers=headers)
    client.post("/checks/", json={"message_text": "First", "claimed_sender": "Sender B"}, headers=headers)

    r = client.post("/checks/", json={"message_text": "Second", "claimed_sender": "Sender A"}, headers=headers)
    summary = r.json()["repeat_sender_summary"]
    assert "Sender A" in summary
    assert "Sender B" not in summary


def test_no_claimed_sender_has_no_summary(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "First, no sender"}, headers=headers)
    r = client.post("/checks/", json={"message_text": "Second, no sender"}, headers=headers)
    assert r.json()["repeat_sender_summary"] is None


def test_history_is_scoped_to_one_user_only(client, auth_headers):
    """The core privacy property: user B's checks on the same sender
    name must never appear in user A's repeat-sender summary."""
    headers_a = auth_headers(email="repeata@fraudlens.mu")
    headers_b = auth_headers(email="repeatb@fraudlens.mu")

    client.post("/checks/", json={"message_text": "A's check", "claimed_sender": "Shared Name Corp"}, headers=headers_a)
    client.post("/checks/", json={"message_text": "B's check", "claimed_sender": "Shared Name Corp"}, headers=headers_b)

    r = client.post("/checks/", json={"message_text": "A's second check", "claimed_sender": "Shared Name Corp"}, headers=headers_a)
    summary = r.json()["repeat_sender_summary"]
    assert "1 time" in summary


def test_summary_updates_on_a_previously_created_check_when_fetched_later(client, auth_headers):
    """
    The summary is computed fresh on read, not frozen at creation time,
    fetching an earlier check after a later one was submitted must
    reflect the updated history.
    """
    headers = auth_headers()
    r1 = client.post("/checks/", json={"message_text": "First", "claimed_sender": "Growing History Co"}, headers=headers)
    first_check_id = r1.json()["id"]
    assert r1.json()["repeat_sender_summary"] is None

    client.post("/checks/", json={"message_text": "Second", "claimed_sender": "Growing History Co"}, headers=headers)

    r2 = client.get(f"/checks/{first_check_id}", headers=headers)
    assert r2.json()["repeat_sender_summary"] is not None


def test_unsaved_check_does_not_count_toward_future_history(client, auth_headers):
    """A check submitted with save_check=false is never persisted, so
    it must not appear in a later check's repeat-sender count."""
    headers = auth_headers()
    client.post(
        "/checks/",
        json={"message_text": "Not saved", "claimed_sender": "Ghost Sender", "save_check": False},
        headers=headers,
    )

    r = client.post("/checks/", json={"message_text": "Real check", "claimed_sender": "Ghost Sender"}, headers=headers)
    assert r.json()["repeat_sender_summary"] is None
