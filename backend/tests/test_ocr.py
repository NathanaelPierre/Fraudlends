"""
OCR module tests. Uses real generated test images (via Pillow) rather
than mocking Tesseract, since the whole point of this module is
actually invoking the real, local OCR engine, a mocked test would not
catch a genuine integration problem with Tesseract itself.
"""
import io
import pytest
from PIL import Image, ImageDraw
from app.ocr import extract_text_from_image, InvalidImageError, MAX_IMAGE_BYTES, MAX_DIMENSION_PIXELS


def _make_test_image(text: str, size=(800, 200), font_size=32) -> bytes:
    """
    Uses a larger, explicit font size rather than Pillow's tiny default
    bitmap font — found during testing that the default font produces
    genuinely poor OCR results ("Hello world" read as "Helloworla" at
    35% confidence), which is an accurate reflection of a real OCR
    limitation on very small/low-quality text, not a bug in the OCR
    module itself. A real phone screenshot has much larger, clearer
    text than Pillow's tiny default, so tests should reflect that
    realistic case rather than an artificially degraded one.
    """
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (ImportError, OSError):
        font = None  # fall back to default font if DejaVu isn't available in this environment
    draw.text((20, 70), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_extracts_text_from_a_real_image():
    image_bytes = _make_test_image("Hello world")
    result = extract_text_from_image(image_bytes)
    assert "Hello" in result.text
    assert "world" in result.text


def test_confidence_is_reported_for_clear_text():
    image_bytes = _make_test_image("Clear readable text here")
    result = extract_text_from_image(image_bytes)
    assert result.average_confidence is not None
    assert result.average_confidence > 0


def test_low_quality_text_is_flagged_as_low_confidence():
    """
    Deliberate test for the confidence-flagging property: genuinely
    poor-quality rendered text (Pillow's tiny default bitmap font,
    rather than the larger explicit font used elsewhere in this file)
    produces both garbled OCR output and a low confidence score, and
    is_low_confidence must correctly reflect that rather than silently
    treating a poor scan as equally reliable as clean text.
    """
    img = Image.new("RGB", (600, 150), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "Hello world", fill="black")  # tiny default font, deliberately
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = extract_text_from_image(buf.getvalue())
    assert result.is_low_confidence is True


def test_blank_image_produces_empty_text_not_an_error():
    """A blank image is a valid image with no text to find, this must
    not be treated as an error, just an empty or near-empty result."""
    img = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = extract_text_from_image(buf.getvalue())
    assert result.text == ""
    assert result.average_confidence is None
    assert result.is_low_confidence is False


def test_non_image_bytes_rejected():
    with pytest.raises(InvalidImageError):
        extract_text_from_image(b"this is not an image, just plain bytes")


def test_empty_bytes_rejected():
    with pytest.raises(InvalidImageError):
        extract_text_from_image(b"")


def test_oversized_file_rejected():
    with pytest.raises(InvalidImageError):
        extract_text_from_image(b"x" * (MAX_IMAGE_BYTES + 1))


def test_oversized_dimensions_rejected():
    img = Image.new("RGB", (MAX_DIMENSION_PIXELS + 100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(InvalidImageError):
        extract_text_from_image(buf.getvalue())


def test_non_rgb_image_mode_is_handled():
    """Some real screenshots come as palette-mode (P) or with an alpha
    channel (RGBA), must not error, must still extract text correctly
    after conversion to RGB."""
    img = Image.new("RGBA", (600, 150), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "RGBA test text", fill=(0, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = extract_text_from_image(buf.getvalue())
    assert "RGBA" in result.text or "test" in result.text


def test_jpeg_format_is_accepted():
    """Real screenshots are commonly JPEG, not just PNG, confirms the
    module isn't accidentally PNG-only."""
    image_bytes = _make_test_image("JPEG format test")
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    result = extract_text_from_image(buf.getvalue())
    assert len(result.text) > 0
