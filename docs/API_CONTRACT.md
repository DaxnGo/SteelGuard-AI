# SteelGuard AI API Contract

> **Purpose:** Establish a stable request and response boundary between the
> Streamlit frontend and FastAPI backend before either implementation is
> complete.
>
> **Contract endpoint:** `POST /predict`
>
> **Contract status:** Normative except for decisions explicitly marked `TBD`.

The preliminary MVP accepts exactly one steel surface image per request and
returns exactly one prediction result. The frontend displays the backend
response; it does not calculate or replace any AI-derived value.

## Contract principles

- Field names, types, allowed values, HTTP statuses, and error codes in this
  document are part of the frontend/backend contract.
- The backend must never return a fabricated prediction when validation,
  inference, or Grad-CAM generation fails.
- The frontend must never silently repair an invalid success response or fall
  back to mock data after a live request fails.
- A breaking contract change must update this document, the frontend client,
  backend schema, mock fixtures, and contract tests together.

## 1. Endpoint

```http
POST /predict
```

| Property | Contract |
| --- | --- |
| Method | `POST` |
| Path | `/predict` |
| Request content type | `multipart/form-data` |
| Response content type | `application/json` |
| Authentication | None in the preliminary MVP |
| Request cardinality | Exactly one image |
| Response cardinality | Exactly one prediction or one error |

The client must use `/predict` exactly. A trailing-slash redirect must not be
required for normal operation.

## 2. Request Format

The request body is `multipart/form-data` with exactly one file field.

| Property | Contract |
| --- | --- |
| Field name | `file` |
| Field type | Binary file part |
| Required | Yes |
| Number of files | Exactly one |
| Supported media types | `image/jpeg`, `image/png` |

Example request:

```bash
curl -X POST http://localhost:8000/predict \
  -H "accept: application/json" \
  -F "file=@steel-surface.jpg;type=image/jpeg"
```

Request rules:

1. The frontend sends the original selected image bytes in the `file` field.
2. The backend rejects a missing `file` field.
3. The backend rejects repeated `file` fields or any attempt to submit more
   than one image.
4. The backend validates the decoded content and must not trust only the
   filename extension or client-supplied media type.
5. A maximum upload size is not defined by this contract yet. If introduced,
   it must be agreed by both teams, documented here, applied consistently, and
   use `413 Payload Too Large` when exceeded.

Missing-file response:

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "missing_file",
    "message": "One image file is required."
  }
}
```

Multiple-file response:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "multiple_files_not_allowed",
    "message": "Only one image may be analyzed per request."
  }
}
```

## 3. Response Schema

