# SteelGuard AI Backend

FastAPI backend for SteelGuard AI. Phase 1 provides the contract-shaped dummy
prediction API so the Streamlit frontend can integrate before the real AI model
is available.

The shared HTTP contract is documented in
[`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md). The backend-specific copy is
also kept in [`backend/docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

## Requirements

- Python 3.10+
- pip

## Local setup

From the repository root:

```powershell
python -m venv .venv-backend
.\\.venv-backend\\Scripts\\Activate.ps1
python -m pip install -r backend/requirements.txt
```

Run the API from the repository root:

```powershell
uvicorn app.main:app --app-dir backend --reload --port 8000
```

The API is available at `http://localhost:8000` and Swagger UI at
`http://localhost:8000/docs`.

Set `STEELGUARD_MAX_UPLOAD_BYTES` to the approved positive D-04 byte limit in
the target environment. When configured, `/predict` rejects larger uploads
with `413 FILE_TOO_LARGE`. The final numeric limit remains a team decision.

## Endpoints

### `GET /health`

Returns `{ "status": "ok" }`.

### `POST /predict`

Accepts one multipart field named `file` containing a validated JPEG or PNG.
Phase 1 returns the dummy prediction with `gradcam_image: null`.

Example:

```powershell
curl.exe -X POST http://localhost:8000/predict -F "file=@steel_surface.jpg"
```

## Tests

From the repository root:

```powershell
python -m pytest backend/tests -q
```

## Docker

```powershell
docker build -f backend/Dockerfile -t steelguard-backend backend
docker run -p 8000:8000 steelguard-backend
```

The backend enables CORS for the local Streamlit origin at
`http://localhost:8501`. Authentication, history, analytics, batch inference,
and persistent storage are outside the MVP.

## Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── routes/predict.py
│   ├── schemas/prediction.py
│   ├── services/
│   └── utils/image_validation.py
├── tests/
├── docs/API_CONTRACT.md
├── requirements.txt
└── Dockerfile
```
