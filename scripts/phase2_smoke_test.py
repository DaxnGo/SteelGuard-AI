"""Verify the real frontend client against the Phase 2 dummy backend."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import urlopen

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIRECTORY = REPOSITORY_ROOT / "frontend"
HEALTH_TIMEOUT_SECONDS = 10.0


def _free_port() -> int:
    with socket.socket() as connection:
        connection.bind(("127.0.0.1", 0))
        return int(connection.getsockname()[1])


def _wait_for_health(process: subprocess.Popen[bytes], url: str) -> None:
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"The dummy backend exited before becoming healthy (code {process.returncode})."
            )
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.1)
    raise RuntimeError("The dummy backend did not become healthy in time.")


def _image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(120, 120, 120)).save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "backend",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_health(process, f"{base_url}/health")
        sys.path.insert(0, str(FRONTEND_DIRECTORY))
        from services.api_client import predict_image
        from utils.image_validator import validate_image_bytes

        image = validate_image_bytes("phase2-smoke.png", _image_bytes())
        environment = {
            "STEELGUARD_USE_MOCK_API": "false",
            "STEELGUARD_API_BASE_URL": base_url,
            # Temporary smoke-test values; final D-04 values remain a team decision.
            "STEELGUARD_API_CONNECT_TIMEOUT_SECONDS": "2",
            "STEELGUARD_API_READ_TIMEOUT_SECONDS": "10",
        }
        with patch.dict(os.environ, environment, clear=True):
            response = predict_image(image)

        prediction = response["prediction"]
        expected = {
            "class_name": "Scratches",
            "confidence": 0.942,
            "recommendation": "REWORK",
            "gradcam_image": None,
        }
        if response.get("success") is not True or prediction != expected:
            raise AssertionError(f"Unexpected dummy prediction: {response!r}")
        print("Phase 2 smoke test passed: Streamlit client -> FastAPI dummy /predict")
        print(f"Validated response: {response}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
