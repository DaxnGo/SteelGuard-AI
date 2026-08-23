# SteelGuard AI Backend

FastAPI backend for SteelGuard AI — Intelligent Steel Surface Defect Detection. Phase 1 provides a stable REST API with a dummy prediction response so the Streamlit frontend can integrate before the real AI model is available. See `docs/API_CONTRACT.md` for the full API specification.

## Requirements

- Python 3.10+
- pip

## Setup

### 1. Create virtual environment

```
python -m venv .venv
```

Activate:

Windows:

```
.venv\Scripts\activate
```

Linux/macOS:

```
source .venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

## Run Development Server

```
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`.

Interactive API docs: `http://localhost:8000/docs`

## API Endpoints

### GET /health

```
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok"
}
```

### POST /predict

```
curl -X POST http://localhost:8000/predict -F "file=@steel_surface.jpg"
```

Accepts a single JPEG or PNG image. Full request/response schema, error codes, and status codes are defined in `docs/API_CONTRACT.md`.

## Run Tests

```
pytest
```

## Docker

### Build

```
docker build -t steelguard-backend .
```

### Run

```
docker run -p 8000:8000 steelguard-backend
```

Verify:

```
curl http://localhost:8000/health
```

## CORS

CORS is enabled for local development to allow requests from the Streamlit frontend at `http://localhost:8501`. See `app/main.py`.

## Environment Configuration

No environment variables are required for Phase 1. No database, authentication, or background jobs are used.

## Project Structure

```
backend/
├── app/
│   ├── main.py
│   ├── routes/
│   │   └── predict.py
│   ├── schemas/
│   │   └── prediction.py
│   ├── services/
│   ├── utils/
│   │   └── image_validation.py
├── tests/
│   ├── test_health.py
│   └── test_predict.py
├── docs/
│   └── API_CONTRACT.md
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```
