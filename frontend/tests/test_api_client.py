"""Tests for the mock prediction-service contract."""

from __future__ import annotations

from io import BytesIO
import os
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import requests

from services.api_client import (
    API_BASE_URL_ENV,
    CONNECT_TIMEOUT_ENV,
    PredictionServiceError,
    READ_TIMEOUT_ENV,
    SUPPORTED_CLASSES,
    SUPPORTED_RECOMMENDATIONS,
    USE_MOCK_API_ENV,
    get_prediction_source_label,
    load_api_client_config,
    predict_image,
    validate_prediction_response,
)
from utils.image_validator import validate_image_bytes


def validated_test_image():
    image_bytes = BytesIO()
    Image.new("RGB", (32, 32), color=(95, 105, 115)).save(image_bytes, format="PNG")
    return validate_image_bytes("surface.png", image_bytes.getvalue())


def valid_prediction_response() -> dict:
    """Return an independent valid response for contract-negative tests."""

    return {
        "success": True,
        "prediction": {
            "class_name": "Scratches",
            "confidence": 0.942,
            "recommendation": "REWORK",
            "gradcam_image": "mock_gradcam.png",
        },
    }


def real_api_environment() -> dict[str, str]:
    """Return explicit test-only real-mode transport configuration."""

    return {
        USE_MOCK_API_ENV: "false",
        API_BASE_URL_ENV: "http://backend.test:8000",
        CONNECT_TIMEOUT_ENV: "1.25",
        READ_TIMEOUT_ENV: "8.5",
    }


class PredictionServiceTests(unittest.TestCase):
    def test_predict_image_returns_contract_shaped_mock(self) -> None:
        environment = {
            USE_MOCK_API_ENV: "true",
            "STEELGUARD_MOCK_DELAY_SECONDS": "0",
        }
        with patch.dict(os.environ, environment):
            with patch("services.api_client.requests.post") as post:
                response = predict_image(validated_test_image())

        post.assert_not_called()
        self.assertTrue(response["success"])
        self.assertEqual(response["prediction"]["class_name"], "Scratches")
        self.assertEqual(response["prediction"]["confidence"], 0.942)
        self.assertEqual(response["prediction"]["recommendation"], "REWORK")
        self.assertIsNone(response["prediction"]["gradcam_image"])

    def test_accepts_every_supported_defect_class(self) -> None:
        for class_name in SUPPORTED_CLASSES:
            with self.subTest(class_name=class_name):
                response = valid_prediction_response()
                response["prediction"]["class_name"] = class_name
                normalized = validate_prediction_response(response)
                self.assertEqual(normalized["prediction"]["class_name"], class_name)

    def test_accepts_every_supported_recommendation(self) -> None:
        for recommendation in SUPPORTED_RECOMMENDATIONS:
            with self.subTest(recommendation=recommendation):
                response = valid_prediction_response()
                response["prediction"]["recommendation"] = recommendation
                normalized = validate_prediction_response(response)
                self.assertEqual(
                    normalized["prediction"]["recommendation"],
                    recommendation,
                )

    def test_rejects_missing_prediction_fields(self) -> None:
        response = valid_prediction_response()
        del response["prediction"]["gradcam_image"]
        with self.assertRaisesRegex(PredictionServiceError, "incomplete"):
            validate_prediction_response(response)

    def test_rejects_invalid_success_and_enum_values(self) -> None:
        cases = (
            ("success", False),
            ("class_name", "Unknown"),
            ("recommendation", "HOLD"),
        )

        for field, value in cases:
            with self.subTest(field=field):
                response = valid_prediction_response()
                if field == "success":
                    response[field] = value
                else:
                    response["prediction"][field] = value
                with self.assertRaises(PredictionServiceError):
                    validate_prediction_response(response)

    def test_rejects_non_string_enum_values_as_service_errors(self) -> None:
        cases = (
            ("class_name", ["Scratches"]),
            ("class_name", {"name": "Scratches"}),
            ("recommendation", ["REWORK"]),
            ("recommendation", {"value": "REWORK"}),
        )

        for field, value in cases:
            with self.subTest(field=field, value=value):
                response = valid_prediction_response()
                response["prediction"][field] = value
                with self.assertRaises(PredictionServiceError):
                    validate_prediction_response(response)

    def test_rejects_invalid_confidence_values(self) -> None:
        for value in (-0.1, 1.1, True, "0.9", float("nan"), float("inf")):
            with self.subTest(value=value):
                response = valid_prediction_response()
                response["prediction"]["confidence"] = value
                with self.assertRaisesRegex(PredictionServiceError, "confidence"):
                    validate_prediction_response(response)

    def test_rejects_invalid_gradcam_references(self) -> None:
        for value in ("", "   ", ["mock_gradcam.png"]):
            with self.subTest(value=value):
                response = valid_prediction_response()
                response["prediction"]["gradcam_image"] = value
                with self.assertRaisesRegex(PredictionServiceError, "Grad-CAM"):
                    validate_prediction_response(response)

    def test_accepts_null_gradcam_during_dummy_stage(self) -> None:
        response = valid_prediction_response()
        response["prediction"]["gradcam_image"] = None

        normalized = validate_prediction_response(response)

        self.assertIsNone(normalized["prediction"]["gradcam_image"])

    def test_configured_missing_mock_fixture_is_a_safe_failure(self) -> None:
        environment = {
            USE_MOCK_API_ENV: "true",
            "STEELGUARD_MOCK_DELAY_SECONDS": "0",
            "STEELGUARD_MOCK_RESPONSE_PATH": "missing/mock-response.json",
        }
        with patch.dict(os.environ, environment, clear=False):
            with self.assertRaisesRegex(PredictionServiceError, "not found"):
                predict_image(validated_test_image())


