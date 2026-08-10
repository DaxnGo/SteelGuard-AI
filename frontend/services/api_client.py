"""Prediction service boundary using mock data for the frontend MVP.

The public ``predict_image`` interface is intentionally shaped so the mock
implementation can later be replaced with ``POST /predict`` without changing
presentation components.
"""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Mapping

from utils.image_validator import ValidatedImage


SUPPORTED_CLASSES = frozenset(
    {
        "Crazing",
        "Inclusion",
        "Patches",
        "Pitted Surface",
        "Rolled-in Scale",
        "Scratches",
    }
)
SUPPORTED_RECOMMENDATIONS = frozenset({"ACCEPT", "REWORK", "REJECT"})

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOCK_RESPONSE_PATH = REPOSITORY_ROOT / "mock" / "prediction_response.json"

PACKAGED_MOCK_RESPONSE: dict[str, Any] = {
    "success": True,
    "prediction": {
        "class_name": "Scratches",
        "confidence": 0.942,
        "recommendation": "REWORK",
        "gradcam_image": "mock_gradcam.png",
    },
}


class PredictionServiceError(RuntimeError):
    """A safe prediction-service error for the application boundary."""


def predict_image(image_file: ValidatedImage) -> dict[str, Any]:
    """Return one validated mock prediction for one validated image."""

    if not isinstance(image_file, ValidatedImage) or not image_file.data:
        raise PredictionServiceError("A valid image is required for inspection.")

    delay_seconds = _mock_delay_seconds()
    if delay_seconds:
        time.sleep(delay_seconds)

    response = _load_mock_response()
    return validate_prediction_response(response)


def validate_prediction_response(response: object) -> dict[str, Any]:
    """Validate and normalize the prediction contract consumed by the UI."""

    if not isinstance(response, Mapping) or response.get("success") is not True:
        raise PredictionServiceError("The AI service returned an invalid response.")

    prediction = response.get("prediction")
    if not isinstance(prediction, Mapping):
        raise PredictionServiceError("The AI service response is missing prediction data.")

    required_fields = {
        "class_name",
        "confidence",
        "recommendation",
        "gradcam_image",
    }
    if not required_fields.issubset(prediction):
        raise PredictionServiceError("The AI service response is incomplete.")

    class_name = prediction["class_name"]
    if class_name not in SUPPORTED_CLASSES:
        raise PredictionServiceError("The AI service returned an unsupported defect class.")

    confidence = prediction["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0.0 <= confidence <= 1.0
    ):
        raise PredictionServiceError("The AI service returned an invalid confidence score.")

    recommendation = prediction["recommendation"]
    if recommendation not in SUPPORTED_RECOMMENDATIONS:
        raise PredictionServiceError("The AI service returned an invalid recommendation.")

    gradcam_image = prediction["gradcam_image"]
    if not isinstance(gradcam_image, str) or not gradcam_image.strip():
        raise PredictionServiceError("The AI service response is missing Grad-CAM output.")

    return {
        "success": True,
        "prediction": {
            "class_name": class_name,
            "confidence": float(confidence),
            "recommendation": recommendation,
            "gradcam_image": gradcam_image.strip(),
        },
    }


def _load_mock_response() -> dict[str, Any]:
    """Load the repository fixture, with a packaged fallback for containers."""

    configured_path = os.getenv("STEELGUARD_MOCK_RESPONSE_PATH")
    mock_path = Path(configured_path) if configured_path else DEFAULT_MOCK_RESPONSE_PATH

    if mock_path.is_file():
        try:
            with mock_path.open(encoding="utf-8") as response_file:
                response = json.load(response_file)
        except (OSError, json.JSONDecodeError) as exc:
            raise PredictionServiceError("The mock AI response could not be loaded.") from exc
        return response

    if configured_path:
        raise PredictionServiceError("The configured mock AI response was not found.")

    return deepcopy(PACKAGED_MOCK_RESPONSE)


def _mock_delay_seconds() -> float:
    """Return a small configurable delay so the mock loading state is visible."""

    raw_value = os.getenv("STEELGUARD_MOCK_DELAY_SECONDS", "0.6")
    try:
        delay = float(raw_value)
    except ValueError:
        return 0.6
    return max(0.0, min(delay, 3.0))
