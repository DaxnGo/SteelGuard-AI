"""In-process inference adapter for the bundled SteelGuard YOLO checkpoint."""

from __future__ import annotations

import base64
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import threading
from typing import Mapping

from PIL import Image, ImageOps


MODEL_PATH_ENV = "STEELGUARD_MODEL_PATH"
RECOMMENDATION_MAP_ENV = "STEELGUARD_RECOMMENDATION_MAP_JSON"
CONFIDENCE_THRESHOLD_ENV = "STEELGUARD_CONFIDENCE_THRESHOLD"
MODEL_INPUT_SIZE = 640

MODEL_CLASS_MAP = {
    "crazing": "Crazing",
    "inclusion": "Inclusion",
    "patches": "Patches",
    "pitted_surface": "Pitted Surface",
    "rolled-in_scale": "Rolled-in Scale",
    "scratches": "Scratches",
}
RECOMMENDATIONS = {"ACCEPT", "REWORK", "REJECT"}


class AIConfigurationError(RuntimeError):
    """The model artifact or required live-mode configuration is invalid."""


class AIInferenceError(RuntimeError):
    """The configured model could not produce one complete prediction."""


def map_model_class(model_name: str) -> str:
    """Map one checkpoint label to the exact public API label."""

    try:
        return MODEL_CLASS_MAP[model_name]
    except (KeyError, TypeError) as exc:
        raise AIConfigurationError(
            f"Unsupported model class label: {model_name!r}."
        ) from exc


