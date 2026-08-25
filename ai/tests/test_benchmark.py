from pathlib import Path

import pytest

from ai.benchmark import create_synthetic_image, percentile, run_benchmark


def test_percentile_interpolates_and_validates_input() -> None:
    assert percentile([10.0, 20.0, 30.0], 0.5) == 20.0
    assert percentile([10.0, 20.0], 0.95) == pytest.approx(19.5)
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_synthetic_benchmark_image_is_deterministic() -> None:
    first = create_synthetic_image()
    second = create_synthetic_image()

    assert first.size == (640, 640)
    assert first.mode == "RGB"
    assert first.tobytes() == second.tobytes()


def test_benchmark_rejects_invalid_run_configuration_before_model_load() -> None:
    with pytest.raises(ValueError):
        run_benchmark(
            model_path=Path("missing.pt"),
            image_path=None,
            warmup_runs=-1,
            measured_runs=1,
            confidence_threshold=0.0,
        )
    with pytest.raises(ValueError):
        run_benchmark(
            model_path=Path("missing.pt"),
            image_path=None,
            warmup_runs=0,
            measured_runs=1,
            confidence_threshold=float("nan"),
        )
