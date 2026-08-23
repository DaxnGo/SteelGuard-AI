from enum import Enum

from pydantic import BaseModel, Field


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


class PredictionResponse(BaseModel):
    success: bool = True
    prediction: PredictionDetail


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
