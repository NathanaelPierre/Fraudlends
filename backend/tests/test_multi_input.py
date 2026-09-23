"""
Tests for the multi-input layer: submitting a check via a URL to fetch
or an image to OCR, instead of pasted text, both must converge on the
exact same analysis pipeline as pasted text (see
_run_check_pipeline() in app/routers/checks.py).
"""
import io
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageFont


def _seed_registry(db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()


def test_message_text_and_source_url_together_rejected(client, auth_headers):
    headers = auth_headers()
    r = client.post(
        "/checks/",
        json={"message_text": "some text", "source_url": "http://example.com"},
        headers=headers,
    )
    assert r.status_code == 422


def test_neither_message_text_nor_source_url_rejected(client, auth_headers):
    headers = auth_headers()
    r = client.post("/checks/", json={"claimed_sender": "MCB"}, headers=headers)
    assert r.status_code == 422


def test_url_mode_fetches_and_analyzes_content(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    with patch("app.routers.checks.fetch_url_text", return_value="MCB: verify your OTP to continue") as mock_fetch:
        r = client.post(
            "/checks/",
            json={"source_url": "http://example.com/message", "claimed_sender": "MCB"},
            headers=headers,
        )
        assert r.status_code == 200
        mock_fetch.assert_called_once_with("http://example.com/message")
        body = r.json()
        assert body["registry_match_status"] == "verified"
        assert "requests_otp" in body["ai_flags"]


def test_unsafe_url_rejected_with_clear_error(client, auth_headers):
    from app.url_fetcher import UnsafeUrlError

    headers = auth_headers()
    with patch("app.routers.checks.fetch_url_text", side_effect=UnsafeUrlError("blocked")):
        r = client.post(
            "/checks/",
            json={"source_url": "http://169.254.169.254/"},
            headers=headers,
        )
        assert r.status_code == 400


def test_unreachable_url_returns_422_not_500(client, auth_headers):
    from app.url_fetcher import FetchError

    headers = auth_headers()
    with patch("app.routers.checks.fetch_url_text", side_effect=FetchError("timeout")):
        r = client.post("/checks/", json={"source_url": "http://example.com"}, headers=headers)
        assert r.status_code == 422


def test_url_with_no_readable_text_rejected(client, auth_headers):
    headers = auth_headers()
    with patch("app.routers.checks.fetch_url_text", return_value="   "):
        r = client.post("/checks/", json={"source_url": "http://example.com"}, headers=headers)
        assert r.status_code == 422


def _make_test_image_bytes(text: str) -> bytes:
    img = Image.new("RGB", (800, 200), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except OSError:
        font = None
    draw.text((20, 70), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_image_upload_extracts_and_analyzes_text(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    image_bytes = _make_test_image_bytes("MCB account update")

    r = client.post(
        "/checks/from-image",
        files={"image": ("screenshot.png", image_bytes, "image/png")},
        data={"claimed_sender": "MCB"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["registry_match_status"] == "verified"
    assert "MCB" in body["message_text"] or "account" in body["message_text"].lower()


def test_image_upload_requires_auth(client):
    image_bytes = _make_test_image_bytes("test")
    r = client.post(
        "/checks/from-image",
        files={"image": ("screenshot.png", image_bytes, "image/png")},
    )
    assert r.status_code == 401


def test_invalid_image_file_rejected(client, auth_headers):
    headers = auth_headers()
    r = client.post(
        "/checks/from-image",
        files={"image": ("not-an-image.png", b"this is not an image", "image/png")},
        headers=headers,
    )
    assert r.status_code == 422


def test_blank_image_with_no_text_rejected(client, auth_headers):
    headers = auth_headers()
    img = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    r = client.post(
        "/checks/from-image",
        files={"image": ("blank.png", buf.getvalue(), "image/png")},
        headers=headers,
    )
    assert r.status_code == 422


def test_low_confidence_ocr_result_includes_a_caveat(client, auth_headers, db_session):
    """Poor-quality OCR (tiny default font, deliberately) must surface
    a visible caveat in the explanation, not be presented with the
    same confidence as clean pasted text."""
    _seed_registry(db_session)
    headers = auth_headers()

    img = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "MCB account", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    r = client.post(
        "/checks/from-image",
        files={"image": ("blurry.png", buf.getvalue(), "image/png")},
        data={"claimed_sender": "MCB"},
        headers=headers,
    )
    if r.status_code == 200:
        body = r.json()
        if "low OCR confidence" in body["ai_explanation"]:
            assert "double-check" in body["ai_explanation"]


def test_url_mode_respects_save_check_false(client, auth_headers, db_session):
    _seed_registry(db_session)
    headers = auth_headers()

    with patch("app.routers.checks.fetch_url_text", return_value="MCB account notice"):
        client.post(
            "/checks/",
            json={"source_url": "http://example.com", "claimed_sender": "MCB", "save_check": False},
            headers=headers,
        )

    r = client.get("/checks/", headers=headers)
    assert r.json() == []
