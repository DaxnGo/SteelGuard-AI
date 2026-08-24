from PIL.Image import Image as PILImage

from app.schemas.prediction import DefectClass, Recommendation


def run_inference(image: PILImage) -> dict:
    return {
        "class_name": DefectClass.SCRATCHES,
        "confidence": 0.942,
        "recommendation": Recommendation.REWORK,
        "gradcam_image": None,
    }
