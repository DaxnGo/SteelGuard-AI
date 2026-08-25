"""Backend-owned switch between the Phase 2 dummy and real AI adapter."""

import os

from PIL.Image import Image as PILImage

from app.schemas.prediction import DefectClass, Recommendation


AI_MODE_ENV = "STEELGUARD_AI_MODE"


def load_ai_mode() -> str:
    """Return an explicit adapter mode without automatic fallback."""

    mode = os.getenv(AI_MODE_ENV, "dummy").strip().lower()
    if mode not in {"dummy", "model"}:
        raise ValueError(f"{AI_MODE_ENV} must be dummy or model.")
    return mode


def initialize_ai() -> None:
    """Fail at backend startup when live model configuration is unusable."""

    if load_ai_mode() == "model":
        from ai.inference import get_model_engine, load_recommendation_map

        load_recommendation_map()
        get_model_engine()


def _run_model_inference(image: PILImage) -> dict:
    from ai.inference import run_inference as run_model_inference

    return run_model_inference(image)


def run_inference(image: PILImage) -> dict:
    """Run exactly one configured adapter and never hide a live failure."""

    if load_ai_mode() == "model":
        return _run_model_inference(image)
    return {
        "class_name": DefectClass.SCRATCHES,
        "confidence": 0.942,
        "recommendation": Recommendation.REWORK,
        "gradcam_image": None,
    }
