"""Client-side validation for one uploaded steel surface image."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Protocol
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})
EXPECTED_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
}
MEDIA_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}


class UploadedFileLike(Protocol):
    """Minimum uploaded-file interface required by the validator."""

    name: str

    def getvalue(self) -> bytes:
        """Return the complete uploaded file contents."""


class ImageValidationError(ValueError):
    """A safe validation failure that can be shown to the user."""


@dataclass(frozen=True)
class ValidatedImage:
    """Validated upload data used by the current frontend interaction."""

    filename: str
    data: bytes
    preview: Image.Image
    width: int
    height: int
    image_format: str
    media_type: str


def validate_uploaded_image(image_file: UploadedFileLike | None) -> ValidatedImage:
    """Validate one Streamlit upload and build an orientation-safe preview."""

    if image_file is None:
        raise ImageValidationError("Please select one JPG, JPEG, or PNG image.")

    filename = Path(getattr(image_file, "name", "")).name
    if not filename:
        raise ImageValidationError("The selected image must have a filename.")

    try:
        data = image_file.getvalue()
    except (AttributeError, OSError, ValueError) as exc:
        raise ImageValidationError("The selected image could not be read.") from exc

    return validate_image_bytes(filename, data)


def validate_image_bytes(filename: str, data: bytes) -> ValidatedImage:
    """Validate encoded bytes without changing the bytes sent for inference."""

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ImageValidationError("Unsupported format. Choose a JPG, JPEG, or PNG image.")

    if not data:
        raise ImageValidationError("The selected image is empty. Choose another image.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(BytesIO(data)) as image:
                detected_format = (image.format or "").upper()
                image.verify()

            if detected_format not in MEDIA_TYPES:
                raise ImageValidationError(
                    "Unsupported format. Choose a JPG, JPEG, or PNG image."
                )

            if detected_format != EXPECTED_FORMATS[extension]:
                raise ImageValidationError(
                    "The filename does not match the image format. Choose another image."
                )

            with Image.open(BytesIO(data)) as image:
                image.load()
                preview = ImageOps.exif_transpose(image).convert("RGB")
                preview.load()
                width, height = preview.size
    except ImageValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ) as exc:
        raise ImageValidationError(
            "This image could not be opened. Choose a valid JPG, JPEG, or PNG image."
        ) from exc

    if width < 1 or height < 1:
        raise ImageValidationError("The selected image has invalid dimensions.")

    return ValidatedImage(
        filename=Path(filename).name,
        data=data,
        preview=preview,
        width=width,
        height=height,
        image_format=detected_format,
        media_type=MEDIA_TYPES[detected_format],
    )
