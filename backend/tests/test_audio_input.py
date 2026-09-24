"""
Tests for POST /checks/from-audio: the fourth input mode, transcribing
spoken audio locally (CMU Sphinx) before running the exact same
analysis pipeline as pasted text.
"""
import subprocess
import shutil
import tempfile
import os
import pytest

ESPEAK_AVAILABLE = shutil.which("espeak-ng") is not None


def _synthesize_speech_bytes(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(["espeak-ng", text, "-w", tmp_path], capture_output=True, check=True)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_audio_upload_transcribes_and_analyzes(client, auth_headers):
    headers = auth_headers()
    audio_bytes = _synthesize_speech_bytes("hello this is a test message")

    r = client.post(
        "/checks/from-audio",
        files={"audio": ("test.wav", audio_bytes, "audio/wav")},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["message_text"]) > 0


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_audio_upload_includes_low_reliability_caveat(client, auth_headers):
    headers = auth_headers()
    audio_bytes = _synthesize_speech_bytes("test message for caveat check")

    r = client.post(
        "/checks/from-audio",
        files={"audio": ("test.wav", audio_bytes, "audio/wav")},
        headers=headers,
    )
    body = r.json()
    assert "speech recognition engine" in body["ai_explanation"]
    assert "verify" in body["ai_explanation"].lower()


def test_audio_upload_requires_auth(client):
    r = client.post(
        "/checks/from-audio",
        files={"audio": ("test.wav", b"fake audio bytes", "audio/wav")},
    )
    assert r.status_code == 401


def test_invalid_audio_file_rejected(client, auth_headers):
    headers = auth_headers()
    r = client.post(
        "/checks/from-audio",
        files={"audio": ("not-audio.wav", b"this is not audio data at all", "audio/wav")},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_audio_upload_respects_save_check_false(client, auth_headers):
    headers = auth_headers()
    audio_bytes = _synthesize_speech_bytes("do not save this one")

    client.post(
        "/checks/from-audio",
        files={"audio": ("test.wav", audio_bytes, "audio/wav")},
        data={"save_check": "false"},
        headers=headers,
    )

    r = client.get("/checks/", headers=headers)
    assert r.json() == []


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_audio_upload_passes_claimed_sender_through(client, auth_headers, db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()

    headers = auth_headers()
    audio_bytes = _synthesize_speech_bytes("your account statement is ready")

    r = client.post(
        "/checks/from-audio",
        files={"audio": ("test.wav", audio_bytes, "audio/wav")},
        data={"claimed_sender": "MCB"},
        headers=headers,
    )
    assert r.json()["registry_match_status"] == "verified"