class APIClientConfigurationTests(unittest.TestCase):
    def test_mock_mode_is_the_safe_default(self) -> None:
        config = load_api_client_config({})

        self.assertTrue(config.use_mock_api)
        self.assertIsNone(config.api_base_url)
        self.assertIsNone(config.connect_timeout_seconds)
        self.assertIsNone(config.read_timeout_seconds)

    def test_source_label_is_owned_by_client_configuration(self) -> None:
        with patch.dict(os.environ, {USE_MOCK_API_ENV: "true"}, clear=True):
            self.assertEqual(get_prediction_source_label(), "MOCK AI MODE")

        with patch.dict(os.environ, real_api_environment(), clear=True):
            self.assertEqual(get_prediction_source_label(), "LIVE API MODE")

    def test_boolean_configuration_accepts_common_explicit_values(self) -> None:
        for value in ("true", "TRUE", "1", "yes", "on"):
            with self.subTest(value=value):
                config = load_api_client_config({USE_MOCK_API_ENV: value})
                self.assertTrue(config.use_mock_api)

    def test_invalid_mode_value_is_a_safe_configuration_error(self) -> None:
        with self.assertRaises(PredictionServiceError) as raised:
            load_api_client_config({USE_MOCK_API_ENV: "sometimes"})

        self.assertEqual(raised.exception.category, "configuration")
        self.assertFalse(raised.exception.retryable)

    def test_real_mode_requires_url_and_both_timeouts(self) -> None:
        incomplete_configurations = (
            {USE_MOCK_API_ENV: "false"},
            {
                USE_MOCK_API_ENV: "false",
                API_BASE_URL_ENV: "http://backend.test:8000",
            },
            {
                USE_MOCK_API_ENV: "false",
                API_BASE_URL_ENV: "http://backend.test:8000",
                CONNECT_TIMEOUT_ENV: "1",
            },
        )

        for environment in incomplete_configurations:
            with self.subTest(environment=environment):
                with self.assertRaises(PredictionServiceError) as raised:
                    load_api_client_config(environment)
                self.assertEqual(raised.exception.category, "configuration")

    def test_real_mode_rejects_invalid_or_credentialed_urls(self) -> None:
        for url in (
            "backend.test:8000",
            "ftp://backend.test",
            "http://user:password@backend.test:8000",
            "http://backend.test:8000?token=secret",
        ):
            with self.subTest(url=url):
                environment = real_api_environment()
                environment[API_BASE_URL_ENV] = url
                with self.assertRaises(PredictionServiceError) as raised:
                    load_api_client_config(environment)
                self.assertEqual(raised.exception.category, "configuration")

    def test_real_mode_rejects_non_positive_or_non_finite_timeouts(self) -> None:
        for value in ("0", "-1", "nan", "inf", "not-a-number"):
            with self.subTest(value=value):
                environment = real_api_environment()
                environment[CONNECT_TIMEOUT_ENV] = value
                with self.assertRaises(PredictionServiceError) as raised:
                    load_api_client_config(environment)
                self.assertEqual(raised.exception.category, "configuration")


