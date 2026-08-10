"""Contract and UI coverage for the development-only response matrix."""

from __future__ import annotations

from itertools import product
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

from services.api_client import PredictionServiceError, validate_prediction_response
from tests.scenario_matrix import (
    CONFIDENCE_VALUES,
    DEFECT_CLASSES,
    INVALID_SCENARIOS,
    RECOMMENDATIONS,
    VALID_SCENARIOS,
)


HARNESS_PATH = Path(__file__).resolve().parent / "ui_matrix_app.py"


def markdown_contains(app: AppTest, text: str) -> bool:
    """Return whether any rendered Markdown block contains text."""

    return any(text in element.value for element in app.markdown)


class ResponseMatrixContractTests(unittest.TestCase):
    def test_valid_matrix_is_the_complete_cartesian_product(self) -> None:
        expected_combinations = set(
            product(DEFECT_CLASSES, RECOMMENDATIONS, CONFIDENCE_VALUES)
        )
        actual_combinations = {
            (
                scenario.response["prediction"]["class_name"],
                scenario.response["prediction"]["recommendation"],
                scenario.response["prediction"]["confidence"],
            )
            for scenario in VALID_SCENARIOS
        }

        self.assertEqual(len(VALID_SCENARIOS), 90)
        self.assertEqual(actual_combinations, expected_combinations)

    def test_every_valid_response_is_preserved_by_validation(self) -> None:
        for scenario in VALID_SCENARIOS:
            with self.subTest(case_id=scenario.case_id):
                original_prediction = scenario.response["prediction"]
                normalized = validate_prediction_response(scenario.response)
                normalized_prediction = normalized["prediction"]

                self.assertEqual(
                    normalized_prediction["class_name"],
                    original_prediction["class_name"],
                )
                self.assertEqual(
                    normalized_prediction["confidence"],
                    original_prediction["confidence"],
                )
                self.assertEqual(
                    normalized_prediction["recommendation"],
                    original_prediction["recommendation"],
                )

    def test_every_invalid_response_has_the_expected_safe_error(self) -> None:
        for scenario in INVALID_SCENARIOS:
            if scenario.service_error is not None:
                continue
            with self.subTest(case_id=scenario.case_id):
                with self.assertRaises(PredictionServiceError) as raised:
                    validate_prediction_response(scenario.response)
                self.assertEqual(str(raised.exception), scenario.expected_result)


class ResponseMatrixUITests(unittest.TestCase):
    def create_harness(self) -> AppTest:
        return AppTest.from_file(HARNESS_PATH, default_timeout=15).run()

    def test_all_valid_combinations_render_exact_backend_values(self) -> None:
        app = self.create_harness()

        for scenario in VALID_SCENARIOS:
            with self.subTest(case_id=scenario.case_id):
                app.sidebar.selectbox[0].set_value(scenario.case_id).run()
                prediction = scenario.response["prediction"]
                confidence_text = f'{prediction["confidence"] * 100:.1f}%'

                self.assertEqual(len(app.exception), 0)
                self.assertEqual(
                    app.session_state.filtered_state["inspection_state"],
                    "SUCCESS",
                )
                self.assertTrue(
                    markdown_contains(app, prediction["class_name"]),
                )
                self.assertTrue(markdown_contains(app, confidence_text))
                self.assertTrue(
                    markdown_contains(app, prediction["recommendation"]),
                )

    def test_all_invalid_and_service_scenarios_render_error_state(self) -> None:
        app = self.create_harness()
        app.sidebar.radio[0].set_value("Invalid and error responses").run()

        for scenario in INVALID_SCENARIOS:
            with self.subTest(case_id=scenario.case_id):
                app.sidebar.selectbox[0].set_value(scenario.case_id).run()

                self.assertEqual(len(app.exception), 0)
                self.assertEqual(
                    app.session_state.filtered_state["inspection_state"],
                    "ERROR",
                )
                self.assertEqual(app.error[0].value, "Inspection failed.")
                self.assertTrue(markdown_contains(app, scenario.expected_result))
                self.assertFalse(markdown_contains(app, "INSPECTION RESULT"))


if __name__ == "__main__":
    unittest.main()
