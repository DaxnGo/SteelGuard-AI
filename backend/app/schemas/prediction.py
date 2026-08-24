import math
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class DefectClass(str, Enum):
    CRAZING = "Crazing"
    INCLUSION = "Inclusion"
    PATCHES = "Patches"
    PITTED_SURFACE = "Pitted Surface"
    ROLLED_IN_SCALE = "Rolled-in Scale"
    SCRATCHES = "Scratches"


class Recommendation(str, Enum):
    ACCEPT = "ACCEPT"
    REWORK = "REWORK"
    REJECT = "REJECT"


class PredictionDetail(BaseModel):
    class_name: DefectClass
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: Recommendation
    gradcam_image: str | None = None

    @field_validator("confidence", mode="before")
    @classmethod
    def validate_confidence(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("confidence must be a finite number.")
        if not math.isfinite(value):
            raise ValueError("confidence must be a finite number.")
        return value

    @field_validator("gradcam_image", mode="before")
    @classmethod
    def validate_gradcam_image(cls, value):
        if value is None:
            return value
        if not isinstance(value, str) or not value.strip():
            raise ValueError("gradcam_image must be null or a non-empty string.")
        return value


class PredictionResponse(BaseModel):
    success: bool = True
    prediction: PredictionDetail


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
