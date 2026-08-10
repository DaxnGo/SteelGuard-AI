# API Contract

## Overview

The preliminary MVP exposes one versioned inference operation. The contract is
defined before backend implementation so frontend and backend work can proceed
independently.

```text
POST /api/v1/predict
```

## Request

- Content type: `multipart/form-data`
- Required field: `image`
- Cardinality: exactly one file
- Supported media types: `image/jpeg` and `image/png`

Example:

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "accept: application/json" \
  -F "image=@steel-surface.jpg;type=image/jpeg"
```

The backend must inspect the decoded content rather than trusting only the file
extension or client-supplied media type. A maximum file size is not fixed in
the foundation contract; if one is added during integration, the same limit and
message must be documented and applied consistently by frontend and backend.

## Success response

- Status: `200 OK`
- Content type: `application/json`

```json
{
  "success": true,
  "prediction": {
    "class_name": "Scratches",
    "confidence": 0.942,
    "recommendation": "REWORK",
    "gradcam_image": "mock_gradcam.png"
  }
}
```

| Field | Type | Constraint |
| --- | --- | --- |
| `success` | boolean | Always `true` for a `200` prediction response |
| `prediction.class_name` | string | One exact supported class label |
| `prediction.confidence` | number | Finite value from `0.0` through `1.0` |
| `prediction.recommendation` | string | `ACCEPT`, `REWORK`, or `REJECT` |
| `prediction.gradcam_image` | string | Non-empty backend resource reference |

Supported `class_name` values:

- `Crazing`
- `Inclusion`
- `Patches`
- `Pitted Surface`
- `Rolled-in Scale`
- `Scratches`

`gradcam_image` is opaque to presentation components. An absolute URL is used
directly; a relative reference is resolved against the configured backend base
URL. The backend is responsible for ensuring that the resolved resource is
browser-retrievable. The mock filename is illustrative and does not imply that
the foundation contains a generated heatmap file.

## Error responses

Errors use FastAPI's standard JSON detail shape:

```json
{
  "detail": "A concise, user-safe explanation of the failure."
}
```

| Status | Situation |
| --- | --- |
| `400 Bad Request` | Repeated image field, corrupt image, or otherwise invalid request content |
| `415 Unsupported Media Type` | File is not a supported JPEG or PNG image |
| `422 Unprocessable Entity` | Required `image` field is missing or malformed |
| `500 Internal Server Error` | Inference or Grad-CAM generation failed |
| `503 Service Unavailable` | Model or required AI artifact is unavailable |

Error responses do not include a fake prediction and do not need a
`success: false` wrapper. The frontend must handle non-success status codes,
timeouts, connection failures, invalid JSON, and contract-invalid success
responses as recoverable errors.

## Ownership rules

- The frontend supplies the file and displays the response.
- The backend owns HTTP validation, adapter orchestration, response validation,
  serialization, and Grad-CAM resource delivery.
- The AI adapter supplies `class_name`, `confidence`, `recommendation`, and the
  Grad-CAM artifact.
- No frontend threshold, lookup table, or fallback may replace any prediction
  field.

## Compatibility policy

Breaking field, enum, path, or semantic changes require a new API version.
Backward-compatible clarifications must update this document, the mock fixture,
and integration tests together.
