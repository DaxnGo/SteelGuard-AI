import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.inference import ModelEngine
from app.schemas import HealthResponse, PredictionResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model at startup, cleanup at shutdown."""
    logger.info("Starting up — loading model...")
    engine = ModelEngine.get_instance()
    app.state.engine = engine
    logger.info("Model ready. API accepting requests.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="NEU-DET Defect Detection API",
    description="Steel surface defect detection using YOLOv8. "
    "Supports 6 defect classes: crazing, inclusion, patches, "
    "pitted_surface, rolled-in_scale, scratches.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_engine() -> ModelEngine:
    return app.state.engine


# ---------- Endpoints ---------- #


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health_check():
    """Check API and model status."""
    engine = _get_engine()
    return HealthResponse(
        status="healthy",
        model_loaded=engine.model is not None,
        model_classes=list(engine.class_names.values()),
    )


@app.post("/predict", response_model=PredictionResponse, tags=["inference"])
async def predict(file: UploadFile = File(..., description="Image file (JPEG/PNG/BMP)")):
    """Run defect detection on an uploaded image.

    Returns JSON with detected defects, bounding boxes, confidence scores,
    and inference timing.
    """
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        engine = _get_engine()
        result = engine.predict(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Inference failed")
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

    return PredictionResponse(
        success=True,
        detections=result["detections"],
        count=len(result["detections"]),
        inference_time_ms=result["inference_time_ms"],
        image_width=result["image_width"],
        image_height=result["image_height"],
    )


@app.post("/predict/annotated", tags=["inference"])
async def predict_annotated(
    file: UploadFile = File(..., description="Image file (JPEG/PNG/BMP)"),
):
    """Run defect detection and return the annotated image with bounding boxes drawn."""
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. "
            f"Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        engine = _get_engine()
        annotated_bytes = engine.predict_annotated(image_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Inference failed")
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

    return Response(content=annotated_bytes, media_type="image/jpeg")
