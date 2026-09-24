"""
Speech-to-text: transcribes an uploaded audio clip (someone speaking a
suspicious message instead of typing it) into text, which then flows
through the exact same pipeline as pasted text, a fetched URL, or
OCR-extracted text.

Uses CMU Sphinx (via SpeechRecognition + pocketsphinx), a genuinely
local, fully offline speech recognition engine, no external API call,
consistent with this project's local-only architecture.

Important, stated honestly: Sphinx's accuracy is meaningfully lower
than a modern neural model such as Whisper, this was confirmed
directly during development: a synthesized test phrase "Your MCB
account will be suspended" was transcribed as "c. b. don't be
suspended", getting the brand name entirely wrong and mangling "will"
into "don't be". Sphinx uses an older, smaller acoustic and language
model and struggles particularly with proper nouns, brand names, and
anything outside its built-in dictionary, exactly the kind of terms
that matter most for this project's use case (bank names, institution
names). Testing with pure silence also found that Sphinx can
hallucinate a word (e.g. reporting "dog" for a silent audio clip)
rather than reliably reporting "no speech found" -- meaning a
transcription result should never be treated as strong evidence on its
own for this project's fraud-analysis purposes, only as an approximate
starting point a user can review, exactly the same caution already
applied to OCR results (see app/ocr.py). This module is honest about
that rather than presenting Sphinx's output with the same implied
confidence as typed text, see the caveat surfaced in
app/routers/checks.py's STT endpoint. Whisper
would be a meaningfully better choice if disk space allows in a real
deployment (see README's "Known limitations"); it was not available in
this development environment due to a disk space constraint.
"""
import io
from dataclasses import dataclass

import speech_recognition as sr

MAX_AUDIO_BYTES = 10_000_000
MAX_AUDIO_DURATION_SECONDS = 120


class InvalidAudioError(Exception):
    """Raised when the uploaded file isn't readable audio, or exceeds
    the size/duration limits."""


class TranscriptionError(Exception):
    """Raised when the audio is valid but no speech could be
    recognized in it at all, a normal, expected outcome for silent or
    unintelligible audio, not necessarily a bug."""


@dataclass
class SttResult:
    text: str
    engine: str = "sphinx"
    is_low_reliability_engine: bool = True


def transcribe_audio(audio_bytes: bytes) -> SttResult:
    """
    Expects a format SpeechRecognition's AudioFile can read directly
    (wav, aiff, flac) — see app/routers/checks.py's STT endpoint for
    how a browser-recorded webm/ogg clip would need transcoding to one
    of these first (not yet implemented, see README's "Known
    limitations").
    """
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise InvalidAudioError(f"Audio exceeds the maximum allowed size of {MAX_AUDIO_BYTES // 1_000_000} MB")

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            if source.DURATION and source.DURATION > MAX_AUDIO_DURATION_SECONDS:
                raise InvalidAudioError(
                    f"Audio exceeds the maximum allowed duration of {MAX_AUDIO_DURATION_SECONDS} seconds"
                )
            audio_data = recognizer.record(source)
    except InvalidAudioError:
        raise
    except Exception as e:
        raise InvalidAudioError(f"Could not read the uploaded audio: {e}")

    try:
        text = recognizer.recognize_sphinx(audio_data)
    except sr.UnknownValueError:
        raise TranscriptionError("No recognizable speech was found in this audio.")
    except sr.RequestError as e:
        raise InvalidAudioError(f"The local speech recognition engine failed: {e}")

    return SttResult(text=text)
