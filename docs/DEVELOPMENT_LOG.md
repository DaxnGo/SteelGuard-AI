# Development Log

Use this log for decisions and changes that affect more than one subsystem or
the competition demonstration. It complements Git history; it is not an
inspection-event log and must never contain user images or predictions.

## Entry template

```markdown
## YYYY-MM-DD — Short change title

**Status:** Planned | In progress | Implemented | Verified

### Changes

- What changed.

### Decisions

- Contract, ownership, or scope decision and its reason.

### Validation

- Check performed and outcome.

### Follow-up

- Remaining work, or “None”.
```

## 2026-08-11 — Repository foundation

**Status:** Verified

### Changes

- Established frontend, backend, AI, documentation, and mock-data boundaries.
- Added a startup-only Streamlit page and placeholder frontend modules.
- Added a frontend Dockerfile and frontend-only Docker Compose service.
- Defined the single-image v1 prediction contract and team responsibilities.

### Decisions

- The current repository root is the monorepo root; no nested project directory
  is used.
- The preliminary MVP remains limited to one image, one request, and one result.
- The frontend is display-only for all AI-derived output.
- Requests is the planned synchronous frontend HTTP client.
- MIT is the repository license.

### Validation

- Confirmed all 30 expected foundation files exist.
- Compiled the frontend Python modules and imported all declared dependencies.
- Verified the mock JSON exactly matches the approved response object.
- Executed the Streamlit app through its test harness without an app exception.
- Started a real Streamlit server and received `200 ok` from its health endpoint.
- Passed prohibited-branding, trailing-whitespace, and Git diff checks.
- Inspected the frontend-only Compose structure statically. Docker runtime
  validation remains unavailable on the current host because Docker is not
  installed.

### Follow-up

- Implement the documented frontend workflow, FastAPI service, and AI adapter
  in their respective delivery phases.

## 2026-08-11 — Frontend mock inspection MVP

**Status:** Verified

### Changes

- Implemented the single-image Streamlit workflow from upload through reset.
- Added Pillow validation, original-image preview, and safe validation errors.
- Added a contract-validating `predict_image(...)` service backed by the mock
  response fixture.
- Added defect, confidence, recommendation, and original-versus-Grad-CAM
  presentation components; missing mock Grad-CAM uses an honest placeholder.
- Added responsive industrial styling and explicit mock-mode labeling.

### Decisions

- The frontend remains display-only for classification, confidence, Grad-CAM,
  and recommendation.
- Mock prediction data flows through the same service boundary intended for
  the future `POST /predict` integration.
- A mock latency is configurable only to make the inference loading state
  visible; it does not simulate training progress.
- No generated scientific heatmap is fabricated for the mock result.

### Validation

- Passed 15 unittest and Streamlit AppTest cases covering the happy path,
  reset, corrupt input, service failure, response fields, class enum, and
  confidence bounds.
- Compiled all frontend Python modules successfully.
- Started the real Streamlit server and received `ok` from its health endpoint.
- Automated browser control and Docker runtime validation were unavailable on
  the current host; the Streamlit test harness covered UI interactions.

### Follow-up

- Implement FastAPI and AI separately, confirm Grad-CAM transport, then replace
  the mock service internals with `POST /predict` without rewriting components.

## 2026-08-23 — Frontend integration-ready freeze

**Status:** Verified

### Changes

- Aligned the dummy response with `gradcam_image: null` and retained the honest
  Grad-CAM placeholder until the live transport is confirmed.
- Preserved normalized error retryability so unchanged invalid input cannot be
  submitted again from the error state.
- Added regression coverage for nullable dummy Grad-CAM and retryable versus
  non-retryable recovery controls.

### Decisions

- `gradcam_image` remains required, but `null` is valid only during dummy
  integration. Live inference must use the transport confirmed under D-05.
- Retryable service failures keep the current valid image and offer a deliberate
  retry; non-retryable failures require replacement.

### Validation

- Passed all 44 frontend unittest and Streamlit AppTest cases, including the
  complete 90-case response matrix.

### Follow-up

- Wait for the dummy FastAPI endpoint, then run frontend-to-backend contract
  integration and resolve the remaining D-04/D-05 settings with the team.

## 2026-08-24 — Phase 1 backend and dummy integration

**Status:** Verified

### Changes

- Integrated the Phase 1 FastAPI `/health` and `/predict` implementation while
  preserving the existing frontend history after the remote branch was
  force-pushed as a standalone backend root commit.
- Added backend Docker and health-checked two-service Compose wiring.
- Removed generated backend `__pycache__` artifacts from the imported commit.
- Added authoritative decoded-format validation for extension/content mismatches.

### Decisions

- Compose keeps the frontend in mock mode by default because D-04 timeout values
  are not yet approved. Live dummy mode is available through explicit local
  environment settings.
- Phase 1 returns `gradcam_image: null`; final live Grad-CAM transport remains
  the D-05 decision.

### Validation

- Backend suite passes: 8 tests.
- Frontend suite remains green: 44 tests.
- Local smoke test passed against Uvicorn: `GET /health` returned `{"status":"ok"}`
  and FE `POST /predict` returned the validated dummy prediction.

### Follow-up

- Resolve D-04/D-05 with the team, then switch the Compose environment to live
  mode and add the real AI adapter without changing the frontend presentation
  boundary.
