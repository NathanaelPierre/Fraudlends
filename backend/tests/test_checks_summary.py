"""
GET /checks/summary: a dashboard-style rollup of a user's own check
history. Registered before /{check_id} so the literal path is matched
first rather than FastAPI trying to parse "summary" as an integer id.
"""


def test_summary_route_is_matched_before_check_id_route(client, auth_headers):
    """
    The core routing concern: /checks/summary must not be swallowed by
    /checks/{check_id}'s integer parsing, which would otherwise return
    422 instead of the actual summary.
    """
    headers = auth_headers()
    r = client.get("/checks/summary", headers=headers)
    assert r.status_code == 200


def test_summary_with_no_checks_returns_zeros(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/summary", headers=headers)
    body = r.json()
    assert body["total_checks"] == 0
    assert body["safe_count"] == 0
    assert body["suspicious_count"] == 0
    assert body["high_risk_count"] == 0
    assert body["most_checked_senders"] == []


def test_summary_counts_verdicts_correctly(client, auth_headers, db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()

    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Safe", "claimed_sender": "MCB"}, headers=headers)
    client.post("/checks/", json={"message_text": "Unknown sender msg", "claimed_sender": "Nobody Corp"}, headers=headers)
    client.post("/checks/", json={"message_text": "Send OTP", "claimed_sender": "Scam Co"}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    body = r.json()
    assert body["total_checks"] == 3
    assert body["safe_count"] == 1
    assert body["suspicious_count"] == 1
    assert body["high_risk_count"] == 1


def test_summary_counts_feedback(client, auth_headers):
    headers = auth_headers()
    r1 = client.post("/checks/", json={"message_text": "First"}, headers=headers)
    r2 = client.post("/checks/", json={"message_text": "Second"}, headers=headers)
    client.post("/checks/", json={"message_text": "Third, no feedback"}, headers=headers)

    client.post(f"/checks/{r1.json()['id']}/feedback", json={"is_correct": True}, headers=headers)
    client.post(f"/checks/{r2.json()['id']}/feedback", json={"is_correct": False}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    body = r.json()
    assert body["checks_with_feedback"] == 2
    assert body["feedback_marked_correct"] == 1
    assert body["feedback_marked_incorrect"] == 1


def test_summary_ranks_most_checked_senders(client, auth_headers):
    headers = auth_headers()
    for _ in range(3):
        client.post("/checks/", json={"message_text": "msg", "claimed_sender": "Frequent Sender"}, headers=headers)
    client.post("/checks/", json={"message_text": "msg", "claimed_sender": "Rare Sender"}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    body = r.json()
    assert body["most_checked_senders"][0]["sender"] == "Frequent Sender"
    assert body["most_checked_senders"][0]["count"] == 3


def test_summary_caps_most_checked_senders_at_five(client, auth_headers):
    headers = auth_headers()
    for i in range(7):
        client.post("/checks/", json={"message_text": "msg", "claimed_sender": f"Sender {i}"}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    assert len(r.json()["most_checked_senders"]) == 5


def test_summary_excludes_checks_with_no_claimed_sender_from_ranking(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "No sender given"}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    assert r.json()["most_checked_senders"] == []


def test_summary_requires_auth(client):
    r = client.get("/checks/summary")
    assert r.status_code == 401


def test_summary_is_scoped_to_own_checks_only(client, auth_headers):
    headers_a = auth_headers(email="summarya@fraudlens.mu")
    headers_b = auth_headers(email="summaryb@fraudlens.mu")

    client.post("/checks/", json={"message_text": "A's check"}, headers=headers_a)
    client.post("/checks/", json={"message_text": "B's check 1"}, headers=headers_b)
    client.post("/checks/", json={"message_text": "B's check 2"}, headers=headers_b)

    r = client.get("/checks/summary", headers=headers_a)
    assert r.json()["total_checks"] == 1


def test_summary_excludes_unsaved_checks(client, auth_headers):
    """A check submitted with save_check=false was never persisted and
    must not be counted in the summary."""
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Not saved", "save_check": False}, headers=headers)
    client.post("/checks/", json={"message_text": "Saved"}, headers=headers)

    r = client.get("/checks/summary", headers=headers)
    assert r.json()["total_checks"] == 1
