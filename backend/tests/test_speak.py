"""
GET /checks/{id}/speak: returns a spoken-audio (WAV) version of a
check's verdict and explanation, using the local espeak-ng TTS engine.
"""
import shutil
import pytest

ESPEAK_AVAILABLE = shutil.which("espeak-ng") is not None


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_speak_returns_real_wav_audio(client, auth_headers):
    headers = auth_headers()
    r1 = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r1.json()["id"]

    r2 = client.get(f"/checks/{check_id}/speak", headers=headers)
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "audio/wav"
    assert r2.content[:4] == b"RIFF"
    assert r2.content[8:12] == b"WAVE"
    assert len(r2.content) > 0


def test_speak_requires_auth(client, auth_headers):
    headers = auth_headers()
    r1 = client.post("/checks/", json={"message_text": "Test message"}, headers=headers)
    check_id = r1.json()["id"]

    r2 = client.get(f"/checks/{check_id}/speak")
    assert r2.status_code == 401


def test_speak_on_nonexistent_check_returns_404(client, auth_headers):
    headers = auth_headers()
    r = client.get("/checks/999999/speak", headers=headers)
    assert r.status_code == 404


def test_speak_on_another_users_check_returns_404(client, auth_headers):
    headers_a = auth_headers(email="speaka@fraudlens.mu")
    headers_b = auth_headers(email="speakb@fraudlens.mu")

    r1 = client.post("/checks/", json={"message_text": "A's message"}, headers=headers_a)
    check_id = r1.json()["id"]

    r2 = client.get(f"/checks/{check_id}/speak", headers=headers_b)
    assert r2.status_code == 404


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_speak_on_high_risk_check_produces_audio(client, auth_headers, db_session):
    from app import models
    from app.entity_matcher import normalize_name

    db_session.add(models.RegistryEntity(
        name="MCB Ltd", normalized_name=normalize_name("MCB Ltd"), source="BOM", status="Active"
    ))
    db_session.commit()

    headers = auth_headers()
    r_safe = client.post("/checks/", json={"message_text": "Statement ready", "claimed_sender": "MCB"}, headers=headers)
    r_risky = client.post("/checks/", json={"message_text": "Send your OTP now", "claimed_sender": "Scam Co"}, headers=headers)

    audio_safe = client.get(f"/checks/{r_safe.json()['id']}/speak", headers=headers).content
    audio_risky = client.get(f"/checks/{r_risky.json()['id']}/speak", headers=headers).content

    assert len(audio_safe) > 0
    assert len(audio_risky) > 0
