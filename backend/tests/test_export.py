"""
GET /checks/export: exports the current user's own check history as
CSV. Registered before /{check_id} for the same routing reason as
/summary.
"""
import csv
import io


def test_export_route_matched_before_check_id_route(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/export", headers=headers)
    assert r.status_code == 200


def test_export_returns_csv_content_type(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/export", headers=headers)
    assert "text/csv" in r.headers["content-type"]


def test_export_has_attachment_disposition(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/export", headers=headers)
    assert "attachment" in r.headers["content-disposition"]
    assert "fraudlens_checks_export.csv" in r.headers["content-disposition"]


def test_export_with_no_checks_has_only_header_row(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/export", headers=headers)
    reader = csv.reader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0][0] == "id"


def test_export_includes_submitted_checks(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "First check", "claimed_sender": "Sender A"}, headers=headers)
    client.post("/checks/", json={"message_text": "Second check"}, headers=headers)

    r = client.get("/checks/export", headers=headers)
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 2
    message_texts = {row["message_text"] for row in rows}
    assert "First check" in message_texts
    assert "Second check" in message_texts


def test_export_includes_verdict_and_flags(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Send your OTP now", "claimed_sender": "Scam Co"}, headers=headers)

    r = client.get("/checks/export", headers=headers)
    reader = csv.DictReader(io.StringIO(r.text))
    row = list(reader)[0]
    assert row["overall_verdict"] == "high_risk"
    assert "requests_otp" in row["ai_flags"]


def test_export_includes_feedback_if_given(client, auth_headers):
    headers = auth_headers()
    r1 = client.post("/checks/", json={"message_text": "Test"}, headers=headers)
    client.post(f"/checks/{r1.json()['id']}/feedback", json={"is_correct": True}, headers=headers)

    r = client.get("/checks/export", headers=headers)
    reader = csv.DictReader(io.StringIO(r.text))
    row = list(reader)[0]
    assert row["user_feedback"] == "correct"


def test_export_excludes_unsaved_checks(client, auth_headers):
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Not saved", "save_check": False}, headers=headers)
    client.post("/checks/", json={"message_text": "Saved"}, headers=headers)

    r = client.get("/checks/export", headers=headers)
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["message_text"] == "Saved"


def test_export_requires_auth(client):
    r = client.get("/checks/export")
    assert r.status_code == 401


def test_export_is_scoped_to_own_checks_only(client, auth_headers):
    headers_a = auth_headers(email="exporta@fraudlens.mu")
    headers_b = auth_headers(email="exportb@fraudlens.mu")

    client.post("/checks/", json={"message_text": "A's check"}, headers=headers_a)
    client.post("/checks/", json={"message_text": "B's check"}, headers=headers_b)

    r = client.get("/checks/export", headers=headers_a)
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["message_text"] == "A's check"


def test_export_content_is_already_pii_scrubbed(client, auth_headers):
    """
    The export doesn't re-scrub, it exports exactly what's already
    stored, which is already scrubbed at write time (see
    test_checks.py's PII scrubbing tests). This confirms that
    guarantee carries through to the export, not just the API
    responses.
    """
    headers = auth_headers()
    client.post("/checks/", json={"message_text": "Your OTP is 483921, verify now"}, headers=headers)

    r = client.get("/checks/export", headers=headers)
    assert "483921" not in r.text
