from pydantic import BaseModel, Field
from typing import List, Optional


class BoundingBox(BaseModel):
    """Bounding box coordinates in xyxy format (pixels)."""

    x_min: float = Field(..., description="Left edge x-coordinate")
    y_min: float = Field(..., description="Top edge y-coordinate")
    x_max: float = Field(..., description="Right edge x-coordinate")
    y_max: float = Field(..., description="Bottom edge y-coordinate")


class Detection(BaseModel):
    """Single object detection result."""

    class_id: int = Field(..., description="Class index (0-5)")
    class_name: str = Field(..., description="Defect type name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    bbox: BoundingBox = Field(..., description="Bounding box in pixel coordinates")


class PredictionResponse(BaseModel):
    """Full prediction response with metadata."""

    success: bool = True
    detections: List[Detection] = Field(default_factory=list)
    count: int = Field(0, description="Number of detections")
    inference_time_ms: float = Field(..., description="Inference time in milliseconds")
    image_width: int = Field(..., description="Input image width")
    image_height: int = Field(..., description="Input image height")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    model_loaded: bool = False
    model_classes: Optional[List[str]] = None
