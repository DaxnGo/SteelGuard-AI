"""Tests for local image validation and preview preparation."""

from __future__ import annotations

from io import BytesIO
import unittest

from PIL import Image

from utils.image_validator import (
    ImageValidationError,
    validate_image_bytes,
    validate_uploaded_image,
)


def make_image_bytes(image_format: str, size: tuple[int, int] = (48, 32)) -> bytes:
    """Build a small in-memory image fixture."""

    image_bytes = BytesIO()
    Image.new("RGB", size, color=(112, 122, 132)).save(
        image_bytes,
        format=image_format,
    )
    return image_bytes.getvalue()


class FakeUpload:
    """Minimal upload object accepted by the validator."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


class ImageValidatorTests(unittest.TestCase):
    def test_accepts_supported_extensions_and_preserves_bytes(self) -> None:
        cases = (
            ("surface.jpg", "JPEG", "image/jpeg"),
            ("surface.JPEG", "JPEG", "image/jpeg"),
            ("surface.png", "PNG", "image/png"),
        )

        for filename, image_format, media_type in cases:
            with self.subTest(filename=filename):
                data = make_image_bytes(image_format)
                result = validate_uploaded_image(FakeUpload(filename, data))

                self.assertEqual(result.filename, filename)
                self.assertEqual(result.data, data)
                self.assertEqual((result.width, result.height), (48, 32))
                self.assertEqual(result.image_format, image_format)
                self.assertEqual(result.media_type, media_type)
                self.assertEqual(result.preview.mode, "RGB")
                result.preview.close()

    def test_rejects_missing_or_empty_upload(self) -> None:
        with self.assertRaises(ImageValidationError):
            validate_uploaded_image(None)
        with self.assertRaises(ImageValidationError):
            validate_image_bytes("surface.png", b"")

    def test_rejects_unsupported_extension(self) -> None:
        with self.assertRaisesRegex(ImageValidationError, "Unsupported format"):
            validate_image_bytes("surface.gif", make_image_bytes("PNG"))

    def test_rejects_corrupt_image(self) -> None:
        with self.assertRaisesRegex(ImageValidationError, "could not be opened"):
            validate_image_bytes("surface.png", b"not-an-image")

    def test_rejects_extension_and_content_mismatch(self) -> None:
        with self.assertRaisesRegex(ImageValidationError, "does not match"):
            validate_image_bytes("surface.jpg", make_image_bytes("PNG"))


if __name__ == "__main__":
    unittest.main()
