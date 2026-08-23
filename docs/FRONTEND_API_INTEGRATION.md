# SteelGuard AI Frontend API Integration Readiness

> **Current mode:** Mock API
> **Live backend status:** Not connected
> **Frontend boundary:** `frontend/services/api_client.py`

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

No request to a real backend is part of the current MVP execution or automated
tests. HTTP behavior is tested through mocked Requests responses.

## Prepared error mapping

| Condition | Frontend service behavior |
| --- | --- |
| Connection refused | Safe `connection` error; no prediction |
| Timeout | Safe `timeout` error; no prediction and no automatic retry |
| HTTP `400` | Image-processing request error |
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

When the FastAPI service becomes available:

- [ ] Confirm `POST /predict` against `docs/API_CONTRACT.md`.
- [ ] Confirm the final Grad-CAM transport representation.
- [ ] Require a non-empty Grad-CAM representation in live mode after transport
      confirmation; retain `null` only for the dummy stage.
- [ ] Resolve D-04 and record approved connection/read timeout values.
- [ ] Verify the backend accepts exactly one multipart field named `file`.
- [ ] Set `STEELGUARD_USE_MOCK_API=false` in the target environment.
- [ ] Set `STEELGUARD_API_BASE_URL` without `/predict` and without credentials.
- [ ] Set both confirmed timeout variables.
- [ ] Add the backend service and health dependency to Docker Compose.
- [ ] Run API-client tests against mocked transport.
- [ ] Run contract tests against the FastAPI test application.
- [ ] Run one frontend-to-backend integration test with a known test image.
- [ ] Verify connection, timeout, `400`, `415`, `422`, `500`, `503`, malformed
      JSON, and contract-invalid responses.
- [ ] Confirm a failed real request never produces mock output.
- [ ] Keep `app.py` and all presentation components unchanged.