### Successful response

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "success": true,
  "prediction": {
    "class_name": "Scratches",
    "confidence": 0.942,
    "recommendation": "REWORK",
    "gradcam_image": "<representation to be agreed>"
  }
}
```

The confidence in this example is illustrative contract data, not a model
accuracy claim or performance target.

| Field | JSON type | Required | Constraint |
| --- | --- | --- | --- |
| `success` | boolean | Yes | Exactly `true` for `200 OK` |
| `prediction` | object | Yes | Contains all four fields below |
| `prediction.class_name` | string | Yes | One exact value from Section 4 |
| `prediction.confidence` | number | Yes | Finite value from `0.0` through `1.0` |
| `prediction.recommendation` | string | Yes | One exact value from Section 5 |
| `prediction.gradcam_image` | string | Yes | Non-empty representation selected under Section 7 |

A `200 OK` response is valid only when every required field is present and
valid. The backend must return an error rather than a partial prediction. The
frontend must treat a malformed `200 OK` body as a contract error and display
no result.

### Error response envelope

All anticipated non-success responses use one stable envelope:

```json
{
  "success": false,
  "error": {
    "code": "machine_readable_code",
    "message": "Concise user-safe message."
  }
}
```

| Field | JSON type | Required | Constraint |
| --- | --- | --- | --- |
| `success` | boolean | Yes | Exactly `false` for an error response |
| `error` | object | Yes | Error details; no `prediction` object is present |
| `error.code` | string | Yes | Stable machine-readable code defined by this contract |
| `error.message` | string | Yes | Concise, non-sensitive, user-safe explanation |

Error bodies must not expose stack traces, local paths, secrets, model
internals, framework exceptions, or uploaded image data.

## 4. Supported Classes

`prediction.class_name` is case-sensitive and must be exactly one of:

1. `Crazing`
2. `Inclusion`
3. `Patches`
4. `Pitted Surface`
5. `Rolled-in Scale`
6. `Scratches`

The backend owns model-index-to-label mapping and validates the AI adapter's
value before serialization. The frontend validates membership for contract
integrity and displays the exact returned string. It must not rename, merge,
infer, or substitute a class.

Adding, removing, renaming, or changing the case of a class is a breaking
contract change.

## 5. Recommendation Enum

`prediction.recommendation` is case-sensitive and must be exactly one of:

- `ACCEPT`
- `REWORK`
- `REJECT`

> **TBD – recommendation logic must be defined by AI/backend/product team.**

This contract defines only the transport enum. It does not define which class,
confidence, severity, threshold, or other condition produces a recommendation.
No frontend lookup table, confidence threshold, or fallback rule may be used to
derive it. The algorithm must be agreed, documented, and tested before a live
backend returns recommendation values.

## 6. Confidence Format

`prediction.confidence` is a JSON number representing the AI subsystem's score
for the returned class.

| Rule | Contract |
| --- | --- |
| Minimum | `0.0` |
| Maximum | `1.0` |
| Bounds | Inclusive |
| Valid form | Finite JSON number |
| Invalid forms | String, boolean, `null`, NaN, infinity, or out-of-range number |

The backend returns the normalized numeric value and documents how the selected
model calculates it. The frontend may format it as a percentage for display,
but must retain its meaning, label it as model confidence rather than accuracy,
and must not use it to change the class or recommendation.

The number of decimal places is not fixed. Clients must not rely on the example
precision shown in Section 3.

## 7. Grad-CAM Delivery Strategy

`prediction.gradcam_image` remains a required string, but its representation
needs confirmation before frontend and backend implementation are finalized.

> **TBD – Grad-CAM transport must be confirmed by the frontend and backend
> teams.**

### Option A: Base64-encoded image

The backend embeds the generated PNG in the JSON response, preferably as a
data URI:

```json
{
  "gradcam_image": "data:image/png;base64,<encoded-png-bytes>"
}
```

Advantages:

- one request and one response contain the complete result;
- no generated-file endpoint, shared volume, public container hostname, or
  cleanup lifecycle is required; and
- the Streamlit server can decode the data directly for display.

Tradeoffs:

- base64 increases response size;
- the frontend must validate and decode the representation safely; and
- this approach is less suitable if Grad-CAM artifacts later become large or
  persistent.

### Option B: Image endpoint or generated-file reference

The backend returns an absolute URL or a relative resource path, for example:

```json
{
  "gradcam_image": "/gradcam/<artifact-id>.png"
}
```

Advantages:

- keeps the JSON response smaller; and
- lets the image be retrieved and cached as a normal resource.

Tradeoffs:

- requires an additional resource request;
- requires browser- or Streamlit-reachable URL configuration across Docker
  networking;
- requires temporary storage or an in-memory artifact registry; and
- requires expiry, cleanup, missing-resource, and optional CORS behavior.

### MVP recommendation

**Recommend Option A: a PNG data URI containing base64-encoded bytes for the
local Docker Compose MVP.** It is the simplest option for a single-image,
single-result workflow because it avoids a second endpoint, generated-file
storage, resource cleanup, and container-to-browser URL concerns. The expected
size impact must still be checked with representative Grad-CAM output before
the teams confirm the decision.

Whichever option is selected must be documented here and covered by contract
tests. The backend must generate Grad-CAM from the same inference as the class
and confidence. The frontend must label it as a model explanation, not as a
segmentation mask or precise defect boundary.

## 8. Invalid File Response

Use this response when the `file` part exists and claims a supported media type
but is empty, corrupt, unreadable, or cannot be decoded as a valid supported
image.

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "invalid_file",
    "message": "The uploaded file is empty or could not be decoded as a valid image."
  }
}
```

The backend must not call the AI adapter after this validation fails. The
frontend should preserve no invalid preview/result and should ask the user to
select another file.

## 9. Unsupported Format Response

Use this response when the supplied or decoded format is not JPEG or PNG. A
renamed extension does not make unsupported content valid.

