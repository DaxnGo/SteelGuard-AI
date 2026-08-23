from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import predict_image
from app.utils.image_validation import ImageValidationError

router = APIRouter()


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


@router.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile | None = File(None)):
    if file is None or not file.filename:
        return error_response(400, "NO_FILE", "No file was uploaded.")

    content = await file.read()
    if not content:
        return error_response(400, "NO_FILE", "No file was uploaded.")

    try:
        return predict_image(file, content)
    except ImageValidationError as exc:
        status_code = 415 if exc.code == "UNSUPPORTED_FILE_TYPE" else 422
        return error_response(status_code, exc.code, exc.message)
