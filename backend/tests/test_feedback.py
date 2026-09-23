"""
Feedback loop: a user can mark whether a past verdict was correct, a
real, verifiable way to describe improvement over time, rather than an
unverifiable claim about the system getting smarter with more data.
"""


def test_submit_positive_feedback(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r.json()["id"]

    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": True}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["user_feedback"] == "correct"


def test_submit_negative_feedback(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r.json()["id"]

    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": False}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["user_feedback"] == "incorrect"


def test_new_check_has_no_feedback_by_default(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    assert r.json()["user_feedback"] is None


def test_feedback_persists_and_is_visible_on_later_fetch(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r.json()["id"]
    client.post(f"/checks/{check_id}/feedback", json={"is_correct": True}, headers=headers)

    r2 = client.get(f"/checks/{check_id}", headers=headers)
    assert r2.json()["user_feedback"] == "correct"


def test_feedback_can_be_changed(client, auth_headers):
    """A user should be able to correct their own feedback, the
    endpoint always overwrites, it doesn't error on a second call."""
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r.json()["id"]

    client.post(f"/checks/{check_id}/feedback", json={"is_correct": True}, headers=headers)
    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": False}, headers=headers)
    assert r2.json()["user_feedback"] == "incorrect"


def test_feedback_requires_auth(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r.json()["id"]

    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": True})
    assert r2.status_code == 401


def test_feedback_on_nonexistent_check_returns_404(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/999999/feedback", json={"is_correct": True}, headers=headers)
    assert r.status_code == 404


def test_cannot_give_feedback_on_another_users_check(client, auth_headers):
    headers_a = auth_headers(email="feedbacka@fraudlens.mu")
    headers_b = auth_headers(email="feedbackb@fraudlens.mu")

    r = client.post("/checks/", json={"message_text": "A's message"}, headers=headers_a)
    check_id = r.json()["id"]

    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": True}, headers=headers_b)
    assert r2.status_code == 404


def test_feedback_on_unsaved_check_fails_gracefully(client, auth_headers):
    """
    A check submitted with save_check=false has id=0 and was never
    persisted, attempting feedback on it must return a clean 404 (no
    such check exists to give feedback on), not a 500 error from
    trying to look up a nonsensical id.
    """
    headers = auth_headers()
    r = client.post("/checks/", json={"message_text": "Not saved", "save_check": False}, headers=headers)
    check_id = r.json()["id"]
    assert check_id == 0

    r2 = client.post(f"/checks/{check_id}/feedback", json={"is_correct": True}, headers=headers)
    assert r2.status_code == 404
