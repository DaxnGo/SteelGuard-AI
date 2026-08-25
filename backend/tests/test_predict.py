import pytest

from app.schemas.prediction import DefectClass, Recommendation
from app.routes import predict as predict_route
from app.services import prediction_service
from app.services import ai_service


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


def test_predict_rejects_second_image_under_another_field(client, valid_jpeg_bytes):
    response = client.post(
        "/predict",
        files=[
            ("file", ("sample1.jpg", valid_jpeg_bytes, "image/jpeg")),
            ("other", ("sample2.jpg", valid_jpeg_bytes, "image/jpeg")),
        ],
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MULTIPLE_FILES_NOT_ALLOWED"


def test_predict_rejects_extra_multipart_field(client, valid_jpeg_bytes):
    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
        data={"note": "extra field"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "MULTIPLE_FILES_NOT_ALLOWED"


def test_predict_openapi_documents_single_multipart_upload(client):
    operation = client.get("/openapi.json").json()["paths"]["/predict"]["post"]

    request_body = operation["requestBody"]
    assert "multipart/form-data" in request_body["content"]
    for status in ("400", "413", "415", "422", "500", "503"):
        assert status in operation["responses"]


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


def test_ai_service_defaults_to_dummy_mode(monkeypatch):
    monkeypatch.delenv("STEELGUARD_AI_MODE", raising=False)

    result = ai_service.run_inference(object())

    assert result["class_name"] == DefectClass.SCRATCHES
    assert result["gradcam_image"] is None


def test_ai_service_model_mode_never_falls_back_to_dummy(monkeypatch):
    expected = _dummy_adapter_output(
        class_name=DefectClass.CRAZING,
        confidence=0.73,
        gradcam_image="data:image/png;base64,AAAA",
    )
    monkeypatch.setenv("STEELGUARD_AI_MODE", "model")
    monkeypatch.setattr(ai_service, "_run_model_inference", lambda image: expected)

    assert ai_service.run_inference(object()) == expected


def test_ai_service_rejects_unknown_mode(monkeypatch):
    monkeypatch.setenv("STEELGUARD_AI_MODE", "automatic")

    with pytest.raises(ValueError, match="STEELGUARD_AI_MODE"):
        ai_service.run_inference(object())


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
    assert calls[0].mode == "RGB"


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


def test_predict_with_empty_gradcam_image_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(gradcam_image=""),
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


def test_predict_keeps_gradcam_transport_neutral_until_d05(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    gradcam_reference = "/gradcam/example.png"
    monkeypatch.setattr(
        prediction_service,
        "run_inference",
        lambda image: _dummy_adapter_output(gradcam_image=gradcam_reference),
    )

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["prediction"]["gradcam_image"] == gradcam_reference


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


def test_predict_when_ai_adapter_raises_returns_sanitized_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    def boom(image):
        raise RuntimeError("model backend unreachable at /srv/models/steel.pt")

    monkeypatch.setattr(prediction_service, "run_inference", boom)

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    body = response.json()
    assert body == {
        "success": False,
        "error": {
            "code": "INFERENCE_FAILED",
            "message": "The image could not be analyzed at this time. Please try again.",
        },
    }
    assert "prediction" not in body
    assert "/srv/models" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text


def test_predict_with_non_mapping_adapter_output_returns_503(
    client,
    monkeypatch,
    valid_jpeg_bytes,
):
    monkeypatch.setattr(prediction_service, "run_inference", lambda image: None)

    response = client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INFERENCE_FAILED"


def test_predict_unexpected_backend_error_returns_sanitized_500(
    lenient_client,
    monkeypatch,
    valid_jpeg_bytes,
):
    def boom(file, content):
        raise RuntimeError("database unavailable at /srv/private/data")

    monkeypatch.setattr(predict_route, "predict_image", boom)

    response = lenient_client.post(
        "/predict",
        files={"file": ("sample.jpg", valid_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "/srv/private" not in response.text
    assert "RuntimeError" not in response.text
