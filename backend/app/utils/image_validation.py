from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class ImageValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


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
