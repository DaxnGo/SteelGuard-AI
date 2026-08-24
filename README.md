# SteelGuard AI

Intelligent Steel Surface Defect Detection for Smart Manufacturing.

SteelGuard AI is a competition-project monorepo for single-image steel surface
inspection. The Streamlit frontend accepts one image, calls either the local
mock or the Phase 1 FastAPI dummy backend, and displays a defect class,
confidence score, quality recommendation, and an honest Grad-CAM placeholder.

The repository currently contains:

- a working single-page Streamlit frontend with upload, validation, preview,
  loading, result, error, retry, and reset states;
- a validated mock prediction service and configurable Requests API client;
- a Phase 1 FastAPI backend with `/health` and dummy `/predict` endpoints;
- backend request validation, error responses, tests, and a Dockerfile;
- documented backend and AI boundaries;
- an API contract for the prediction endpoint;
- a contract-shaped mock response used by the frontend; and
- repository documentation for scope, flow, and ownership.

The frontend is presentation-only. It must never calculate or alter the
classification, confidence, Grad-CAM, or recommendation returned by the
backend.

## Current status

- The Streamlit frontend completes the one-image workflow with explicit mock
  AI output.
- The prediction client defaults to mock mode and includes a configuration-
  gated, mocked-test-covered Requests adapter for future `POST /predict` use.
- Frontend components, Pillow validation, response validation, errors, retry,
  and reset are implemented and covered by automated tests.
- The Phase 1 FastAPI backend and dummy AI adapter are available; the trained
  deep-learning model remains future work.
- Phase 2 FE-to-dummy-BE `POST /predict` integration is reproducibly smoke-tested
  with `python scripts/phase2_smoke_test.py`.
- Generated Grad-CAM and the final recommendation policy remain future work.
- Docker Compose now defines healthy backend and frontend services; live mode
  requires explicit environment values while D-04 remains open.

## Quick start

Use Python 3.11 to match the frontend container.

### Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r frontend/requirements.txt -r backend/requirements.txt
streamlit run frontend/app.py
```

For POSIX shells, activate the environment with `source .venv/bin/activate`.
Then open <http://localhost:8501>.

To run the dummy backend locally in a second terminal:

```powershell
uvicorn app.main:app --app-dir backend --reload --port 8000
```

For a local FE-to-BE smoke test, set `STEELGUARD_USE_MOCK_API=false`,
`STEELGUARD_API_BASE_URL=http://localhost:8000`, positive connection/read
timeouts, and one positive `STEELGUARD_MAX_UPLOAD_BYTES` value before starting
Streamlit. Smoke-test values are temporary and are not the final D-04 decision.

To run the reproducible Phase 2 check, which starts a temporary dummy backend
and completes the upload, Analyze, and result flow through the production
Streamlit application:

```powershell
.\.venv\Scripts\python.exe scripts/phase2_smoke_test.py
```

Run the automated frontend tests from the repository root:

```powershell
cd frontend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

### Run with Docker Compose

```bash
docker compose up --build
```

The frontend is exposed at <http://localhost:8501> and the backend at
<http://localhost:8000>. Compose keeps the frontend in mock mode by default;
set the live API variables in `.env` to exercise the dummy backend through the
container network.

## Repository layout

```text
frontend/   Streamlit application, UI boundaries, styles, and API client boundary
backend/    FastAPI request validation, dummy prediction API, tests, and Docker
ai/         AI integration guidance; no model or inference code yet
docs/       Product, architecture, API, UI, and development documentation
mock/       Contract-shaped fixtures for independent frontend development
```

See these documents before implementing a subsystem:

| Document | Purpose |
| --- | --- |
| [Project plan](docs/PROJECT_PLAN.md) | Delivery phases, ownership, and completion criteria |
| [Features](docs/FEATURES.md) | MVP capabilities and explicit exclusions |
| [Architecture](docs/ARCHITECTURE.md) | Service boundaries and end-to-end data flow |
| [API contract](docs/API_CONTRACT.md) | Stable prediction request and response contract |
| [Frontend API readiness](docs/FRONTEND_API_INTEGRATION.md) | Mode configuration, error mapping, and backend activation checklist |
| [UI flow](docs/UI_FLOW.md) | Single-image interaction states and transitions |
| [Frontend specification](docs/FRONTEND_SPEC.md) | Streamlit component responsibilities and constraints |
| [Development log](docs/DEVELOPMENT_LOG.md) | Chronological record and entry template |

## Team responsibilities

- Frontend: accept and preview one image, call the backend, and display
  backend-supplied output.
- Backend: validate the HTTP request, invoke the AI adapter once, serialize
  the result and confirmed Grad-CAM representation, and return clear HTTP
  errors.
- AI: own preprocessing, model inference, label mapping, confidence,
  Grad-CAM generation, and recommendation policy.

No subsystem should add authentication, accounts, inspection history,
analytics dashboards, automated data logging, background jobs, distributed
databases, batch inference, or multi-image inference to the preliminary MVP.

## API boundary

The planned frontend integration uses `POST /predict` with one
`multipart/form-data` field named `file`. The complete contract and error
behavior are defined in [docs/API_CONTRACT.md](docs/API_CONTRACT.md).

## Git conventions

Use [Conventional Commits](https://www.conventionalcommits.org/) for readable
history and automated release tooling. Keep commits focused and use an
imperative, lowercase description.

```text
chore: initialize SteelGuard AI monorepo foundation
feat(frontend): add single-image upload and preview
feat(backend): expose prediction endpoint
docs: clarify Grad-CAM response contract
fix(frontend): preserve selected image after API error
test(ai): cover supported defect labels
```

Recommended first foundation commit:

```text
chore: initialize SteelGuard AI monorepo foundation
```

## License

This project is licensed under the [MIT License](LICENSE).