def load_recommendation_map(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Load the domain-approved class-to-recommendation mapping."""

    values = os.environ if environ is None else environ
    raw_mapping = values.get(RECOMMENDATION_MAP_ENV)
    if raw_mapping is None or not raw_mapping.strip():
        raise AIConfigurationError(
            f"{RECOMMENDATION_MAP_ENV} is required in model mode."
        )
    try:
        parsed = json.loads(raw_mapping)
    except json.JSONDecodeError as exc:
        raise AIConfigurationError(
            f"{RECOMMENDATION_MAP_ENV} must be a JSON object."
        ) from exc

    expected_labels = set(MODEL_CLASS_MAP.values())
    if not isinstance(parsed, dict) or set(parsed) != expected_labels:
        raise AIConfigurationError(
            f"{RECOMMENDATION_MAP_ENV} must define exactly all six API labels."
        )
    if any(value not in RECOMMENDATIONS for value in parsed.values()):
        raise AIConfigurationError(
            f"{RECOMMENDATION_MAP_ENV} values must be ACCEPT, REWORK, or REJECT."
        )
    return dict(parsed)


def encode_png_data_uri(image: Image.Image) -> str:
    """Encode one in-memory explanation image using the D-05 MVP transport."""

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_model_artifact(model_path: Path, checksum_path: Path) -> None:
    """Fail before loading an absent or altered pickle-based model artifact."""

    if not model_path.is_file():
        raise AIConfigurationError(f"Model artifact not found: {model_path}.")
    if not checksum_path.is_file():
        raise AIConfigurationError(f"Model checksum not found: {checksum_path}.")

    try:
        expected = checksum_path.read_text(encoding="ascii").split()[0].lower()
    except (OSError, UnicodeError, IndexError) as exc:
        raise AIConfigurationError("Model checksum file is invalid.") from exc
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise AIConfigurationError("Model checksum file is invalid.")

    digest = hashlib.sha256()
    with model_path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise AIConfigurationError("Model artifact checksum does not match.")


def _load_confidence_threshold(
    environ: Mapping[str, str] | None = None,
) -> float:
    values = os.environ if environ is None else environ
    raw_value = values.get(CONFIDENCE_THRESHOLD_ENV, "0.25")
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise AIConfigurationError(
            f"{CONFIDENCE_THRESHOLD_ENV} must be a number from 0 to 1."
        ) from exc
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise AIConfigurationError(
            f"{CONFIDENCE_THRESHOLD_ENV} must be a number from 0 to 1."
        )
    return value


class ModelEngine:
    """Load the verified model once and serialize gradient-based inference."""

    def __init__(self, model_path: Path, confidence_threshold: float):
        checksum_path = model_path.with_suffix(model_path.suffix + ".sha256")
        verify_model_artifact(model_path, checksum_path)

        try:
            import torch
            from ultralytics import YOLO
        except ImportError as exc:
            raise AIConfigurationError(
                "The Ultralytics CPU runtime is not installed."
            ) from exc

        try:
            yolo = YOLO(str(model_path))
        except Exception as exc:
            raise AIConfigurationError("The model artifact could not be loaded.") from exc
        if yolo.task != "detect":
            raise AIConfigurationError("The bundled artifact is not a detection model.")

        names = yolo.names
        ordered_names = [names[index] for index in range(len(names))]
        if ordered_names != list(MODEL_CLASS_MAP):
            raise AIConfigurationError("The model class map does not match SteelGuard.")

        self._torch = torch
        self._model = yolo.model.to("cpu").eval()
        self._target_layer = self._find_gradcam_layer()
        self._confidence_threshold = confidence_threshold
        self._inference_lock = threading.Lock()

    def _find_gradcam_layer(self):
        layers = list(self._model.model)
        first_upsample = next(
            (
                index
                for index, layer in enumerate(layers)
                if type(layer).__name__ == "Upsample"
            ),
            None,
        )
        if first_upsample is None or first_upsample == 0:
            raise AIConfigurationError("A compatible Grad-CAM layer was not found.")
        return layers[first_upsample - 1]

    def predict(self, image: Image.Image) -> tuple[str, float, Image.Image]:
        """Return class, confidence, and Grad-CAM from one forward pass."""

        rgb_image = image.convert("RGB")
        tensor, crop = self._preprocess(rgb_image)
        torch = self._torch

        with self._inference_lock:
            activations = []
            hook = self._target_layer.register_forward_hook(
                lambda _module, _inputs, output: activations.append(output)
            )
            try:
                self._model.zero_grad(set_to_none=True)
                with torch.enable_grad():
                    output = self._model(tensor)
                    predictions = (
                        output[0] if isinstance(output, (tuple, list)) else output
                    )
                    if (
                        predictions.ndim != 3
                        or predictions.shape[1] != 4 + len(MODEL_CLASS_MAP)
                    ):
                        raise AIInferenceError("The model returned an unexpected tensor.")

                    scores = predictions[0, 4:, :]
                    flat_scores = scores.reshape(-1)
                    selected_index = int(flat_scores.argmax())
                    selected_score = flat_scores[selected_index]
                    confidence = float(selected_score.detach().cpu())
                    if (
                        not math.isfinite(confidence)
                        or confidence < self._confidence_threshold
                    ):
                        raise AIInferenceError(
                            "No defect prediction met the configured confidence threshold."
                        )

                    activation = activations[0]
                    activation.retain_grad()
                    selected_score.backward()
                    if activation.grad is None:
                        raise AIInferenceError("Grad-CAM gradients were unavailable.")

                class_id = selected_index // scores.shape[1]
                class_name = map_model_class(list(MODEL_CLASS_MAP)[class_id])
                gradcam = self._build_gradcam(
                    rgb_image,
                    activation.detach(),
                    activation.grad.detach(),
                    crop,
                )
                return class_name, confidence, gradcam
            except AIInferenceError:
                raise
            except Exception as exc:
                raise AIInferenceError("Model inference failed.") from exc
            finally:
                hook.remove()

    def _preprocess(self, image: Image.Image):
        torch = self._torch
        width, height = image.size
        if width <= 0 or height <= 0:
            raise AIInferenceError("The decoded image has invalid dimensions.")

        scale = min(MODEL_INPUT_SIZE / width, MODEL_INPUT_SIZE / height)
        resized_width = max(1, round(width * scale))
        resized_height = max(1, round(height * scale))
        resized = image.resize(
            (resized_width, resized_height),
            Image.Resampling.BILINEAR,
        )
        left = (MODEL_INPUT_SIZE - resized_width) // 2
        top = (MODEL_INPUT_SIZE - resized_height) // 2
        canvas = Image.new(
            "RGB",
            (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE),
            color=(114, 114, 114),
        )
        canvas.paste(resized, (left, top))

        try:
            import numpy as np
        except ImportError as exc:
            raise AIConfigurationError("NumPy is required for model inference.") from exc
        pixels = np.asarray(canvas, dtype=np.float32) / 255.0
        pixels = np.ascontiguousarray(pixels.transpose(2, 0, 1))
        tensor = torch.from_numpy(pixels).unsqueeze(0).requires_grad_(True)
        return tensor, (left, top, resized_width, resized_height)

    def _build_gradcam(self, image, activation, gradient, crop):
        torch = self._torch
        weights = gradient.mean(dim=(2, 3), keepdim=True)
        heatmap = torch.relu((weights * activation).sum(dim=1, keepdim=True))
        heatmap = torch.nn.functional.interpolate(
            heatmap,
            size=(MODEL_INPUT_SIZE, MODEL_INPUT_SIZE),
            mode="bilinear",
            align_corners=False,
        )[0, 0]

        left, top, width, height = crop
        heatmap = heatmap[top : top + height, left : left + width]
        heatmap -= heatmap.min()
        maximum = float(heatmap.max().cpu())
        if not math.isfinite(maximum) or maximum <= 0:
            raise AIInferenceError("Grad-CAM could not be generated.")
        heatmap = (heatmap / maximum * 255).byte().cpu().numpy()

        grayscale = Image.fromarray(heatmap, mode="L").resize(
            image.size,
            Image.Resampling.BILINEAR,
        )
        colored = ImageOps.colorize(
            grayscale,
            black=(0, 0, 80),
            mid=(255, 220, 0),
            white=(255, 0, 0),
        )
        return Image.blend(image, colored, alpha=0.45)


_engine: ModelEngine | None = None
_engine_lock = threading.Lock()


def get_model_engine() -> ModelEngine:
    """Return the process-wide verified model instance."""

    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                configured_path = os.getenv(MODEL_PATH_ENV)
                model_path = (
                    Path(configured_path).expanduser().resolve()
                    if configured_path
                    else Path(__file__).with_name("best.pt")
                )
                _engine = ModelEngine(model_path, _load_confidence_threshold())
    return _engine


def reset_model_engine() -> None:
    """Clear the cached engine for isolated tests and controlled reloads."""

    global _engine
    with _engine_lock:
        _engine = None


def run_inference(image: Image.Image) -> dict[str, object]:
    """Return one contract-shaped live prediction with no fallback data."""

    recommendations = load_recommendation_map()
    class_name, confidence, gradcam = get_model_engine().predict(image)
    return {
        "class_name": class_name,
        "confidence": round(confidence, 6),
        "recommendation": recommendations[class_name],
        "gradcam_image": encode_png_data_uri(gradcam),
    }
