"""Tests for the mock prediction-service contract."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import os
import unittest
from unittest.mock import patch

from PIL import Image

from services.api_client import (
    PACKAGED_MOCK_RESPONSE,
    PredictionServiceError,
    SUPPORTED_CLASSES,
    predict_image,
    validate_prediction_response,
)
from utils.image_validator import validate_image_bytes


def validated_test_image():
    image_bytes = BytesIO()
    Image.new("RGB", (32, 32), color=(95, 105, 115)).save(image_bytes, format="PNG")
    return validate_image_bytes("surface.png", image_bytes.getvalue())


class PredictionServiceTests(unittest.TestCase):
    def test_predict_image_returns_contract_shaped_mock(self) -> None:
        with patch.dict(os.environ, {"STEELGUARD_MOCK_DELAY_SECONDS": "0"}):
            response = predict_image(validated_test_image())

        self.assertTrue(response["success"])
        self.assertEqual(response["prediction"]["class_name"], "Scratches")
        self.assertEqual(response["prediction"]["confidence"], 0.942)
        self.assertEqual(response["prediction"]["recommendation"], "REWORK")

    def test_accepts_every_supported_defect_class(self) -> None:
        for class_name in SUPPORTED_CLASSES:
            with self.subTest(class_name=class_name):
                response = deepcopy(PACKAGED_MOCK_RESPONSE)
                response["prediction"]["class_name"] = class_name
                normalized = validate_prediction_response(response)
                self.assertEqual(normalized["prediction"]["class_name"], class_name)

    def test_rejects_missing_prediction_fields(self) -> None:
        response = deepcopy(PACKAGED_MOCK_RESPONSE)
        del response["prediction"]["gradcam_image"]
        with self.assertRaisesRegex(PredictionServiceError, "incomplete"):
            validate_prediction_response(response)

    def test_rejects_invalid_success_and_enums(self) -> None:
        cases = (
            ("success", False),
            ("class_name", "Unknown"),
            ("recommendation", "HOLD"),
        )

        for field, value in cases:
            with self.subTest(field=field):
                response = deepcopy(PACKAGED_MOCK_RESPONSE)
                if field == "success":
                    response[field] = value
                else:
                    response["prediction"][field] = value
                with self.assertRaises(PredictionServiceError):
                    validate_prediction_response(response)

    def test_rejects_invalid_confidence_values(self) -> None:
        for value in (-0.1, 1.1, True, "0.9", float("nan"), float("inf")):
            with self.subTest(value=value):
                response = deepcopy(PACKAGED_MOCK_RESPONSE)
                response["prediction"]["confidence"] = value
                with self.assertRaisesRegex(PredictionServiceError, "confidence"):
                    validate_prediction_response(response)

    def test_configured_missing_mock_fixture_is_a_safe_failure(self) -> None:
        environment = {
            "STEELGUARD_MOCK_DELAY_SECONDS": "0",
            "STEELGUARD_MOCK_RESPONSE_PATH": "missing/mock-response.json",
        }
        with patch.dict(os.environ, environment, clear=False):
            with self.assertRaisesRegex(PredictionServiceError, "not found"):
                predict_image(validated_test_image())


if __name__ == "__main__":
    unittest.main()
