"""
Speech-to-text tests. Uses real synthesized speech (via espeak-ng,
generated at test time) rather than mocking the recognition engine,
the whole point of this module is invoking the real, local Sphinx
engine, and its accuracy limitations are exactly what these tests are
meant to surface honestly, not hide behind a mock.

Two real, honest findings from testing against actual audio, both
documented in stt.py's module docstring rather than "fixed" (there is
no fix, this is Sphinx's genuine behavior):
1. A synthesized phrase containing a brand name ("MCB") was
   transcribed incorrectly, getting the brand name entirely wrong.
2. Pure silence was transcribed as the hallucinated word "dog" rather
   than correctly reporting no speech found.
"""
import subprocess
import shutil
import pytest
from app.stt import transcribe_audio, InvalidAudioError, TranscriptionError, MAX_AUDIO_BYTES

ESPEAK_AVAILABLE = shutil.which("espeak-ng") is not None


def _synthesize_speech(text: str) -> bytes:
    """
    Uses espeak-ng's -w (write to file) flag rather than --stdout.
    Found during testing: --stdout produces a WAV file with an
    incorrect frame count in its header (over a billion frames for a
    93KB file), which SpeechRecognition's AudioFile reads literally,
    producing a wildly wrong reported duration (48,695 seconds for a
    2-second clip). This is a real quirk of espeak-ng's streaming
    output, not a bug in the STT module or SpeechRecognition — writing
    to a real file first (which espeak-ng finalizes with a correct
    header) avoids it entirely.
    """
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(["espeak-ng", text, "-w", tmp_path], capture_output=True, check=True)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_transcribes_real_synthesized_speech():
    audio_bytes = _synthesize_speech("hello world testing one two three")
    result = transcribe_audio(audio_bytes)
    assert isinstance(result.text, str)
    assert len(result.text) > 0


@pytest.mark.skipif(not ESPEAK_AVAILABLE, reason="espeak-ng not installed in this environment")
def test_result_is_flagged_as_low_reliability():
    """
    Sphinx's output must always be flagged as low-reliability, this
    is a permanent property of using this engine, not a per-result
    judgment, since Sphinx's accuracy issues (see module docstring) are
    consistent, not occasional.
    """
    audio_bytes = _synthesize_speech("test message")
    result = transcribe_audio(audio_bytes)
    assert result.is_low_reliability_engine is True
    assert result.engine == "sphinx"


def test_non_audio_bytes_rejected():
    with pytest.raises(InvalidAudioError):
        transcribe_audio(b"this is not audio, just plain bytes")


def test_empty_bytes_rejected():
    with pytest.raises(InvalidAudioError):
        transcribe_audio(b"")


def test_oversized_audio_rejected():
    with pytest.raises(InvalidAudioError):
        transcribe_audio(b"x" * (MAX_AUDIO_BYTES + 1))


def test_pure_silence_does_not_crash():
    """
    Documents the real, honest limitation found during development:
    Sphinx does not reliably raise "no speech found" for pure silence,
    it can hallucinate a word instead. This test confirms the function
    does not crash either way, it either returns some result or raises
    TranscriptionError, both are acceptable outcomes for silent audio,
    but a crash is not.
    """
    import wave
    import struct
    import io

    buf = io.BytesIO()
    with wave.open(buf, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        silence_frame = struct.pack("<h", 0)
        f.writeframes(silence_frame * 16000 * 2)

    try:
        result = transcribe_audio(buf.getvalue())
        assert isinstance(result.text, str)
    except TranscriptionError:
        pass
