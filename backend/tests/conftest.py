from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_image_bytes(fmt: str) -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (32, 32), color=(120, 120, 120))
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    return _make_image_bytes("JPEG")


@pytest.fixture
def valid_png_bytes() -> bytes:
    return _make_image_bytes("PNG")
