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

## 2026-08-24 — Phase 2 FE-to-dummy-BE smoke check

**Status:** Verified

### Changes

- Added `scripts/phase2_smoke_test.py`, a reproducible check that starts a
  temporary FastAPI dummy backend and exercises it through the real frontend
  Requests client.
- Documented the Phase 2 command in the README and frontend integration guide.

### Validation

- The smoke check validates the live client configuration, one multipart image
  request, and the contract-shaped dummy response without using mock data.
- D-04 timeout values and D-05 Grad-CAM transport remain explicitly unresolved;
  the smoke check uses temporary local timeout values and accepts dummy
  `gradcam_image: null` only.

## 2026-08-24 — Phase 2 live frontend hardening and demo rehearsal

**Status:** Implemented; target activation awaits approved D-04 values

### Changes

- Added `STEELGUARD_MAX_UPLOAD_BYTES` as one shared FE/BE upload-size setting.
- Added frontend early rejection and authoritative backend `413 FILE_TOO_LARGE`
  handling without invoking prediction.
- Upgraded the Phase 2 smoke check to exercise the complete Streamlit upload,
  Analyze, result, and reset path against the real dummy FastAPI process.
- Added live HTTP UI coverage for timeout, `400`, `413`, `415`, `422`, `500`,
  `503`, malformed JSON, and contract-invalid JSON.
- Improved error recovery guidance, heading hierarchy, decorative icon
  semantics, focus styling, reduced-motion behavior, and narrow-layout rules.

### Validation

- Backend tests: 10 passed.
- Frontend tests: 54 passed, including live HTTP fault injection.
- Full Streamlit-to-dummy-FastAPI smoke test passed.
- Browser rehearsal passed for successful inspection, backend outage recovery,
  deliberate retry, and reset.
- Browser layout checks found no horizontal overflow at `390 × 844` or
  `1440 × 900`; result columns stack on the narrow viewport.
- Docker Compose configuration renders successfully.

### Pending decision

- The repository deliberately does not choose the numeric upload limit or
  connect/read timeouts. D-04 must be approved before live mode is enabled in
  the target environment.

## 2026-08-25 — Provisional AI adapter and full container integration

**Status:** Technically verified; final model, policy, and deployment approvals remain open

### Changes

- Reconciled the AI branch with the latest frontend/backend integration while
  preserving the supplied checkpoint commit.
- Replaced the duplicate standalone AI HTTP service with one in-process adapter
  imported by FastAPI.
- Added checkpoint checksum and exact label-order validation, lazy model loading,
  one-result inference, and Grad-CAM generated from the selected score in the
  same forward pass.
- Added explicit `dummy` and `model` backend modes. Model mode requires a
  complete recommendation mapping, fails startup on invalid configuration, and
  never falls back to dummy output.
- Added bounded PNG data-URI decoding in the frontend and removed duplicate AI
  Docker/service definitions.
- Updated the backend image with the CPU model runtime and model package, and
  updated Compose to pass explicit AI configuration while retaining safe
  mock/dummy defaults.
- Synchronized the README, architecture, feature inventory, API integration,
  API contract, project plan, and AI artifact documentation with the
  implemented provisional path.

### Validation

- Local AI/backend tests: 40 passed; the heavy model smoke test skipped because
  Ultralytics is intentionally installed in the backend image.
- Frontend tests: 56 passed, including timeout, `400`, `413`, `415`, `422`,
  `500`, `503`, malformed JSON, invalid response, accessibility, and responsive
  layout coverage.
- Backend-image tests: 41 passed, including the real checkpoint and Grad-CAM
  smoke test.
- Both Docker images built successfully; Compose backend and frontend became
  healthy.
- Browser rehearsal passed for live Streamlit upload, model-backed prediction,
  confidence/recommendation presentation, backend-supplied Grad-CAM rendering,
  and reset.
- Browser responsive checks found no horizontal overflow at `375 x 812` or
  `1280 x 800`; comparison columns stack on the narrow viewport and align on
  desktop. The upload control is a native enabled button with `tabIndex=0` and
  a visible 3 px focus outline.
- The reproducible Streamlit-to-dummy-FastAPI Phase 2 smoke check remains green.

