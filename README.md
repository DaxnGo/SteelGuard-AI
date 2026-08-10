# SteelGuard AI

Intelligent Steel Surface Defect Detection for Smart Manufacturing.

SteelGuard AI is a competition-project monorepo for single-image steel surface
inspection. The frontend MVP accepts one image, exercises the complete
interaction with mock AI data, and displays a defect class, confidence score,
quality recommendation, and an honest Grad-CAM placeholder.

The repository currently contains:

- a working single-page Streamlit frontend with upload, validation, preview,
  loading, result, error, retry, and reset states;
- a validated mock prediction service behind the future API client boundary;
- documented backend and AI boundaries;
- an API contract for the future prediction endpoint;
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
- The FastAPI backend and deep-learning implementation have not been created.
- Live `POST /predict` integration and generated Grad-CAM remain future work.
- Docker Compose currently runs only the frontend service.

## Quick start

Use Python 3.11 to match the frontend container.

### Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```

For POSIX shells, activate the environment with `source .venv/bin/activate`.
Then open <http://localhost:8501>.

Run the automated frontend tests from the repository root:

```powershell
cd frontend
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### Run with Docker Compose

```bash
docker compose up --build
```

The frontend is exposed at <http://localhost:8501>. A backend service will be
added after the FastAPI application and its Dockerfile exist.

## Repository layout

```text
frontend/   Streamlit application, UI boundaries, styles, and API client boundary
backend/    FastAPI guidance; no application code yet
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
