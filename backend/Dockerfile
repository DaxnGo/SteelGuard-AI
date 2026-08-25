FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=appuser:appgroup backend/app ./app
COPY --chown=appuser:appgroup ai ./ai
RUN mkdir -p "$YOLO_CONFIG_DIR/Ultralytics" \
    && chown -R appuser:appgroup "$YOLO_CONFIG_DIR"

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
