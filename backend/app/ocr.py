"""
OCR (optical character recognition): extracts text from an uploaded
image (a screenshot of an SMS, WhatsApp message, or email) so it can
flow through the exact same pipeline as pasted text, registry check,
indicator extraction, domain analysis, eventually the AI layer.

Uses Tesseract (via pytesseract), a local, offline OCR engine, no
external API call, consistent with this project's local-only
architecture. Deliberately conservative about what it accepts:
- File size and pixel-dimension caps, so a malicious or huge image
  can't exhaust memory or processing time.
- Only real image formats, verified by actually opening the file with
  Pillow (not just trusting a claimed Content-Type or file extension,
  either of which a malicious upload could lie about).
- A confidence-based warning when Tesseract's own per-word confidence
  scores are low, so a low-quality scan doesn't get silently treated
  as if it were as reliable as clean pasted text, the caller decides
  how to surface that, this module just reports it honestly.
"""
import io
from dataclasses import dataclass
from typing import Optional

from PIL import Image, UnidentifiedImageError
import pytesseract

MAX_IMAGE_BYTES = 8_000_000
MAX_DIMENSION_PIXELS = 6000
LOW_CONFIDENCE_THRESHOLD = 40


class InvalidImageError(Exception):
    """Raised when the uploaded file isn't a real, readable image, or
    exceeds the size/dimension limits, never raised for a genuinely
    valid image that just happens to contain little or no text, which
    is a normal, expected OCR outcome, not an error."""


@dataclass
class OcrResult:
    text: str
    average_confidence: Optional[float]
    is_low_confidence: bool


def extract_text_from_image(image_bytes: bytes) -> OcrResult:
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise InvalidImageError(f"Image exceeds the maximum allowed size of {MAX_IMAGE_BYTES // 1_000_000} MB")

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except UnidentifiedImageError:
        raise InvalidImageError("The uploaded file is not a readable image")
    except Exception as e:
        raise InvalidImageError(f"Could not read the uploaded image: {e}")

    if image.width > MAX_DIMENSION_PIXELS or image.height > MAX_DIMENSION_PIXELS:
        raise InvalidImageError(
            f"Image dimensions ({image.width}x{image.height}) exceed the maximum "
            f"allowed {MAX_DIMENSION_PIXELS}x{MAX_DIMENSION_PIXELS}"
        )

    if image.mode != "RGB":
        image = image.convert("RGB")

    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    confidences = []
    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        if not text:
            continue
        words.append(text)
        conf_value = float(conf)
        if conf_value >= 0:
            confidences.append(conf_value)

    extracted_text = " ".join(words)
    average_confidence = sum(confidences) / len(confidences) if confidences else None
    is_low_confidence = average_confidence is not None and average_confidence < LOW_CONFIDENCE_THRESHOLD

    return OcrResult(text=extracted_text, average_confidence=average_confidence, is_low_confidence=is_low_confidence)
