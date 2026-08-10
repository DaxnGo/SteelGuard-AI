"""Prediction boundary for mock development and future FastAPI integration.

The public ``predict_image`` interface always returns the same validated
internal structure. Only this module knows whether data comes from the local
mock fixture or ``POST /predict``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Literal, Mapping, TypedDict
from urllib.parse import urlparse

import requests

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

USE_MOCK_API_ENV = "STEELGUARD_USE_MOCK_API"
API_BASE_URL_ENV = "STEELGUARD_API_BASE_URL"
CONNECT_TIMEOUT_ENV = "STEELGUARD_API_CONNECT_TIMEOUT_SECONDS"
READ_TIMEOUT_ENV = "STEELGUARD_API_READ_TIMEOUT_SECONDS"

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOCK_RESPONSE_PATH = REPOSITORY_ROOT / "mock" / "prediction_response.json"

ErrorCategory = Literal[
    "configuration",
    "connection",
    "timeout",
    "request",
    "service",
    "invalid_response",
    "mock",
]


class PredictionData(TypedDict):
    """Normalized prediction fields consumed by presentation components."""

    class_name: str
    confidence: float
    recommendation: str
    gradcam_image: str


class PredictionResponse(TypedDict):
    """Stable internal success structure returned by ``predict_image``."""

    success: Literal[True]
    prediction: PredictionData


@dataclass(frozen=True)
class APIClientConfig:
    """Environment-derived mode and transport configuration."""

    use_mock_api: bool
    api_base_url: str | None = None
    connect_timeout_seconds: float | None = None
    read_timeout_seconds: float | None = None

    @property
    def prediction_url(self) -> str:
        """Return the configured future prediction endpoint."""

        if self.api_base_url is None:
            raise PredictionServiceError(
                "The AI service URL is not configured.",
                category="configuration",
                retryable=False,
            )
        return f"{self.api_base_url}/predict"

    @property
    def timeout(self) -> tuple[float, float]:
        """Return Requests connection and read timeout values."""

        if (
            self.connect_timeout_seconds is None
            or self.read_timeout_seconds is None
        ):
            raise PredictionServiceError(
                "The AI service timeouts are not configured.",
                category="configuration",
                retryable=False,
            )
        return self.connect_timeout_seconds, self.read_timeout_seconds


class PredictionServiceError(RuntimeError):
    """Client-independent, user-safe error raised at the service boundary."""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory = "invalid_response",
        retryable: bool = True,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


def predict_image(image_file: ValidatedImage) -> PredictionResponse:
    """Return one normalized prediction from the configured source."""

    if not isinstance(image_file, ValidatedImage) or not image_file.data:
        raise PredictionServiceError(
            "A valid image is required for inspection.",
            category="request",
            retryable=False,
        )

    config = load_api_client_config()
    if config.use_mock_api:
        raw_response = _predict_with_mock()
    else:
        raw_response = _predict_with_real_api(image_file, config)

    return validate_prediction_response(raw_response)


def load_api_client_config(
    environ: Mapping[str, str] | None = None,
) -> APIClientConfig:
    """Load mock/real mode without embedding deployment-specific values."""

    values = os.environ if environ is None else environ
    use_mock_api = _parse_boolean(
        values.get(USE_MOCK_API_ENV, "true"),
        variable_name=USE_MOCK_API_ENV,
    )
    if use_mock_api:
        return APIClientConfig(use_mock_api=True)

    api_base_url = _validate_api_base_url(values.get(API_BASE_URL_ENV))
    connect_timeout = _parse_positive_float(
        values.get(CONNECT_TIMEOUT_ENV),
        variable_name=CONNECT_TIMEOUT_ENV,
    )
    read_timeout = _parse_positive_float(
        values.get(READ_TIMEOUT_ENV),
        variable_name=READ_TIMEOUT_ENV,
    )
    return APIClientConfig(
        use_mock_api=False,
        api_base_url=api_base_url,
        connect_timeout_seconds=connect_timeout,
        read_timeout_seconds=read_timeout,
    )


def get_prediction_source_label() -> str:
    """Return a presentation-safe source label without leaking configuration."""

    try:
        config = load_api_client_config()
    except PredictionServiceError:
        return "API CONFIGURATION REQUIRED"
    return "MOCK AI MODE" if config.use_mock_api else "LIVE API MODE"


def validate_prediction_response(response: object) -> PredictionResponse:
    """Validate and normalize the success contract consumed by the UI."""

    if not isinstance(response, Mapping) or response.get("success") is not True:
        raise PredictionServiceError("The AI service returned an invalid response.")

    prediction = response.get("prediction")
    if not isinstance(prediction, Mapping):
        raise PredictionServiceError(
            "The AI service response is missing prediction data."
        )

    required_fields = {
        "class_name",
        "confidence",
        "recommendation",
        "gradcam_image",
    }
    if not required_fields.issubset(prediction):
        raise PredictionServiceError("The AI service response is incomplete.")

    class_name = prediction["class_name"]
    if not isinstance(class_name, str) or class_name not in SUPPORTED_CLASSES:
        raise PredictionServiceError(
            "The AI service returned an unsupported defect class."
        )

    confidence = prediction["confidence"]
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0.0 <= confidence <= 1.0
    ):
        raise PredictionServiceError(
            "The AI service returned an invalid confidence score."
        )

    recommendation = prediction["recommendation"]
    if (
        not isinstance(recommendation, str)
        or recommendation not in SUPPORTED_RECOMMENDATIONS
    ):
        raise PredictionServiceError(
            "The AI service returned an invalid recommendation."
        )

    gradcam_image = prediction["gradcam_image"]
    if not isinstance(gradcam_image, str) or not gradcam_image.strip():
        raise PredictionServiceError(
            "The AI service response is missing Grad-CAM output."
        )

    return {
        "success": True,
        "prediction": {
            "class_name": class_name,
            "confidence": float(confidence),
            "recommendation": recommendation,
            "gradcam_image": gradcam_image.strip(),
        },
    }


def _predict_with_mock() -> object:
    """Load the canonical fixture after an optional development-only delay."""

    delay_seconds = _mock_delay_seconds()
    if delay_seconds:
        time.sleep(delay_seconds)
    return _load_mock_response()


def _predict_with_real_api(
    image_file: ValidatedImage,
    config: APIClientConfig,
) -> object:
    """Submit one multipart request when real mode is explicitly enabled."""

    files = {
        "file": (
            image_file.filename,
            image_file.data,
            image_file.media_type,
        )
    }
    try:
        response = requests.post(
            config.prediction_url,
            files=files,
            headers={"Accept": "application/json"},
            timeout=config.timeout,
        )
    except requests.exceptions.Timeout as exc:
        raise PredictionServiceError(
            "Analysis did not complete in time. Please try again.",
            category="timeout",
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise PredictionServiceError(
            "The AI service could not be reached. Please try again.",
            category="connection",
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise PredictionServiceError(
            "The AI service request failed. Please try again.",
            category="request",
        ) from exc

    _raise_for_http_status(response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise PredictionServiceError(
            "The AI service returned malformed JSON.",
            category="invalid_response",
        ) from exc


def _raise_for_http_status(status_code: int) -> None:
    """Map transport statuses to safe frontend service errors."""

    if status_code == 200:
        return
    if status_code == 400:
        raise PredictionServiceError(
            "The AI service could not process this image. Choose another image.",
            category="request",
            retryable=False,
        )
    if status_code == 415:
        raise PredictionServiceError(
            "Unsupported image format. Choose a JPG, JPEG, or PNG image.",
            category="request",
            retryable=False,
        )
    if status_code == 422:
        raise PredictionServiceError(
            "The AI service could not validate this image. Choose another image.",
            category="request",
            retryable=False,
        )
    if status_code == 503:
        raise PredictionServiceError(
            "The AI service is temporarily unavailable. Please try again.",
            category="service",
        )
    if 500 <= status_code <= 599:
        raise PredictionServiceError(
            "The AI service encountered an internal error. Please try again.",
            category="service",
        )
    if 400 <= status_code <= 499:
        raise PredictionServiceError(
            "The AI service rejected the request. Please check the image.",
            category="request",
            retryable=False,
        )
    raise PredictionServiceError(
        "The AI service returned an unexpected status.",
        category="service",
    )


def _parse_boolean(raw_value: str, *, variable_name: str) -> bool:
    """Parse one explicit environment boolean."""

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise PredictionServiceError(
        f"{variable_name} must be true or false.",
        category="configuration",
        retryable=False,
    )


def _validate_api_base_url(raw_value: str | None) -> str:
    """Require a credential-free HTTP(S) base URL in real mode."""

    if raw_value is None or not raw_value.strip():
        raise PredictionServiceError(
            f"{API_BASE_URL_ENV} is required when mock mode is disabled.",
            category="configuration",
            retryable=False,
        )

    base_url = raw_value.strip().rstrip("/")
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise PredictionServiceError(
            f"{API_BASE_URL_ENV} must be a credential-free HTTP(S) base URL.",
            category="configuration",
            retryable=False,
        )
    return base_url


def _parse_positive_float(
    raw_value: str | None,
    *,
    variable_name: str,
) -> float:
    """Require one finite positive timeout without inventing a default."""

    if raw_value is None or not raw_value.strip():
        raise PredictionServiceError(
            f"{variable_name} is required when mock mode is disabled.",
            category="configuration",
            retryable=False,
        )
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise PredictionServiceError(
            f"{variable_name} must be a positive number.",
            category="configuration",
            retryable=False,
        ) from exc
    if not math.isfinite(value) or value <= 0:
        raise PredictionServiceError(
            f"{variable_name} must be a positive number.",
            category="configuration",
            retryable=False,
        )
    return value


def _load_mock_response() -> object:
    """Load the canonical repository mock fixture."""

    configured_path = os.getenv("STEELGUARD_MOCK_RESPONSE_PATH")
    mock_path = Path(configured_path) if configured_path else DEFAULT_MOCK_RESPONSE_PATH

    try:
        if mock_path.is_file():
            with mock_path.open(encoding="utf-8") as response_file:
                return json.load(response_file)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PredictionServiceError(
            "The mock AI response could not be loaded.",
            category="mock",
            retryable=False,
        ) from exc

    raise PredictionServiceError(
        "The mock AI response was not found.",
        category="mock",
        retryable=False,
    )


def _mock_delay_seconds() -> float:
    """Return a small configurable delay so the mock loading state is visible."""

    raw_value = os.getenv("STEELGUARD_MOCK_DELAY_SECONDS", "0.6")
    try:
        delay = float(raw_value)
    except ValueError:
        return 0.6
    return max(0.0, min(delay, 3.0))
