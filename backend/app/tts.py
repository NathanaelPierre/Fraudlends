"""
Text-to-speech: converts a check's verdict and explanation into a
spoken audio clip, for accessibility — someone with low literacy, a
visual impairment, or simply reacting under stress to a suspicious
call can hear "this looks like a scam, don't send money" instead of
needing to read and parse a text screen.

Uses espeak-ng, a genuinely local, fully offline TTS engine, no
external API call, consistent with this project's local-only
architecture, and consistent with app/stt.py's speech-to-text module
using local CMU Sphinx for the same reason.

Honest, upfront limitation: espeak-ng's voice is synthetic and
robotic-sounding compared to modern neural TTS (a cloud provider's
voice, or a local neural model like Piper), a real, audible quality
tradeoff for staying fully local and dependency-light. It is
intelligible, which is what matters for this use case (conveying a
safety-critical verdict), but it should not be presented as
production-polish audio quality.
"""
import subprocess
import tempfile
import os
from dataclasses import dataclass

MAX_TEXT_LENGTH = 2000


class TtsError(Exception):
    """Raised when speech synthesis fails, a missing espeak-ng binary,
    or the underlying subprocess call failing for any reason."""


@dataclass
class TtsResult:
    audio_bytes: bytes
    format: str = "wav"
    engine: str = "espeak-ng"


def synthesize_speech(text: str) -> TtsResult:
    """
    Returns a WAV audio clip of the given text spoken aloud. Raises
    TtsError if synthesis fails for any reason (missing binary,
    invalid input, subprocess failure) — callers should treat this the
    same way app/ocr.py and app/stt.py treat their own failure modes:
    a clear, honest error rather than a silent empty result.
    """
    if not text or not text.strip():
        raise TtsError("No text was provided to synthesize.")

    truncated = text[:MAX_TEXT_LENGTH]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["espeak-ng", truncated, "-w", tmp_path],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise TtsError(f"Speech synthesis failed: {result.stderr.decode(errors='replace')}")

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        if not audio_bytes:
            raise TtsError("Speech synthesis produced no audio output.")

        return TtsResult(audio_bytes=audio_bytes)

    except FileNotFoundError:
        raise TtsError("The local text-to-speech engine (espeak-ng) is not installed on this server.")
    except subprocess.TimeoutExpired:
        raise TtsError("Speech synthesis timed out.")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def build_spoken_summary(overall_verdict: str, ai_explanation: str) -> str:
    """
    Builds the actual text that gets spoken for a check result, not
    just the raw explanation, but a verdict-first phrasing appropriate
    for listening rather than reading. A person hearing this should
    get the single most important fact (is this safe or not) before
    the supporting detail, which is the opposite of how the visual
    CheckOut response is ordered (verdict is a field among many).
    """
    verdict_phrases = {
        "safe": "This message appears safe.",
        "suspicious": "Warning. This message is suspicious.",
        "high_risk": "Warning. This message is high risk. Do not send money or share personal information.",
    }
    intro = verdict_phrases.get(overall_verdict, "")
    if intro:
        return f"{intro} {ai_explanation}"
    return ai_explanation
