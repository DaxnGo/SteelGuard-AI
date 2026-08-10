# Project Plan

## Objective

Deliver a competition-ready preliminary MVP that accepts one steel surface
image, performs one AI inference, and presents the backend-returned defect
class, confidence, Grad-CAM, and quality recommendation.

The project succeeds when a user can complete that path reliably and then
reset the interface to analyze another image. Breadth beyond this interaction
does not improve the preliminary MVP and is intentionally excluded.

## Delivery principles

1. Keep frontend presentation, HTTP orchestration, and AI inference as separate
   boundaries.
2. Treat [`API_CONTRACT.md`](API_CONTRACT.md) as the shared integration source
   of truth.
3. Support exactly one image per interaction and one inference per request.
4. Keep the frontend deterministic: every inference value originates from the
   backend response.
5. Prefer a reliable demo path over premature platform capabilities.

## Milestones

| Phase | Primary owner | Deliverable | Exit criteria |
| --- | --- | --- | --- |
| 0. Foundation | Shared | Monorepo tree, startup page, mock response, documentation, container configuration | Streamlit starts; structure and fixture validate |
| 1. Frontend MVP | Frontend | Upload, preview, analyze, loading/error, result, Grad-CAM, and reset states | Works against the approved mock and never derives AI output |
| 2. Backend API | Backend | FastAPI prediction endpoint and retrievable Grad-CAM resource | Request/response and errors conform to the contract |
| 3. AI adapter | AI | Single-image adapter with preprocessing, inference, explanation, and recommendation | Adapter returns valid output for representative inputs |
| 4. Integration | Shared | Streamlit-to-FastAPI-to-model path | End-to-end acceptance scenarios pass |
| 5. Demo hardening | Shared | Containerized startup, recovery behavior, and operator instructions | Clean-machine rehearsal completes without manual code changes |

Phase 0 is the scope of the repository initialization. Later phases are
documented for coordination but are not implemented as part of the foundation.

## Ownership and dependencies

- The frontend team can build against
  [`mock/prediction_response.json`](../mock/prediction_response.json) while the
  backend is under development.
- The backend team can implement transport and validation against a test-double
  AI adapter while the production model is under development.
- The AI team can develop the adapter without importing Streamlit or FastAPI.
- Any contract change must update the API contract, mock fixture, affected
  tests, and development log in the same pull request.

## Preliminary MVP acceptance criteria

- Only JPEG or PNG input can enter the supported UI path.
- The user can select only one image and see its preview before analysis.
- Analysis cannot start without a valid image and cannot be triggered twice
  concurrently.
- Success renders exactly one supported class, a confidence score, one
  recommendation, and one Grad-CAM visualization from the backend response.
- A request or inference failure produces a recoverable message without
  fabricating a result.
- Analyze another image clears the current selection and result.
- No user identity, history, analytics, persistence, batch, or multi-image
  behavior is present.

## Scope control

Requests for authentication, accounts, inspection history, analytics
dashboards, automated logging, background jobs, distributed databases, batch
inference, or multi-image inference should be recorded for a later phase and
must not be merged into the preliminary MVP.
