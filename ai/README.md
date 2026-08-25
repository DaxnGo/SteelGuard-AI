# SteelGuard AI Inference Adapter

The AI package is imported by the existing FastAPI backend. It is not a second
HTTP service and does not expose another port.

## Current artifact status

The supplied `best.pt` artifact is a provisional Ultralytics YOLO11n detection
checkpoint with six labels. It is integrated so the team can test the complete
technical path, but it is **not documented as the final selected model** because
the repository does not include the dataset protocol, candidate comparison, or
evaluation results required by D-01 and D-02.

| Property | Recorded value |
| --- | --- |
| Task | Ultralytics detection |
| Base architecture | YOLO11n |
| Runtime | Ultralytics 8.4.127, PyTorch 2.12.1 CPU |
| Input | RGB, aspect-ratio-preserving resize and padding to 640 × 640 |
| Artifact size | 5,426,138 bytes |
| SHA-256 | `f33543468e7020ac291fc424fafc3b40555b2e45e206182bfb1bab9d1fa9baaf` |
| Artifact source/training run | Not supplied; AI owner follow-up required |
| Accuracy/precision/recall/F1/mAP | Not supplied; must not be inferred |

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
STEELGUARD_RECOMMENDATION_MAP_JSON={"Crazing":"REJECT","Inclusion":"REJECT","Patches":"REWORK","Pitted Surface":"REJECT","Rolled-in Scale":"REWORK","Scratches":"REWORK"}
```

`STEELGUARD_RECOMMENDATION_MAP_JSON` has no code default. The value above is the
approved competition MVP decision-support policy, not a production disposition
rule. Missing or invalid model-mode configuration fails startup and never falls
back to dummy output.

## Tests

Fast unit tests run without the heavy model runtime:

```powershell
python -m pytest ai/tests -q
```

`test_model_smoke.py` automatically exercises the bundled model and Grad-CAM
when Ultralytics is installed, including inside the backend Docker image.

## Remaining AI evidence

- Resolve dataset provenance, split, preprocessing, and augmentation under D-01.
- Record candidate-model evaluation and approve the final architecture under D-02.
- Rehearse the provisional CPU artifact on the approved demo hardware under D-06.
