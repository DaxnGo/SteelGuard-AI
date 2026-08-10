"""Streamlit harness tests for the complete mock inspection workflow."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
import streamlit as st
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def make_png_bytes() -> bytes:
    image_bytes = BytesIO()
    Image.new("RGB", (64, 40), color=(105, 115, 125)).save(
        image_bytes,
        format="PNG",
    )
    return image_bytes.getvalue()


def markdown_contains(app: AppTest, text: str) -> bool:
    return any(text in element.value for element in app.markdown)


class FrontendWorkflowTests(unittest.TestCase):
    def create_app(self) -> AppTest:
        return AppTest.from_file(APP_PATH, default_timeout=15).run()

    def test_initial_page_is_single_image_mock_interface(self) -> None:
        app = self.create_app()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "SteelGuard AI")
        self.assertTrue(
            markdown_contains(app, "Intelligent Steel Surface Defect Detection")
        )
        self.assertTrue(markdown_contains(app, "MOCK AI MODE"))
        self.assertTrue(markdown_contains(app, "STEEL SURFACE INSPECTION"))
        self.assertTrue(markdown_contains(app, "Supported:"))
        self.assertTrue(markdown_contains(app, "One image per inspection"))
        self.assertEqual(len(app.file_uploader), 1)
        self.assertFalse(app.file_uploader[0].accept_multiple_files)
        self.assertEqual(len(app.button), 0)
        self.assertEqual(len(app.sidebar.radio), 0)
        self.assertEqual(len(app.sidebar.selectbox), 0)
        self.assertFalse(markdown_contains(app, "Frontend QA Matrix"))

    def test_prediction_source_label_changes_from_configuration_only(self) -> None:
        environment = {
            "STEELGUARD_USE_MOCK_API": "false",
            "STEELGUARD_API_BASE_URL": "http://backend.test:8000",
            "STEELGUARD_API_CONNECT_TIMEOUT_SECONDS": "1",
            "STEELGUARD_API_READ_TIMEOUT_SECONDS": "8",
        }
        with patch.dict(os.environ, environment, clear=True):
            app = self.create_app()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(markdown_contains(app, "LIVE API MODE"))
        self.assertFalse(markdown_contains(app, "MOCK AI MODE"))

    def test_complete_mock_inspection_and_reset(self) -> None:
        with patch.dict(os.environ, {"STEELGUARD_MOCK_DELAY_SECONDS": "0"}):
            app = self.create_app()
            app.file_uploader[0].upload(
                "steel-surface.png",
                make_png_bytes(),
                "image/png",
            ).run()

            self.assertEqual(len(app.exception), 0)
            self.assertEqual(
                app.session_state.filtered_state["inspection_state"],
                "IMAGE_SELECTED",
            )
            self.assertTrue(markdown_contains(app, "Ready for inspection"))
            self.assertIn("Analyze Surface", [button.label for button in app.button])

            next(
                button for button in app.button if button.label == "Analyze Surface"
            ).click().run()

            self.assertEqual(len(app.exception), 0)
            self.assertEqual(
                app.session_state.filtered_state["inspection_state"],
                "SUCCESS",
            )
            self.assertTrue(markdown_contains(app, "INSPECTION RESULT"))
            self.assertTrue(markdown_contains(app, "Scratches"))
            self.assertTrue(markdown_contains(app, "94.2%"))
            self.assertTrue(markdown_contains(app, "REWORK"))

            markdown_values = [element.value for element in app.markdown]
            recommendation_index = next(
                index
                for index, value in enumerate(markdown_values)
                if "Quality Recommendation" in value
            )
            defect_index = next(
                index
                for index, value in enumerate(markdown_values)
                if "Detected Defect" in value
            )
            confidence_index = next(
                index
                for index, value in enumerate(markdown_values)
                if "Confidence" in value
            )
            self.assertLess(recommendation_index, defect_index)
            self.assertLess(defect_index, confidence_index)

            self.assertTrue(markdown_contains(app, "AI EXPLANATION"))
            self.assertTrue(markdown_contains(app, "AI Attention Map"))
            self.assertTrue(
                markdown_contains(app, "Grad-CAM visualization will appear here")
            )
            self.assertTrue(
                any(
                    "Highlighted regions indicate areas that contributed"
                    in element.value
                    for element in app.caption
                )
            )

            next(
                button
                for button in app.button
                if button.label == "Analyze Another Image"
            ).click().run()

            self.assertEqual(len(app.exception), 0)
            state = app.session_state.filtered_state
            self.assertEqual(state["inspection_state"], "EMPTY")
            self.assertIsNone(state["selected_image"])
            self.assertIsNone(state["selected_signature"])
            self.assertIsNone(state["prediction"])
            self.assertIsNone(state["inspection_error"])
            self.assertEqual(len(app.file_uploader), 1)
            self.assertFalse(markdown_contains(app, "INSPECTION RESULT"))
            self.assertEqual(len(app.button), 0)

    def test_corrupt_image_shows_friendly_error(self) -> None:
        app = self.create_app()
        app.file_uploader[0].upload(
            "corrupt.png",
            b"not-an-image",
            "image/png",
        ).run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.error[0].value, "Inspection failed.")
        self.assertEqual(
            app.session_state.filtered_state["inspection_state"],
            "ERROR",
        )
        self.assertIsNone(app.session_state.filtered_state["selected_image"])
        self.assertIn("Try Again", [button.label for button in app.button])
        self.assertEqual(len([b for b in app.button if b.label == "Analyze Surface"]), 0)

    def test_mock_service_failure_preserves_valid_selection_for_retry(self) -> None:
        environment = {
            "STEELGUARD_MOCK_DELAY_SECONDS": "0",
            "STEELGUARD_MOCK_RESPONSE_PATH": "missing/mock-response.json",
        }
        with patch.dict(os.environ, environment, clear=False):
            app = self.create_app()
            app.file_uploader[0].upload(
                "steel-surface.png",
                make_png_bytes(),
                "image/png",
            ).run()
            next(
                button for button in app.button if button.label == "Analyze Surface"
            ).click().run()

            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.error[0].value, "Inspection failed.")
            state = app.session_state.filtered_state
            self.assertEqual(state["inspection_state"], "ERROR")
            self.assertIsNotNone(state["selected_image"])
            self.assertIsNone(state["prediction"])
            labels = [button.label for button in app.button]
            self.assertIn("Try Again", labels)
            self.assertIn("Choose Another Image", labels)
            self.assertTrue(markdown_contains(app, "Ready for inspection"))

    def test_analysis_enters_analyzing_before_calling_service(self) -> None:
        observed_states: list[str] = []

        def fake_prediction(_image):
            observed_states.append(st.session_state["inspection_state"])
            return {
                "success": True,
                "prediction": {
                    "class_name": "Scratches",
                    "confidence": 0.942,
                    "recommendation": "REWORK",
                    "gradcam_image": "mock_gradcam.png",
                },
            }

        app = self.create_app()
        app.file_uploader[0].upload(
            "steel-surface.png",
            make_png_bytes(),
            "image/png",
        ).run()

        with patch("services.api_client.predict_image", side_effect=fake_prediction):
            next(
                button for button in app.button if button.label == "Analyze Surface"
            ).click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(observed_states, ["ANALYZING"])
        self.assertEqual(
            app.session_state.filtered_state["inspection_state"],
            "SUCCESS",
        )

    def test_valid_replacement_clears_prior_upload_error_and_can_be_removed(self) -> None:
        app = self.create_app()
        app.file_uploader[0].upload(
            "corrupt.png",
            b"not-an-image",
            "image/png",
        ).run()

        self.assertEqual(
            app.session_state.filtered_state["inspection_state"],
            "ERROR",
        )

        app.file_uploader[0].upload(
            "replacement.png",
            make_png_bytes(),
            "image/png",
        ).run()

        state = app.session_state.filtered_state
        self.assertEqual(state["inspection_state"], "IMAGE_SELECTED")
        self.assertIsNone(state["inspection_error"])
        self.assertIsNone(state["prediction"])
        self.assertEqual(state["selected_image"].filename, "replacement.png")

        app.file_uploader[0].clear().run()
        state = app.session_state.filtered_state
        self.assertEqual(state["inspection_state"], "EMPTY")
        self.assertIsNone(state["selected_image"])
        self.assertIsNone(state["selected_signature"])
        self.assertIsNone(state["prediction"])
        self.assertIsNone(state["inspection_error"])


if __name__ == "__main__":
    unittest.main()
