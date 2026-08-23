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


def test_predict_with_empty_file_returns_400(client):
    response = client.post(
        "/predict",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NO_FILE"


def test_predict_with_unsupported_file_type_returns_415(client):
    response = client.post(
        "/predict",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
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
