from app.schemas.prediction import DefectClass, Recommendation


def run_inference(image_bytes: bytes) -> dict:
    return {
        "class_name": DefectClass.SCRATCHES,
        "confidence": 0.942,
        "recommendation": Recommendation.REWORK,
        "gradcam_image": None,
    }
