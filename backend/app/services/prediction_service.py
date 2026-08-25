from io import BytesIO

from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError

from app.schemas.prediction import PredictionDetail, PredictionResponse
from app.services.ai_service import run_inference
from app.utils.image_validation import ImageValidationError, validate_image


class InferenceError(Exception):
    def __init__(self, message: str = "The image could not be analyzed at this time."):
        self.message = message
        super().__init__(message)


def predict_image(file: UploadFile, content: bytes) -> PredictionResponse:
    validate_image(file, content)

    try:
        with Image.open(BytesIO(content)) as decoded_image:
            rgb_image = decoded_image.convert("RGB")
    except (OSError, ValueError) as exc:
        raise ImageValidationError(
            "INVALID_IMAGE",
            "The uploaded file could not be processed as an image.",
        ) from exc

    try:
        result = run_inference(rgb_image)
    except Exception as exc:
        raise InferenceError("AI inference failed.") from exc

    try:
        prediction = PredictionDetail.model_validate(result)
    except (TypeError, ValidationError) as exc:
        raise InferenceError("The AI adapter returned an invalid prediction.") from exc

    return PredictionResponse(prediction=prediction)
