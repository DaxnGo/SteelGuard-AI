import importlib.util
import json

from PIL import Image
import pytest

from ai.inference import RECOMMENDATION_MAP_ENV, reset_model_engine, run_inference


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("ultralytics") is None,
    reason="Ultralytics runtime is only installed in the model container.",
)


def test_bundled_model_runs_one_gradcam_inference(monkeypatch):
    mapping = {
        label: "REWORK"
        for label in (
            "Crazing",
            "Inclusion",
            "Patches",
            "Pitted Surface",
            "Rolled-in Scale",
            "Scratches",
        )
    }
    monkeypatch.setenv(RECOMMENDATION_MAP_ENV, json.dumps(mapping))
    monkeypatch.setenv("STEELGUARD_CONFIDENCE_THRESHOLD", "0")
    reset_model_engine()

    result = run_inference(Image.new("RGB", (200, 200), color=(127, 127, 127)))

    assert result["class_name"] in mapping
    assert 0 <= result["confidence"] <= 1
    assert result["recommendation"] == "REWORK"
    assert result["gradcam_image"].startswith("data:image/png;base64,")
