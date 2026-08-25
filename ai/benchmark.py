"""Reproducible CPU benchmark for the provisional SteelGuard model adapter."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time

from PIL import Image, ImageDraw

from ai.inference import MODEL_CLASS_MAP, ModelEngine


DEFAULT_MODEL_PATH = Path(__file__).with_name("best.pt")


def percentile(values: list[float], quantile: float) -> float:
    """Return a linearly interpolated percentile for a non-empty sample."""

    if not values or not 0 <= quantile <= 1:
        raise ValueError("A non-empty sample and quantile from 0 to 1 are required.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def create_synthetic_image() -> Image.Image:
    """Create one deterministic texture for a dataset-free technical check."""

    image = Image.new("RGB", (640, 640), color=(112, 118, 124))
    drawing = ImageDraw.Draw(image)
    for offset in range(0, 640, 16):
        shade = 70 + (offset * 13) % 140
        drawing.line((offset, 0, 639 - offset // 2, 639), fill=(shade, shade, shade))
        drawing.line((0, offset, 639, offset), fill=(shade, shade + 5, shade + 10))
    return image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def _peak_rss_mib() -> float | None:
    try:
        import resource
    except ImportError:
        return None
    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        peak /= 1024
    return round(peak / 1024, 2)


def run_benchmark(
    *,
    model_path: Path,
    image_path: Path | None,
    warmup_runs: int,
    measured_runs: int,
    confidence_threshold: float,
) -> dict[str, object]:
    """Measure full class-plus-Grad-CAM inference after one model load."""

    if warmup_runs < 0 or measured_runs < 1:
        raise ValueError("Warmup must be non-negative and measured runs must be positive.")
    if not 0 <= confidence_threshold <= 1:
        raise ValueError("Confidence threshold must be from 0 to 1.")

    resolved_model = model_path.expanduser().resolve()
    if image_path is None:
        image = create_synthetic_image()
        input_source = "deterministic synthetic texture"
    else:
        resolved_image = image_path.expanduser().resolve()
        with Image.open(resolved_image) as opened:
            image = opened.convert("RGB")
            image.load()
        input_source = str(resolved_image)

    startup_started = time.perf_counter()
    engine = ModelEngine(resolved_model, confidence_threshold)
    model_startup_ms = (time.perf_counter() - startup_started) * 1000
    result: tuple[str, float, Image.Image] | None = None
    for _ in range(warmup_runs):
        result = engine.predict(image)

    durations_ms = []
    for _ in range(measured_runs):
        started = time.perf_counter()
        result = engine.predict(image)
        durations_ms.append((time.perf_counter() - started) * 1000)

    assert result is not None
    class_name, confidence, gradcam = result
    layers = list(engine._model.model)
    target_index = layers.index(engine._target_layer)
    first_upsample_index = next(
        index
        for index, layer in enumerate(layers)
        if type(layer).__name__ == "Upsample"
    )
    checksum_path = resolved_model.with_suffix(resolved_model.suffix + ".sha256")
    expected_checksum = checksum_path.read_text(encoding="ascii").split()[0].lower()
    model_digest = _sha256(resolved_model)

    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "CPU adapter samples include classification and Grad-CAM; "
            "model startup is measured separately"
        ),
        "input": {
            "source": input_source,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        },
        "model": {
            "path": str(resolved_model),
            "bytes": resolved_model.stat().st_size,
            "sha256": model_digest,
            "checksum_matches_sidecar": model_digest == expected_checksum,
            "checkpoint_class_order": list(MODEL_CLASS_MAP),
            "api_class_order": list(MODEL_CLASS_MAP.values()),
            "input_size": 640,
            "confidence_threshold": confidence_threshold,
            "gradcam_target_index": target_index,
            "gradcam_target_type": type(engine._target_layer).__name__,
            "first_upsample_index": first_upsample_index,
        },
        "runtime": {
            "python": platform.python_version(),
            "pytorch": engine._torch.__version__,
            "ultralytics": version("ultralytics"),
            "platform": platform.platform(),
            "cpu_model": _cpu_model(),
            "logical_cpu_count": os.cpu_count(),
            "process_peak_rss_mib": _peak_rss_mib(),
        },
        "runs": {
            "model_startup_ms": round(model_startup_ms, 2),
            "warmup": warmup_runs,
            "measured": measured_runs,
            "minimum_ms": round(min(durations_ms), 2),
            "mean_ms": round(statistics.fmean(durations_ms), 2),
            "median_ms": round(statistics.median(durations_ms), 2),
            "p95_ms": round(percentile(durations_ms, 0.95), 2),
            "maximum_ms": round(max(durations_ms), 2),
        },
        "last_result": {
            "class_name": class_name,
            "confidence": round(confidence, 6),
            "gradcam_width": gradcam.width,
            "gradcam_height": gradcam.height,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--confidence-threshold", type=float, default=0.0)
    arguments = parser.parse_args()
    report = run_benchmark(
        model_path=arguments.model,
        image_path=arguments.image,
        warmup_runs=arguments.warmup,
        measured_runs=arguments.runs,
        confidence_threshold=arguments.confidence_threshold,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
