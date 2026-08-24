from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.schemas.prediction import ErrorResponse, PredictionResponse
from app.services.prediction_service import InferenceError, predict_image
from app.utils.image_validation import ImageValidationError, load_max_upload_bytes

router = APIRouter()

ERROR_RESPONSES = {
    status_code: {"model": ErrorResponse}
    for status_code in (400, 413, 415, 422, 500, 503)
}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


@router.post(
    "/predict",
    response_model=PredictionResponse,
    responses=ERROR_RESPONSES,
)
async def predict(
    request: Request,
    file: UploadFile | None = File(default=None),
):
    try:
        form = await request.form()
    except Exception:
        return error_response(400, "NO_FILE", "No file was uploaded.")

    parts = list(form.multi_items())
    uploaded_parts = [
        (field_name, value)
        for field_name, value in parts
        if isinstance(value, StarletteUploadFile)
    ]
    named_files = [
        value for field_name, value in uploaded_parts if field_name == "file"
    ]
    if not named_files:
        return error_response(400, "NO_FILE", "No file was uploaded.")
    if len(parts) != 1 or len(uploaded_parts) != 1 or len(named_files) != 1:
        return error_response(
            400,
            "MULTIPLE_FILES_NOT_ALLOWED",
            "Only one image may be analyzed per request.",
        )

    file = named_files[0]
    if not file.filename:
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
        return error_response(
            422,
            "INVALID_IMAGE",
            "The uploaded file is empty or could not be decoded as a valid image.",
        )
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
    except InferenceError:
        return error_response(
            503,
            "INFERENCE_FAILED",
            "The image could not be analyzed at this time. Please try again.",
        )
