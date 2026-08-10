"""Streamlit harness tests for the complete mock inspection workflow."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from PIL import Image
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
        self.assertEqual(len(app.file_uploader), 1)
        self.assertFalse(app.file_uploader[0].accept_multiple_files)
        self.assertEqual(len(app.button), 0)

    def test_complete_mock_inspection_and_reset(self) -> None:
        with patch.dict(os.environ, {"STEELGUARD_MOCK_DELAY_SECONDS": "0"}):
            app = self.create_app()
            app.file_uploader[0].upload(
                "steel-surface.png",
                make_png_bytes(),
                "image/png",
            ).run()

            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.success[0].value, "Ready for inspection")
            self.assertIn("Analyze Surface", [button.label for button in app.button])

            next(
                button for button in app.button if button.label == "Analyze Surface"
            ).click().run()

            self.assertEqual(len(app.exception), 0)
            self.assertTrue(markdown_contains(app, "INSPECTION RESULT"))
            self.assertTrue(markdown_contains(app, "Scratches"))
            self.assertTrue(markdown_contains(app, "94.2%"))
            self.assertTrue(markdown_contains(app, "REWORK"))
            self.assertTrue(markdown_contains(app, "AI EXPLANATION"))
            self.assertTrue(
                markdown_contains(app, "Grad-CAM visualization will appear here")
            )

            next(
                button
                for button in app.button
                if button.label == "Analyze Another Image"
            ).click().run()

            self.assertEqual(len(app.exception), 0)
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
            labels = [button.label for button in app.button]
            self.assertIn("Try Again", labels)
            self.assertIn("Choose Another Image", labels)
            self.assertEqual(app.success[0].value, "Ready for inspection")


if __name__ == "__main__":
    unittest.main()
