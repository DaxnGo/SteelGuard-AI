import base64
import hashlib
from io import BytesIO
import json

from PIL import Image
import pytest

from ai.inference import (
    AIConfigurationError,
    RECOMMENDATION_MAP_ENV,
    encode_png_data_uri,
    load_recommendation_map,
    map_model_class,
    verify_model_artifact,
)


EXPECTED_LABELS = {
    "Crazing",
    "Inclusion",
    "Patches",
    "Pitted Surface",
    "Rolled-in Scale",
    "Scratches",
}


def _recommendations(value: str = "REWORK") -> dict[str, str]:
    return {label: value for label in EXPECTED_LABELS}


def test_model_class_mapping_matches_api_contract():
    assert map_model_class("crazing") == "Crazing"
    assert map_model_class("pitted_surface") == "Pitted Surface"
    assert map_model_class("rolled-in_scale") == "Rolled-in Scale"
    assert map_model_class("scratches") == "Scratches"

    with pytest.raises(AIConfigurationError):
        map_model_class("unknown")


def test_recommendation_map_is_explicit_and_complete():
    with pytest.raises(AIConfigurationError, match=RECOMMENDATION_MAP_ENV):
        load_recommendation_map({})

    configured = load_recommendation_map(
        {RECOMMENDATION_MAP_ENV: json.dumps(_recommendations())}
    )
    assert configured == _recommendations()


@pytest.mark.parametrize("invalid_value", ["MAYBE", "", None])
def test_recommendation_map_rejects_unapproved_values(invalid_value):
    mapping = _recommendations()
    mapping["Scratches"] = invalid_value

    with pytest.raises(AIConfigurationError):
        load_recommendation_map({RECOMMENDATION_MAP_ENV: json.dumps(mapping)})


def test_gradcam_transport_is_a_valid_png_data_uri():
    image = Image.new("RGB", (8, 6), color=(120, 20, 10))

    data_uri = encode_png_data_uri(image)

    prefix, encoded = data_uri.split(",", 1)
    assert prefix == "data:image/png;base64"
    decoded = base64.b64decode(encoded, validate=True)
    with Image.open(BytesIO(decoded)) as parsed:
        assert parsed.format == "PNG"
        assert parsed.size == image.size


def test_model_artifact_checksum_is_verified(tmp_path):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"steelguard-model")
    checksum_path = tmp_path / "model.pt.sha256"
    checksum_path.write_text(
        hashlib.sha256(b"steelguard-model").hexdigest() + "  model.pt\n",
        encoding="ascii",
    )

    verify_model_artifact(model_path, checksum_path)

    model_path.write_bytes(b"tampered")
    with pytest.raises(AIConfigurationError, match="checksum"):
        verify_model_artifact(model_path, checksum_path)
