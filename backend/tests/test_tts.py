"""
Text-to-speech tests. Uses the real espeak-ng binary (skipped
automatically if not installed) rather than mocking synthesis, since
the whole point is confirming real, valid audio is actually produced.
"""
import shutil
import pytest
from app.tts import synthesize_speech, build_spoken_summary, TtsError

ESPEAK_AVAILABLE = shutil.which("espeak-ng") is not None


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_synthesizes_real_audio():
    result = synthesize_speech("hello world")
    assert len(result.audio_bytes) > 0
    assert result.format == "wav"


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_output_is_a_valid_wav_file():
    result = synthesize_speech("this is a test")
    assert result.audio_bytes[:4] == b"RIFF"
    assert result.audio_bytes[8:12] == b"WAVE"


def test_empty_text_rejected():
    with pytest.raises(TtsError):
        synthesize_speech("")


def test_whitespace_only_text_rejected():
    with pytest.raises(TtsError):
        synthesize_speech("   ")


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_long_text_is_truncated_not_rejected():
    long_text = "word " * 1000
    result = synthesize_speech(long_text)
    assert len(result.audio_bytes) > 0


def test_build_spoken_summary_leads_with_high_risk_warning():
    text = build_spoken_summary("high_risk", "Some explanation here.")
    assert text.startswith("Warning. This message is high risk.")
    assert "Some explanation here." in text


def test_build_spoken_summary_leads_with_suspicious_warning():
    text = build_spoken_summary("suspicious", "Some explanation here.")
    assert text.startswith("Warning. This message is suspicious.")


def test_build_spoken_summary_leads_with_safe_confirmation():
    text = build_spoken_summary("safe", "Some explanation here.")
    assert text.startswith("This message appears safe.")


def test_build_spoken_summary_falls_back_to_explanation_for_unknown_verdict():
    """Defensive: an unrecognized verdict string should not crash or
    silently drop the explanation."""
    text = build_spoken_summary("unknown_verdict", "Some explanation here.")
    assert text == "Some explanation here."
