# SteelGuard AI — API Contract

This document is the shared reference between Frontend, Backend, and AI teams. Any change to this contract must be reflected here before implementation changes are considered final.

Base URL (local development): `http://localhost:8000`

---

## 1. GET /health

Used to verify that the backend is running.

**Request**

No parameters, no body.

**Success Response**

HTTP 200 OK

```json
{
  "status": "ok"
}
```

---

## 2. POST /predict

Accepts a single steel surface image and returns a defect prediction.

**Request**

- Content-Type: `multipart/form-data`
- Field name: `file`
- Exactly one image per request

Example (curl):

```
curl -X POST http://localhost:8000/predict \
  -F "file=@steel_surface.jpg"
```

**Supported Image Types**

Content-Type:

- `image/jpeg`
- `image/png`

Extension:

- `.jpg`
- `.jpeg`
- `.png`

Any other file type is rejected. The file must also be successfully opened and verified as an image (Pillow); extension/MIME type alone is not sufficient.

---

## 3. Success Response

HTTP 200 OK

```json
{
  "success": true,
  "prediction": {
    "class_name": "Scratches",
    "confidence": 0.942,
    "recommendation": "REWORK",
    "gradcam_image": null
  }
}
```

Field definitions:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | Always `true` on success |
| `prediction.class_name` | string (enum) | Predicted defect class |
| `prediction.confidence` | float | Model confidence score |
| `prediction.recommendation` | string (enum) | Quality recommendation |
| `prediction.gradcam_image` | string \| null | Grad-CAM visualization |

---

## 4. Defect Classes

`class_name` must be exactly one of the following values:

- `Crazing`
- `Inclusion`
- `Patches`
- `Pitted Surface`
- `Rolled-in Scale`
- `Scratches`

No other value is permitted.

---

## 5. Confidence Format

`confidence` is a decimal in the range:

```
0.0 <= confidence <= 1.0
```

Correct: `0.942`
Incorrect: `94.2`

Percentage conversion, if needed, is performed by the frontend.

---

## 6. Recommendation Values

`recommendation` must be exactly one of the following values:

- `ACCEPT`
- `REWORK`
- `REJECT`

No other value, casing, or synonym is permitted.

Recommendation logic (the rule that maps model output to one of these three values) is not yet finalized. During Phase 1, the dummy `/predict` endpoint always returns `REWORK` for integration testing purposes only.

---

## 7. Grad-CAM Format

Field: `gradcam_image`

During Phase 1 (dummy prediction):

```json
"gradcam_image": null
```

Final format after AI integration (D-05 remains open):

```json
"gradcam_image": "data:image/png;base64,<base64-encoded-png>"
```

During Phase 1, `gradcam_image` is `null`. The final live representation and
its lifecycle remain subject to D-05; the frontend already preserves the field
and renders the dummy placeholder without generating a heatmap.

---

## 8. Error Response

All error responses share a single consistent structure.

```json
{
  "success": false,
  "error": {
    "code": "INVALID_IMAGE",
    "message": "The uploaded file could not be processed as an image."
  }
}
```

| Field | Type | Description |
|---|---|---|
| `success` | boolean | Always `false` on error |
| `error.code` | string | Machine-readable error code |
| `error.message` | string | Human-readable error message |

---

## 9. Error Codes and HTTP Status Codes

| Code | HTTP Status | Meaning |
|---|---|---|
| `NO_FILE` | 400 | No file was included in the request |
| `FILE_TOO_LARGE` | 413 | File exceeds the configured D-04 upload-size limit |
| `UNSUPPORTED_FILE_TYPE` | 415 | File is not JPEG or PNG |
| `INVALID_IMAGE` | 422 | File has an image extension/MIME type but cannot be processed as an image |
| `INFERENCE_FAILED` | 500 | AI received the image but inference failed |
| `MODEL_UNAVAILABLE` | 503 | Model is not loaded or unavailable |
| `INTERNAL_ERROR` | 500 | Unexpected backend error |

---

## 10. Contract Stability

This contract must remain unchanged when the dummy AI implementation is replaced with the real AI model. The frontend must not require refactoring due to AI integration. Any intentional contract change must be updated in this document first.