### Pending decisions and evidence

- The YOLO11n checkpoint is provisional. The AI owner must still provide D-01
  dataset/split provenance and D-02 candidate evaluation, metrics, calibration,
  and selection evidence.
- The all-`REWORK` mapping and `1 MiB`, 2-second connect, and 30-second read
  settings used for container rehearsal were test-only. They are not D-03 or
  D-04 production decisions.
- PNG data URI is implemented as the repository-recommended D-05 option, but
  formal D-05 and D-06 target/deployment sign-off remains required.

## 2026-08-25 — Reproducible AI technical evidence

**Status:** Technical evidence recorded; dataset/model-quality evidence pending

### Changes

- Added a no-new-dependency benchmark entry point for the complete CPU adapter
  path, including model/checksum startup, classification, and same-pass Grad-CAM.
- Added deterministic synthetic input, JSON metadata output, latency statistics,
  hardware/runtime details, peak process RSS, and focused unit tests.
- Recorded the verified checkpoint labels, public API labels, checksum, runtime,
  Grad-CAM target layer, measured demo-host performance, and explicit evidence
  boundaries in `ai/TECHNICAL_EVIDENCE.md`.

### Validation

- The backend image rebuilt successfully with the benchmark entry point.
- Ten measured runs after two warmups completed on an Intel Core i3-7020U CPU.
- Median full-adapter latency was 571.66 ms, P95 was 764.44 ms, model/checksum
  startup was 3,524.11 ms, and process peak RSS was 575.59 MiB.

### Pending evidence

- The benchmark uses deterministic synthetic input and confidence threshold
  `0.0`; it is not evidence of model accuracy, calibration, dataset quality, or
  the production threshold.
- Dataset provenance/splits, held-out metrics, candidate comparison, and the
  quality-owner recommendation mapping remain assigned to the AI/domain owners.

## 2026-08-25 — Auditable AI dataset and evaluation pipeline

**Status:** Pipeline and dataset audit verified; final model-quality evidence pending

### Changes

- Replaced the uploaded training script with deterministic `prepare`, `train`,
  and `evaluate` commands that can be run from the repository root.
- Audited the official NEU-DET archive without committing it. The source contains
  1,800 images and annotations; one exact duplicate image is excluded, leaving a
  documented 1,259/360/180 train/validation/test split with seed 42.
- Added strict filename/class and Pascal VOC validation, duplicate-image and
  split-leakage checks, deterministic duplicate removal, and refusal to mix a
  new preparation run into a non-empty output directory.
- Added machine-readable overall/per-class evaluation output, macro-F1,
  confusion-matrix generation, runtime metadata, checkpoint label validation,
  and SHA-256 recording.
- Corrected the AI documentation to distinguish the current checkpoint's
  embedded 224-pixel, 50-epoch, seed-0 metadata from the new future-run protocol.
  Unsupported license, held-out accuracy, and candidate-comparison claims were
  removed.

### Validation

- Eight focused pipeline regression tests pass.
- Dataset preparation completed from the official archive and produced the
  expected class counts, split sizes, duplicate audit, and manifest checksum.
- Local AI/backend suite: 51 passed and 1 optional heavy-runtime test skipped.
- Rebuilt backend Docker image: 19 AI tests passed inside the production image,
  including the bundled checkpoint and same-pass Grad-CAM smoke test.
- Frontend suite: 56 passed; the Streamlit-to-dummy-FastAPI Phase 2 smoke test
  also passed.
- The evaluator completed a real diagnostic run with the bundled checkpoint and
  produced all expected metric and plot artifacts. Its numeric results are not
  treated as held-out evidence because the checkpoint's original split is
  unknown.

### Pending evidence and approvals

- Train a fresh checkpoint from the documented split, then publish its untouched
  test-set metrics, per-class results, confusion matrix, and reviewed prediction
  examples.
- Compare model candidates on the same split or approve explicit acceptance
  criteria for YOLO11n.
- Confirm production usage rights for NEU-DET; neither the official page nor the
  inspected mirror provides an affirmative dataset license.
- Obtain the quality/domain owner's official six-class recommendation mapping
  before enabling production model mode.
