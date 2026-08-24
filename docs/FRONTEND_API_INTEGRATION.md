# SteelGuard AI Frontend API Integration Readiness

> **Current mode:** Mock API
> **Dummy backend status:** FastAPI Phase 1 available; local FE-to-BE smoke test verified
> **Frontend boundary:** `frontend/services/api_client.py`

Phase 2 now has a reproducible cross-service check:

```powershell
.\.venv\Scripts\python.exe scripts/phase2_smoke_test.py
```

The check starts a temporary FastAPI dummy backend and sends one validated image
through the real frontend Requests client. It uses temporary `2` second connect
and `10` second read values for the smoke test only; final D-04 timeout values
remain a team decision.

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
| `STEELGUARD_USE_MOCK_API` | Optional; defaults to `true` | Required as `false` | Select exactly one prediction source |
| `STEELGUARD_API_BASE_URL` | Ignored | Required | Credential-free HTTP(S) backend base URL; `/predict` is appended by the client |
| `STEELGUARD_API_CONNECT_TIMEOUT_SECONDS` | Ignored | Required | Explicit positive Requests connection timeout |
| `STEELGUARD_API_READ_TIMEOUT_SECONDS` | Ignored | Required | Explicit positive Requests response/read timeout |
| `STEELGUARD_MAX_UPLOAD_BYTES` | Optional | Required | Shared positive whole-byte FE/BE upload limit |
| `STEELGUARD_MOCK_RESPONSE_PATH` | Optional | Ignored | Override the canonical mock fixture path for development |
| `STEELGUARD_MOCK_DELAY_SECONDS` | Optional; defaults to `0.6` | Ignored | Keep the local loading state visible; clamped from `0` to `3` seconds |

The exact real connection/read timeout values remain **TBD** under project
decision D-04. Real mode deliberately refuses to start without both values;
the frontend does not invent deployment defaults.

Do not place tokens, credentials, passwords, or other secrets in the base URL.
The current API contract does not require a frontend secret.

## Current mock behavior

With `STEELGUARD_USE_MOCK_API=true` or with the variable unset:

1. `predict_image()` accepts one previously validated image.
2. The service loads `mock/prediction_response.json` or the optional configured
   fixture path.
3. The same response validator used by real mode checks every required field,
   enum, and confidence bound; it accepts the explicit dummy Grad-CAM `null`
   and rejects malformed non-null references.
4. The UI receives only the normalized internal structure.

## Prepared real-mode behavior

With real mode deliberately enabled, the service:

1. appends `/predict` to the configured base URL;
2. performs one synchronous `POST` with one multipart field named `file`;
3. sends the original filename, bytes, and validated `image/jpeg` or
   `image/png` media type;
4. applies the explicitly configured connection and read timeouts;
5. accepts only HTTP `200` as the success transport status;
6. parses JSON and validates it through the same normalized response boundary;
7. performs no automatic retry and never falls back to mock data.

The Phase 1 dummy backend has been exercised locally with one real
`GET /health` request and one real `POST /predict` request. The automated client
tests still use mocked Requests transport; the final integration test must run
against the confirmed deployment configuration.

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
- [ ] Confirm the final Grad-CAM transport representation.
- [ ] Require a non-empty Grad-CAM representation in live mode after transport
      confirmation; retain `null` only for the dummy stage.
- [ ] Resolve D-04 and record approved upload-size and timeout values.
- [ ] Verify the backend accepts exactly one multipart field named `file`.
- [ ] Set `STEELGUARD_USE_MOCK_API=false` in the target environment.
- [ ] Set `STEELGUARD_API_BASE_URL` without `/predict` and without credentials.
- [ ] Set both confirmed timeout variables.
- [x] Add the backend service and health dependency to Docker Compose.
- [x] Run API-client tests against mocked transport.
- [x] Run contract tests against the FastAPI test application.
- [x] Run the reproducible full Streamlit-to-dummy-backend smoke test with a known test image.
- [x] Verify timeout, `400`, `413`, `415`, `422`, `500`, `503`, malformed JSON,
      and contract-invalid responses through live HTTP fault injection.
- [x] Confirm a failed real request never produces mock output.
- [x] Keep `app.py` and all presentation components unchanged for backend hookup.
