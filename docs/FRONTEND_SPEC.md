# Frontend Specification

## Purpose

The frontend is a Streamlit presentation client for one steel image and one
backend prediction. It owns user interaction and display state. It does not own
any inference or quality decision logic.

The repository foundation currently implements only the readiness page in
`frontend/app.py`. The modules below are documented placeholders for the next
frontend phase.

## Module responsibilities

| Module | Future responsibility |
| --- | --- |
| `app.py` | Compose page states, keep Streamlit session state, and coordinate components with the API client |
| `components/upload_section.py` | Render a single-file JPEG/PNG uploader and return the selected file |
| `components/image_preview.py` | Render the decoded selected image and basic non-inference metadata |
| `components/result_card.py` | Group the required backend prediction fields into one result section |
| `components/confidence.py` | Format the backend confidence as an accessible percentage |
| `components/recommendation.py` | Render the exact backend recommendation with text and visual status |
| `components/gradcam_view.py` | Resolve and display the backend Grad-CAM reference with explanatory labeling |
| `services/api_client.py` | Submit one multipart image, enforce timeout/status handling, and validate the response shape |
| `utils/image_validator.py` | Decode and check one selected JPEG/PNG for early user feedback |
| `styles/main.css` | Maintain project-specific visual tokens and lightweight Streamlit overrides |

Presentation components should receive data through parameters and should not
make HTTP calls. The API client should not render Streamlit elements.

## API client behavior

When implemented, the client will:

1. Read a base URL from `STEELGUARD_API_BASE_URL`, defaulting to
   `http://localhost:8000` for local development.
2. Submit one file in the `image` field to `POST /api/v1/predict` using
   Requests.
3. Apply an explicit connection/read timeout suitable for interactive use.
4. Reject non-success statuses, non-JSON bodies, and success bodies that do not
   satisfy [`API_CONTRACT.md`](API_CONTRACT.md).
5. Resolve a relative `gradcam_image` reference against the backend base URL.
6. Return normalized data or a typed client error to `app.py`; it must not
   calculate replacement values.

## Image validation

Client-side validation is for usability only. It should:

- accept exactly one user selection;
- allow JPEG and PNG formats;
- verify that Pillow can decode and load the image;
- normalize orientation for preview without changing the original upload
  bytes sent to the backend;
- produce a concise message for invalid content.

FastAPI must repeat authoritative validation. The frontend must not inspect
pixels for a defect, generate a heatmap, assign a label, or choose a
recommendation.

## State model

Use Streamlit session state only for the current interaction:

- selected image identity and preview;
- Idle, Ready, Analyzing, Success, or Error status;
- current validated backend result or current error.

Reset removes all request-specific state. Do not persist images or predictions
to a database, local history, analytics system, or automated log.

## Styling direction

- Keep a clean industrial visual language using the existing navy, blue,
  neutral surface, and border tokens.
- Prefer a focused single-column workflow over dashboard navigation.
- Keep custom CSS narrow and documented because Streamlit's generated markup
  can change between versions.
- Use text labels with status colors and retain adequate contrast.
- Do not add organization or institution branding to the competition UI.

## Frontend acceptance checklist

- One-image uploader and preview work for JPEG and PNG.
- Analyze calls only the configured backend endpoint and cannot double-submit.
- Every displayed inference field matches the received response.
- Invalid input, timeout, connection, server, and contract errors recover
  without a fabricated result.
- Reset allows a fresh image without retaining the prior prediction.
- The workflow remains usable without authentication, history, or dashboard
  navigation.
