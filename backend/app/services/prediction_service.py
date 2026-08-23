from fastapi import UploadFile

from app.schemas.prediction import PredictionDetail, PredictionResponse
from app.services.ai_service import run_inference
from app.utils.image_validation import validate_image


def predict_image(file: UploadFile, content: bytes) -> PredictionResponse:
    validate_image(file, content)

    result = run_inference(content)

    prediction = PredictionDetail(
        class_name=result["class_name"],
        confidence=result["confidence"],
        recommendation=result["recommendation"],
        gradcam_image=result["gradcam_image"],
    )

    return PredictionResponse(prediction=prediction)
