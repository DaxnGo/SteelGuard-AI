# NEU-DET Steel Surface Defect Detection API

Pipeline inferensi YOLOv8 untuk deteksi cacat permukaan baja. Mendukung 6 jenis cacat: **crazing**, **inclusion**, **patches**, **pitted_surface**, **rolled-in_scale**, **scratches**.

## Quick Start

```bash
# Build & run
docker compose up --build

# API tersedia di http://localhost:8000
# Dokumentasi Swagger di http://localhost:8000/docs
```

## API Endpoints

### `GET /health`
Health check — status API dan model.

```bash
curl http://localhost:8000/health
```

### `POST /predict`
Deteksi cacat pada gambar. Mengembalikan JSON dengan bounding box, kelas, dan confidence.

```bash
curl -X POST http://localhost:8000/predict \
  -F "file=@path/to/image.jpg"
```

**Response:**
```json
{
  "success": true,
  "detections": [
    {
      "class_id": 5,
      "class_name": "scratches",
      "confidence": 0.92,
      "bbox": {
        "x_min": 10.5,
        "y_min": 20.3,
        "x_max": 180.0,
        "y_max": 190.7
      }
    }
  ],
  "count": 1,
  "inference_time_ms": 45.2,
  "image_width": 200,
  "image_height": 200
}
```

### `POST /predict/annotated`
Deteksi cacat dan mengembalikan gambar dengan bounding box yang digambar.

```bash
curl -X POST http://localhost:8000/predict/annotated \
  -F "file=@path/to/image.jpg" \
  --output result.jpg
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_PATH` | `/app/model/best.pt` | Path ke model YOLOv8 |
| `CONF_THRESHOLD` | `0.25` | Minimum confidence score |
| `IOU_THRESHOLD` | `0.45` | IoU threshold untuk NMS |

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI endpoints
│   ├── inference.py     # YOLOv8 model engine
│   └── schemas.py       # Pydantic response models
├── best.pt              # Trained YOLOv8 model
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Supported Image Formats

JPEG, PNG, BMP, TIFF
