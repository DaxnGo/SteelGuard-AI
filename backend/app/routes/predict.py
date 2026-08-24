from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.prediction import PredictionResponse
from app.services.prediction_service import predict_image
from app.utils.image_validation import ImageValidationError, load_max_upload_bytes

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

    try:
        max_upload_bytes = load_max_upload_bytes()
    except ValueError:
        return error_response(
            500,
            "INTERNAL_ERROR",
            "The upload limit is not configured correctly.",
        )

    content = await file.read(
        max_upload_bytes + 1 if max_upload_bytes is not None else -1
    )
    if not content:
        return error_response(400, "NO_FILE", "No file was uploaded.")
    if max_upload_bytes is not None and len(content) > max_upload_bytes:
        return error_response(
            413,
            "FILE_TOO_LARGE",
            "The uploaded image exceeds the configured size limit.",
        )

    try:
        return predict_image(file, content)
    except ImageValidationError as exc:
        status_code = 415 if exc.code == "UNSUPPORTED_FILE_TYPE" else 422
        return error_response(status_code, exc.code, exc.message)
