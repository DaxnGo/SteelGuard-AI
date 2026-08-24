from app.schemas.prediction import DefectClass, Recommendation
from app.services import prediction_service


def test_predict_with_valid_jpeg_returns_dummy_prediction(client, valid_jpeg_bytes):
    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "success": True,
        "prediction": {
            "class_name": "Scratches",
            "confidence": 0.942,
            "recommendation": "REWORK",
            "gradcam_image": None,
        },
    }


def test_predict_with_valid_png_returns_dummy_prediction(client, valid_png_bytes):
    response = client.post(
        "/predict",
        files={"file": ("sample.png", valid_png_bytes, "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "success": True,
        "prediction": {
            "class_name": "Scratches",
            "confidence": 0.942,
            "recommendation": "REWORK",
            "gradcam_image": None,
        },
    }


def test_predict_without_file_returns_400(client):
    response = client.post("/predict")

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NO_FILE"


def test_predict_with_empty_file_returns_422(client):
    response = client.post(
        "/predict",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_predict_with_duplicate_file_fields_returns_400(client, valid_jpeg_bytes):
    response = client.post(
        "/predict",
        files=[
            ("file", ("sample1.jpg", valid_jpeg_bytes, "image/jpeg")),
            ("file", ("sample2.jpg", valid_jpeg_bytes, "image/jpeg")),
        ],
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MULTIPLE_FILES_NOT_ALLOWED"


def test_predict_with_unsupported_file_type_returns_415(client):
    response = client.post(
        "/predict",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_predict_with_extension_content_mismatch_returns_415(
    client,
    valid_png_bytes,
):
    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_png_bytes, "image/jpeg")},
    )

    assert response.status_code == 415
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_predict_with_corrupted_image_returns_422(client):
    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", b"corrupted-bytes-not-a-real-image", "image/jpeg")},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_IMAGE"


def test_predict_rejects_image_above_configured_upload_limit(
    client,
    monkeypatch,
    valid_png_bytes,
):
    monkeypatch.setenv("STEELGUARD_MAX_UPLOAD_BYTES", str(len(valid_png_bytes) - 1))

    response = client.post(
        "/predict",
        files={"file": ("sample.png", valid_png_bytes, "image/png")},
    )

    assert response.status_code == 413
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FILE_TOO_LARGE"


def test_predict_returns_safe_error_for_invalid_upload_limit(
    client,
    monkeypatch,
    valid_png_bytes,
):
    monkeypatch.setenv("STEELGUARD_MAX_UPLOAD_BYTES", "invalid")

    response = client.post(
        "/predict",
        files={"file": ("sample.png", valid_png_bytes, "image/png")},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"


def _dummy_adapter_output(**overrides) -> dict:
    result = {
        "class_name": DefectClass.SCRATCHES,
        "confidence": 0.5,
        "recommendation": Recommendation.ACCEPT,
        "gradcam_image": None,
    }
    result.update(overrides)
    return result


def test_ai_adapter_invoked_exactly_once_for_valid_request(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    calls = []
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: calls.append(image) or _dummy_adapter_output(),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    assert len(calls) == 1


def test_ai_adapter_not_invoked_when_no_file(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: calls.append(image),
    )

    response = client.post("/predict")

    assert response.status_code == 400
    assert calls == []


def test_ai_adapter_not_invoked_for_unsupported_file_type(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: calls.append(image),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert calls == []


def test_ai_adapter_not_invoked_for_corrupted_image(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: calls.append(image),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", b"corrupted-bytes-not-a-real-image", "image/jpeg")},
    )

    assert response.status_code == 422
    assert calls == []


def test_ai_adapter_not_invoked_for_oversized_file(
    client,
    monkeypatch,
    valid_png_bytes,
):
    monkeypatch.setenv("STEELGUARD_MAX_UPLOAD_BYTES", str(len(valid_png_bytes) - 1))
    calls = []
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: calls.append(image),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.png", valid_png_bytes, "image/png")},
    )

    assert response.status_code == 413
    assert calls == []


def test_predict_with_unmapped_class_name_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(class_name="Unknown Defect"),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_nan_confidence_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(confidence=float("nan")),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_out_of_range_confidence_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(confidence=1.5),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_negative_confidence_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(confidence=-0.1),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_invalid_recommendation_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(recommendation="MAYBE"),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_invalid_gradcam_image_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(gradcam_image="not-valid-base64!!"),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_with_incomplete_adapter_output_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: {"class_name": DefectClass.SCRATCHES, "confidence": 0.5},
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INFERENCE_FAILED"
    assert "prediction" not in body


def test_predict_when_ai_adapter_raises_unexpected_error_returns_sanitized_500(
    lenient_client,
    monkeypatch,
    valid_jpeg_bytes,
):
    def boom(image):
        raise RuntimeError("model backend unreachable at /srv/models/steel.pt")

    monkeypatch.setattr(prediction_service, "run_inference", boom)

    response = lenient_client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred. Please try again.",
        },
    }
    assert "prediction" not in body
    assert "/srv/models" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