class RealAPIAdapterTests(unittest.TestCase):
    def test_real_mode_posts_one_original_image_and_normalizes_response(self) -> None:
        image = validated_test_image()
        fake_response = Mock(status_code=200)
        fake_response.json.return_value = valid_prediction_response()

        with patch.dict(os.environ, real_api_environment(), clear=True):
            with patch(
                "services.api_client.requests.post",
                return_value=fake_response,
            ) as post:
                response = predict_image(image)

        post.assert_called_once_with(
            "http://backend.test:8000/predict",
            files={"file": (image.filename, image.data, image.media_type)},
            headers={"Accept": "application/json"},
            timeout=(1.25, 8.5),
        )
        self.assertEqual(response, valid_prediction_response())

    def test_connection_refused_and_timeout_are_normalized(self) -> None:
        cases = (
            (
                requests.exceptions.ConnectionError("connection refused"),
                "connection",
                "could not be reached",
            ),
            (
                requests.exceptions.Timeout("request timed out"),
                "timeout",
                "did not complete in time",
            ),
        )

        for exception, category, message in cases:
            with self.subTest(category=category):
                with patch.dict(os.environ, real_api_environment(), clear=True):
                    with patch(
                        "services.api_client.requests.post",
                        side_effect=exception,
                    ):
                        with self.assertRaises(PredictionServiceError) as raised:
                            predict_image(validated_test_image())
                self.assertEqual(raised.exception.category, category)
                self.assertIn(message, str(raised.exception))

    def test_documented_http_errors_have_safe_messages(self) -> None:
        cases = {
            400: "could not process this image",
            415: "Unsupported image format",
            422: "could not validate this image",
            500: "internal error",
            503: "temporarily unavailable",
        }

        for status_code, message in cases.items():
            with self.subTest(status_code=status_code):
                fake_response = Mock(status_code=status_code)
                with patch.dict(os.environ, real_api_environment(), clear=True):
                    with patch(
                        "services.api_client.requests.post",
                        return_value=fake_response,
                    ):
                        with self.assertRaises(PredictionServiceError) as raised:
                            predict_image(validated_test_image())
                self.assertIn(message, str(raised.exception))
                fake_response.json.assert_not_called()

    def test_malformed_json_is_not_presented_as_prediction(self) -> None:
        fake_response = Mock(status_code=200)
        fake_response.json.side_effect = ValueError("invalid JSON")

        with patch.dict(os.environ, real_api_environment(), clear=True):
            with patch(
                "services.api_client.requests.post",
                return_value=fake_response,
            ):
                with self.assertRaises(PredictionServiceError) as raised:
                    predict_image(validated_test_image())

        self.assertEqual(raised.exception.category, "invalid_response")
        self.assertIn("malformed JSON", str(raised.exception))

    def test_missing_response_fields_are_rejected_after_http_success(self) -> None:
        incomplete_response = valid_prediction_response()
        del incomplete_response["prediction"]["recommendation"]
        fake_response = Mock(status_code=200)
        fake_response.json.return_value = incomplete_response

        with patch.dict(os.environ, real_api_environment(), clear=True):
            with patch(
                "services.api_client.requests.post",
                return_value=fake_response,
            ):
                with self.assertRaisesRegex(PredictionServiceError, "incomplete"):
                    predict_image(validated_test_image())

    def test_real_mode_failure_never_falls_back_to_mock_data(self) -> None:
        with patch.dict(os.environ, real_api_environment(), clear=True):
            with patch(
                "services.api_client.requests.post",
                side_effect=requests.exceptions.ConnectionError,
            ):
                with patch(
                    "services.api_client._load_mock_response"
                ) as load_mock_response:
                    with self.assertRaises(PredictionServiceError):
                        predict_image(validated_test_image())

        load_mock_response.assert_not_called()


if __name__ == "__main__":
    unittest.main()
