"""Exercise live HTTP failures through the production Streamlit workflow."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def make_png_bytes() -> bytes:
    image_bytes = BytesIO()
    Image.new("RGB", (32, 32), color=(105, 115, 125)).save(
        image_bytes,
        format="PNG",
    )
    return image_bytes.getvalue()


def markdown_contains(app: AppTest, text: str) -> bool:
    return any(text in element.value for element in app.markdown)


class FaultResponseHandler(BaseHTTPRequestHandler):
    response_status = 500
    response_body = b'{"success":false}'
    response_content_type = "application/json"
    response_delay_seconds = 0.0

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(content_length)
        status = type(self).response_status
        body = type(self).response_body
        content_type = type(self).response_content_type
        delay_seconds = type(self).response_delay_seconds
        if delay_seconds:
            time.sleep(delay_seconds)

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            pass

    def log_message(self, _format: str, *_args: object) -> None:
        pass


class LiveHTTPErrorUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FaultResponseHandler)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)

    def run_failure(
        self,
        *,
        status: int,
        expected_message: str,
        retryable: bool,
        body: bytes = b'{"success":false}',
        content_type: str = "application/json",
        delay_seconds: float = 0.0,
        read_timeout: str = "2",
    ) -> None:
        FaultResponseHandler.response_status = status
        FaultResponseHandler.response_body = body
        FaultResponseHandler.response_content_type = content_type
        FaultResponseHandler.response_delay_seconds = delay_seconds
        environment = {
            "STEELGUARD_USE_MOCK_API": "false",
            "STEELGUARD_API_BASE_URL": self.base_url,
            "STEELGUARD_API_CONNECT_TIMEOUT_SECONDS": "1",
            "STEELGUARD_API_READ_TIMEOUT_SECONDS": read_timeout,
            "STEELGUARD_MAX_UPLOAD_BYTES": str(1024 * 1024),
        }

        with patch.dict(os.environ, environment, clear=False):
            app = AppTest.from_file(APP_PATH, default_timeout=15).run()
            app.file_uploader[0].upload(
                "steel-surface.png",
                make_png_bytes(),
                "image/png",
            ).run()
            next(
                button for button in app.button if button.label == "Analyze Surface"
            ).click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            app.session_state.filtered_state["inspection_state"],
            "ERROR",
        )
        self.assertEqual(app.error[0].value, "Inspection failed.")
        self.assertTrue(markdown_contains(app, expected_message))
        self.assertEqual(len(app.info), 1)
        labels = [button.label for button in app.button]
        self.assertEqual("Try Again" in labels, retryable)
        self.assertIn("Choose Another Image", labels)
        if retryable:
            self.assertIn("service is available", app.info[0].value)
        else:
            self.assertIn("upload requirements", app.info[0].value)
        self.assertFalse(markdown_contains(app, "INSPECTION RESULT"))

    def test_live_http_status_errors_render_safe_recovery(self) -> None:
        cases = (
            (400, "could not process this image", False),
            (413, "larger than the service allows", False),
            (415, "Unsupported image format", False),
            (422, "could not validate this image", False),
            (500, "internal error", True),
            (503, "temporarily unavailable", True),
        )

        for status, message, retryable in cases:
            with self.subTest(status=status):
                self.run_failure(
                    status=status,
                    expected_message=message,
                    retryable=retryable,
                )

    def test_live_timeout_preserves_image_for_deliberate_retry(self) -> None:
        self.run_failure(
            status=200,
            expected_message="did not complete in time",
            retryable=True,
            delay_seconds=0.2,
            read_timeout="0.05",
        )

    def test_live_malformed_json_never_renders_a_prediction(self) -> None:
        self.run_failure(
            status=200,
            expected_message="malformed JSON",
            retryable=True,
            body=b"not-json",
            content_type="text/plain",
        )

    def test_live_contract_invalid_json_never_renders_a_prediction(self) -> None:
        self.run_failure(
            status=200,
            expected_message="incomplete",
            retryable=True,
            body=json.dumps(
                {
                    "success": True,
                    "prediction": {
                        "class_name": "Scratches",
                        "confidence": 0.942,
                    },
                }
            ).encode("utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
