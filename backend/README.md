# Backend Foundation

The backend will be a FastAPI service that connects the Streamlit frontend to
the AI inference adapter. This directory intentionally contains no application
code in the foundation phase.

## Required responsibilities

The backend team must:

1. Implement `POST /api/v1/predict` exactly as described in
   [`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md).
2. Accept exactly one multipart field named `image` and reject missing,
   repeated, unsupported, or unreadable inputs with appropriate HTTP errors.
3. Decode the image and invoke the AI adapter once. A request must never be
   expanded into batch or multi-image inference.
4. Validate the AI result against the six supported labels, confidence range,
   and three recommendation values before serialization.
5. Return classification, confidence, recommendation, and Grad-CAM reference
   without asking the frontend to derive any of them.
6. Make the Grad-CAM reference retrievable by the frontend. Any temporary
   artifact handling must not become inspection history or automated data
   logging.
7. Convert validation, inference, and availability failures into documented,
   non-sensitive HTTP error responses.

## AI adapter boundary

The backend should receive one logical inference result from the AI subsystem:

```text
class_name       one supported defect label
confidence       floating-point score from 0.0 through 1.0
recommendation   ACCEPT, REWORK, or REJECT
gradcam_artifact image bytes, an in-memory object, or a temporary artifact
```

The backend is responsible for turning `gradcam_artifact` into the
`gradcam_image` resource reference used by the HTTP contract. It must not
reclassify the image, synthesize a confidence score, or invent a recommendation
when the AI adapter fails.

## Backend deliverables for frontend integration

- A reachable FastAPI base URL configurable by environment.
- The versioned prediction endpoint and OpenAPI schema.
- CORS configuration for the deployed Streamlit origin when the services are
  hosted on different origins.
- Predictable timeouts and the documented JSON error shape.
- A browser-retrievable Grad-CAM reference.
- A container definition before a backend service is added to Compose.

## Out of scope for the preliminary MVP

Do not implement authentication, accounts, inspection history, analytics,
automated result logging, background jobs, distributed storage, batch
endpoints, or multi-image endpoints.
