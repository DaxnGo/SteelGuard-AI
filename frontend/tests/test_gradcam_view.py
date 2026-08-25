import base64
from io import BytesIO
import unittest

from PIL import Image

from components.gradcam_view import decode_gradcam_data_uri


def png_data_uri() -> str:
    buffer = BytesIO()
    Image.new("RGB", (4, 3), color=(100, 20, 30)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


class GradcamViewTests(unittest.TestCase):
    def test_decodes_valid_png_data_uri(self) -> None:
        decoded = decode_gradcam_data_uri(png_data_uri())

        self.assertIsNotNone(decoded)
        with Image.open(BytesIO(decoded)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (4, 3))

    def test_rejects_invalid_or_non_png_data_uri(self) -> None:
        self.assertIsNone(decode_gradcam_data_uri("data:image/jpeg;base64,AAAA"))
        self.assertIsNone(decode_gradcam_data_uri("data:image/png;base64,not-base64"))
        self.assertIsNone(decode_gradcam_data_uri("mock_gradcam.png"))


if __name__ == "__main__":
    unittest.main()
