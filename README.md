# SteelGuard AI

Intelligent Steel Surface Defect Detection for Smart Manufacturing.

SteelGuard AI is a competition-project monorepo for single-image steel surface
inspection. The Streamlit frontend accepts one image, calls either its local
mock or the FastAPI backend, and displays the returned defect class, confidence
score, quality recommendation, and Grad-CAM explanation. The backend can use
the safe dummy adapter or an explicitly configured provisional model adapter.

The repository currently contains:

- a working single-page Streamlit frontend with upload, validation, preview,
  loading, result, error, retry, and reset states;
- a validated mock prediction service and configurable Requests API client;
- a FastAPI backend with contract-stable dummy and explicit real-model adapters;
- backend request validation, error responses, tests, and a Dockerfile;
- an in-process provisional YOLO11n adapter with checksum verification and
  Grad-CAM PNG data-URI generation;
- an API contract for the prediction endpoint;
- a contract-shaped mock response used by the frontend; and
- repository documentation for scope, flow, and ownership.

The frontend is presentation-only. It must never calculate or alter the
classification, confidence, Grad-CAM, or recommendation returned by the
backend.

## Current status

- The Streamlit frontend completes the one-image workflow with explicit mock
  AI output.
- Docker Compose defaults to the live frontend-to-backend HTTP path; isolated
  frontend development can still opt into the validated mock adapter.
- Frontend components, Pillow validation, response validation, errors, retry,
  and reset are implemented and covered by automated tests.
- The supplied provisional YOLO11n checkpoint is integrated behind
  `STEELGUARD_AI_MODE=model`; dummy mode remains the safe default.
- Phase 2 FE-to-dummy-BE `POST /predict` integration is reproducibly smoke-tested
  with `python scripts/phase2_smoke_test.py`.
- Live Grad-CAM generation is implemented using the recommended PNG data-URI
  transport; the demo recommendation policy is recorded, while final model
  evidence remains open.
- Docker Compose defines healthy backend and frontend services with adopted
  demo values of a 1 MiB upload limit and 2/30-second connect/read timeouts.

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

For a local FE-to-BE run outside Docker, use `STEELGUARD_USE_MOCK_API=false`,
`STEELGUARD_API_BASE_URL=http://localhost:8000`, connect/read timeouts of `2`
and `30`, and `STEELGUARD_MAX_UPLOAD_BYTES=1048576` before starting Streamlit.

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
<http://localhost:8000>. Compose uses the live frontend-to-backend path by
default while keeping the backend AI adapter in safe dummy mode. Backend
dummy/model selection is configured separately.

### Run the competition demo with the bundled model

Set the explicit model-mode configuration before starting Compose:

```powershell
$env:STEELGUARD_AI_MODE = "model"
$env:STEELGUARD_MODEL_PATH = "/app/ai/best.pt"
$env:STEELGUARD_CONFIDENCE_THRESHOLD = "0.25"
$env:STEELGUARD_RECOMMENDATION_MAP_JSON = '{"Crazing":"REJECT","Inclusion":"REJECT","Patches":"REWORK","Pitted Surface":"REJECT","Rolled-in Scale":"REWORK","Scratches":"REWORK"}'
$env:STEELGUARD_USE_MOCK_API = "false"
docker compose up --build
```

Then open <http://localhost:8501>. The bundled checkpoint is an existing
YOLO11n artifact supplied to the project and integrated and adapted during the
competition through checksum verification, fixed preprocessing and label
contracts, same-pass Grad-CAM, and the backend/frontend workflow. It is not
claimed as a checkpoint trained by this team during the competition. Its
original training run and final held-out evaluation metrics were not supplied,
so the repository identifies it as provisional instead of inventing evidence.

## Repository layout

```text
frontend/   Streamlit application, UI boundaries, styles, and API client boundary
backend/    FastAPI validation, adapter orchestration, tests, and Docker
ai/         Provisional model artifact, checksum, inference, Grad-CAM, and tests
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
