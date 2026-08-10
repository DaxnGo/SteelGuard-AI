# AI Foundation

The AI subsystem will perform single-image steel surface defect inference for
the FastAPI backend. The deep-learning framework and model architecture remain
owned by the AI team. This directory intentionally contains no model or
inference implementation in the foundation phase.

## Required responsibilities

For one decoded steel image, the AI team must provide:

- documented preprocessing, including color space, resize/crop behavior, and
  normalization expected by the trained model;
- one class label from the exact supported label set;
- a confidence value from `0.0` through `1.0`, with its interpretation and any
  calibration documented;
- a Grad-CAM visualization aligned with the submitted image;
- one quality recommendation: `ACCEPT`, `REWORK`, or `REJECT`;
- explicit exceptions or failure results for invalid input, unavailable model
  artifacts, and inference failures.

Supported labels:

1. Crazing
2. Inclusion
3. Patches
4. Pitted Surface
5. Rolled-in Scale
6. Scratches

## Backend-facing adapter

Expose a framework-independent Python boundary that accepts one decoded RGB
image and returns one result with these logical fields:

```text
predict(image) -> {
    class_name,
    confidence,
    recommendation,
    gradcam_artifact
}
```

The concrete model can use any deep-learning framework, but framework-specific
tensors must not leak into the FastAPI response layer. Load the model once per
backend process where practical; do not reload it for every prediction.

The AI team owns label-index mapping and recommendation policy. The backend
serializes the returned values, while the frontend only displays them.

## Integration evidence to provide

- Model artifact version and checksum.
- Reproducible environment and dependency requirements.
- Preprocessing and label-map documentation.
- Unit tests for output types, label membership, confidence bounds, and
  Grad-CAM generation.
- Representative validation for all six classes and documented known limits.
- Expected inference latency and hardware assumptions for deployment planning.

## Out of scope for the preliminary MVP

Do not expose an HTTP API from this subsystem, implement batch inference,
persist user images or results, or add frontend decision logic.
