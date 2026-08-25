# SteelGuard AI Frontend API Integration Readiness

> **Compose default mode:** Live frontend to dummy backend
> **Live-path status:** Dummy and provisional model-backed FastAPI flows verified
> **Frontend boundary:** `frontend/services/api_client.py`

Phase 2 now has a reproducible cross-service check:

```powershell
.\.venv\Scripts\python.exe scripts/phase2_smoke_test.py
```

The check starts a temporary FastAPI dummy backend and sends one validated image
through the real frontend Requests client. The adopted demo settings are a `2`
second connection timeout, `30` second read timeout, and `1 MiB` shared FE/BE
upload limit. Deployments can override all three settings.

## Stable frontend interface

The Streamlit application calls only:

```python
predict_image(image_file)
```

Both configured sources return the same validated internal structure:

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

Presentation components do not read environment variables, build URLs, create
multipart requests, or catch Requests exceptions.

## Configuration

| Environment variable | Mock mode | Real mode | Purpose |
| --- | --- | --- | --- |
| `STEELGUARD_USE_MOCK_API` | Required as `true` | Compose defaults to `false` | Select exactly one prediction source |
| `STEELGUARD_API_BASE_URL` | Ignored | Required | Credential-free HTTP(S) backend base URL; `/predict` is appended by the client |
| `STEELGUARD_API_CONNECT_TIMEOUT_SECONDS` | Ignored | Required | Explicit positive Requests connection timeout |
| `STEELGUARD_API_READ_TIMEOUT_SECONDS` | Ignored | Required | Explicit positive Requests response/read timeout |
| `STEELGUARD_MAX_UPLOAD_BYTES` | Optional | Required | Shared positive whole-byte FE/BE upload limit |
| `STEELGUARD_MOCK_RESPONSE_PATH` | Optional | Ignored | Override the canonical mock fixture path for development |
| `STEELGUARD_MOCK_DELAY_SECONDS` | Optional; defaults to `0.6` | Ignored | Keep the local loading state visible; clamped from `0` to `3` seconds |

Compose adopts `2` seconds for connection, `30` seconds for response/read, and
`1048576` bytes for upload as the local demo D-04 values. Real mode still
refuses to start if explicitly configured with missing or invalid values.

Do not place tokens, credentials, passwords, or other secrets in the base URL.
The current API contract does not require a frontend secret.

## Current mock behavior

With `STEELGUARD_USE_MOCK_API=true`:

1. `predict_image()` accepts one previously validated image.
2. The service loads `mock/prediction_response.json` or the optional configured
   fixture path.
3. The same response validator used by real mode checks every required field,
   enum, and confidence bound; it accepts the explicit dummy Grad-CAM `null`
   and rejects malformed non-null references.
4. The UI receives only the normalized internal structure.

## Real-mode behavior

With real mode deliberately enabled, the service:

1. appends `/predict` to the configured base URL;
2. performs one synchronous `POST` with one multipart field named `file`;
3. sends the original filename, bytes, and validated `image/jpeg` or
   `image/png` media type;
4. applies the explicitly configured connection and read timeouts;
5. accepts only HTTP `200` as the success transport status;
6. parses JSON and validates it through the same normalized response boundary;
7. performs no automatic retry and never falls back to mock data.

The dummy backend and provisional model adapter have both been exercised through
real `GET /health` and `POST /predict` requests. The model path has also passed
the complete Streamlit upload, Analyze, result, Grad-CAM, and reset workflow in
Docker Compose. The frontend accepts Grad-CAM as a PNG data URI, which is the
adopted transport for the local MVP. Final model acceptance still requires the
AI evidence and quality-owner recommendation mapping.

## Prepared error mapping

| Condition | Frontend service behavior |
| --- | --- |
| Connection refused | Safe `connection` error; no prediction |
| Timeout | Safe `timeout` error; no prediction and no automatic retry |
| HTTP `400` | Image-processing request error |
| HTTP `413` | Image exceeds the shared upload-size limit |
| HTTP `415` | Unsupported image-format error |
| HTTP `422` | Backend image-validation error |
| HTTP `500` | Internal service error |
| HTTP `503` | Temporarily unavailable service error |
| Other non-`200` status | Safe request/service error |
| Malformed JSON | Invalid-response error |
| Missing or invalid response field | Contract-validation error |

Raw Requests exceptions, backend internals, response bodies, local paths, and
credentials are not displayed to the operator.

Retryable connection, timeout, `500`, and `503` failures keep the valid image
and offer a deliberate retry. Non-retryable request/configuration failures
offer image replacement instead of retrying unchanged input.

## Activation checklist

When the real AI service and deployment settings become available:

- [x] Confirm the Phase 1 dummy `POST /predict` against `docs/API_CONTRACT.md`.
- [x] Adopt a PNG data URI as the frontend Grad-CAM transport for the local MVP.
- [x] Return and render a non-empty PNG data URI in provisional model mode;
      retain `null` only for the dummy stage.
- [x] Record demo D-04 values: 1 MiB upload, 2-second connect, 30-second read.
- [x] Verify the backend accepts exactly one multipart field named `file`.
- [x] Set `STEELGUARD_USE_MOCK_API=false` in the Compose target.
- [x] Set `STEELGUARD_API_BASE_URL` without `/predict` and without credentials.
- [x] Set both adopted timeout variables.
- [x] Add the backend service and health dependency to Docker Compose.
- [x] Run API-client tests against mocked transport.
- [x] Run contract tests against the FastAPI test application.
- [x] Run the reproducible full Streamlit-to-dummy-backend smoke test with a known test image.
- [x] Verify timeout, `400`, `413`, `415`, `422`, `500`, `503`, malformed JSON,
      and contract-invalid responses through live HTTP fault injection.
- [x] Confirm a failed real request never produces mock output.
- [x] Keep `app.py` and all presentation components unchanged for backend hookup.