```http
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "unsupported_media_type",
    "message": "Only JPEG and PNG images are supported."
  }
}
```

The backend must not call the AI adapter for an unsupported format. The
frontend may perform the same allowlist check for early feedback, but backend
validation remains authoritative.

## 10. AI Inference Failure Response

Use this response when the request is valid but the required AI operation
cannot complete, including an unavailable model artifact, inference exception,
invalid AI adapter output, or Grad-CAM generation failure.

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "inference_failed",
    "message": "The image could not be analyzed at this time. Please try again."
  }
}
```

The response must not contain `prediction`, partial AI output, a default class,
zero confidence, a placeholder Grad-CAM, or a guessed recommendation. The
backend should record technical diagnostics through its approved operational
logging mechanism without returning them to the frontend.

The frontend treats this as a recoverable service error, preserves the valid
selected image, and allows a deliberate retry. It must not retry automatically.

## 11. Internal Server Error Response

Use this response for an unexpected backend failure outside the recognized
request-validation and AI-inference cases.

```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "internal_server_error",
    "message": "An unexpected server error occurred. Please try again."
  }
}
```

The backend must return the stable safe envelope even when internal diagnostics
contain more detail. The frontend must show a generic recoverable message and
must not render any partial result.

## 12. Frontend Timeout Behavior

The frontend HTTP client must configure explicit connection and response/read
timeouts. Exact timeout values are a shared deployment decision and must not be
invented independently by the frontend.

On timeout, the frontend must:

1. stop waiting for the response and transition from `ANALYZING` to `ERROR`;
2. show a concise message such as “Analysis did not complete in time. Please
   try again.”;
3. preserve the already validated selected image so the user can retry;
4. display no partial, cached, default, or mock prediction; and
5. avoid automatic retry because the backend may still have completed the
   original inference.

A retry is a new, deliberate user action and creates a new request. The
frontend must prevent concurrent submission while the original request is
still considered active locally.

Connection failures, DNS failures, malformed JSON, unexpected content types,
and contract-invalid `200 OK` responses follow the same safe `ERROR` behavior,
with a message appropriate to the failure category.

## 13. Backend Responsibilities

The backend must:

- implement `POST /predict` and accept exactly one multipart field named
  `file`;
- reject missing, repeated, empty, unsupported, corrupt, or undecodable input
  using the documented status and error envelope;
- validate actual decoded content rather than relying only on extension or
  client-supplied media type;
- invoke the AI adapter exactly once for a valid request;
- validate the adapter's class, confidence, recommendation, and Grad-CAM before
  serializing success;
- return all required prediction fields from the same inference;
- implement the confirmed Grad-CAM transport strategy;
- map known validation and inference failures to stable contract errors;
- convert unexpected failures to the safe internal-server-error response;
- avoid persisting uploads, results, or Grad-CAM as inspection history in the
  preliminary MVP; and
- never delegate classification, confidence, Grad-CAM generation, or
  recommendation logic to the frontend.

> **TBD – recommendation logic must be defined by AI/backend/product team.**

Until that decision is approved, backend test doubles may return contract-valid
recommendation fixtures for integration testing, but those fixtures must be
clearly identified and must not be represented as live decision logic.

## 14. Frontend Responsibilities

The frontend must:

- accept exactly one user-selected JPG, JPEG, or PNG image;
- perform non-authoritative usability validation and preview with Pillow;
- submit the original image bytes once in the multipart `file` field;
- call the exact `/predict` path through a centralized Requests/HTTPX client;
- apply explicitly configured connection and response/read timeouts;
- validate HTTP status, JSON structure, `success`, required fields, class enum,
  confidence bounds, recommendation enum, and Grad-CAM representation;
- display only a complete valid backend response;
- format confidence for presentation without using it as a decision threshold;
- display the exact backend class and recommendation without remapping them;
- decode or retrieve Grad-CAM according to the confirmed transport option and
  label it as a model explanation;
- map errors to concise user-safe messages and preserve a valid image when a
  deliberate retry is appropriate;
- prevent duplicate concurrent submission and automatic POST retry; and
- never fabricate results, infer a recommendation, or fall back to mock data
  after a live failure.

The frontend may validate the response more strictly for safety, but it must
not accept a response that violates this contract.
