# SteelGuard AI Inference Adapter

The AI package is imported by the existing FastAPI backend. It is not a second
HTTP service and does not expose another port.

## Current artifact status

The supplied `best.pt` artifact is a provisional Ultralytics YOLO11n detection
checkpoint with six labels. It is integrated so the team can test the complete
technical path, but it is **not documented as the final selected model** because
its original split manifest and run outputs were not supplied. The repository
now contains a clean seed-42 dataset protocol for a future retraining run, but it
must not be presented as the provenance of the current artifact.

| Property | Recorded value |
| --- | --- |
| Task | Ultralytics detection |
| Base architecture | YOLO11n |
| Runtime | Ultralytics 8.4.127, PyTorch 2.12.1 CPU |
| Input | RGB, aspect-ratio-preserving resize and padding to 640 × 640 |
| Artifact size | 5,426,138 bytes |
| SHA-256 | `f33543468e7020ac291fc424fafc3b40555b2e45e206182bfb1bab9d1fa9baaf` |
| Artifact source/training run | Embedded arguments exist; original split and run directory were not supplied |
| Held-out test metrics | Not supplied; embedded validation values are not test evidence |

The adapter verifies the sidecar checksum before loading the pickle-based model
and validates the exact checkpoint label order.

## Inference contract

`ai.inference.run_inference(image)` returns one complete backend-adapter result:

```python
{
    "class_name": "Scratches",
    "confidence": 0.942,
    "recommendation": "REWORK",
    "gradcam_image": "data:image/png;base64,...",
}
```

The provisional detector is adapted to the product's single-result contract by
selecting the highest class score from one forward pass. The same selected score
is backpropagated through the shared C2PSA feature layer to generate Grad-CAM.
The aligned overlay is returned as an in-memory PNG data URI; no uploads or
generated images are persisted.

## Required model-mode configuration

The backend defaults to the safe Phase 2 dummy adapter. Real inference is used
only when explicitly configured:

```env
STEELGUARD_AI_MODE=model
STEELGUARD_MODEL_PATH=/app/ai/best.pt
STEELGUARD_CONFIDENCE_THRESHOLD=0.25
STEELGUARD_RECOMMENDATION_MAP_JSON={...all six exact API labels...}
```

`STEELGUARD_RECOMMENDATION_MAP_JSON` has no default. D-03 requires the quality
owner to approve every `ACCEPT`, `REWORK`, or `REJECT` value. Missing or invalid
model-mode configuration fails startup and never falls back to dummy output.

## Tests

Fast unit tests run without the heavy model runtime:

```powershell
python -m pytest ai/tests -q
```

`test_model_smoke.py` automatically exercises the bundled model and Grad-CAM
when Ultralytics is installed, including inside the backend Docker image.

## Dataset, training, and evaluation

Run the reproducible pipeline from the repository root:

```powershell
python -m ai.train_eval_pipeline prepare --help
python -m ai.train_eval_pipeline train --help
python -m ai.train_eval_pipeline evaluate --help
```

Preparation requires the original NEU-DET `IMAGES` and `ANNOTATIONS` folders,
refuses a non-empty output directory, removes exact duplicates deterministically,
and generates a safe audit without committing dataset files. Evaluation writes
machine-readable overall and per-class metrics for the held-out test split.

See [`training_evaluation_report.md`](training_evaluation_report.md) for the
exact commands, verified dataset audit, embedded checkpoint metadata, model
selection status, and evidence gaps. Do not evaluate the bundled checkpoint on
the new split as if it were held out: its original training split is unknown.

## Technical benchmark

The benchmark uses the existing model runtime to record checkpoint metadata,
CPU/model startup, full class-plus-Grad-CAM latency, and process peak RSS without
requiring the training dataset:

```powershell
docker compose build backend
docker compose run --rm --no-deps backend python -m ai.benchmark --warmup 2 --runs 10
```

See [`TECHNICAL_EVIDENCE.md`](TECHNICAL_EVIDENCE.md) for the recorded demo-host
result, Grad-CAM target-layer validation, scope, and remaining evidence. The
synthetic benchmark is not a model-quality or accuracy test.

## Remaining AI evidence

- Train a fresh checkpoint from the committed dataset protocol and archive its
  exact environment/run metadata.
- Record held-out overall/per-class results, confusion matrix, reviewed failure
  examples, and a same-split candidate decision under D-02.
- Approve the recommendation mapping under D-03.
- Rehearse the provisional CPU artifact on the approved demo hardware under D-06.
