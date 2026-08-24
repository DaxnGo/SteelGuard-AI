from io import BytesIO

from fastapi import UploadFile
from PIL import Image
from pydantic import ValidationError

from app.schemas.prediction import PredictionDetail, PredictionResponse
from app.services.ai_service import run_inference
from app.utils.image_validation import validate_image


class InferenceError(Exception):
    def __init__(self, message: str = "The image could not be analyzed at this time."):
        self.message = message
        super().__init__(message)


def predict_image(file: UploadFile, content: bytes) -> PredictionResponse:
    validate_image(file, content)

    with Image.open(BytesIO(content)) as decoded_image:
        rgb_image = decoded_image.convert("RGB")

    result = run_inference(rgb_image)

    try:
        prediction = PredictionDetail(**result)
    except ValidationError as exc:
        raise InferenceError("The AI adapter returned an invalid prediction.") from exc

    return PredictionResponse(prediction=prediction)
