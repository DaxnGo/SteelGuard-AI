from io import BytesIO
import os

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES_ENV = "STEELGUARD_MAX_UPLOAD_BYTES"


class ImageValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def load_max_upload_bytes() -> int | None:
    """Return the shared D-04 byte limit when configured."""

    raw_value = os.getenv(MAX_UPLOAD_BYTES_ENV)
    if raw_value is None or not raw_value.strip():
        return None
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{MAX_UPLOAD_BYTES_ENV} must be a positive whole number of bytes."
        ) from exc
    if value <= 0:
        raise ValueError(
            f"{MAX_UPLOAD_BYTES_ENV} must be a positive whole number of bytes."
        )
    return value


def validate_image(file: UploadFile, content: bytes) -> None:
    filename = file.filename or ""
    extension = filename[filename.rfind("."):].lower() if "." in filename else ""

    if file.content_type not in ALLOWED_CONTENT_TYPES or extension not in ALLOWED_EXTENSIONS:
        raise ImageValidationError(
            "UNSUPPORTED_FILE_TYPE",
            "Only JPEG and PNG images are supported.",
        )

    expected_format = "JPEG" if extension in {".jpg", ".jpeg"} else "PNG"
    try:
        with Image.open(BytesIO(content)) as image:
            detected_format = (image.format or "").upper()
            image.verify()
    except UnidentifiedImageError:
        raise ImageValidationError(
            "INVALID_IMAGE",
            "The uploaded file could not be processed as an image.",
        )
    except Exception:
        raise ImageValidationError(
            "INVALID_IMAGE",
            "The uploaded file could not be processed as an image.",
        )

    if detected_format != expected_format:
        raise ImageValidationError(
            "UNSUPPORTED_FILE_TYPE",
            "The filename and image format do not match.",
        )
