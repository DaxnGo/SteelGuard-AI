# Provisional AI Technical Evidence

This document records reproducible properties of the bundled checkpoint and
adapter. It is technical evidence only. Dataset provenance, held-out accuracy,
candidate comparison, calibration, and recommendation approval still require
the AI and quality owners.

## Verified checkpoint metadata

| Property | Verified value |
| --- | --- |
| Artifact | `ai/best.pt` |
| Artifact size | 5,426,138 bytes |
| SHA-256 | `f33543468e7020ac291fc424fafc3b40555b2e45e206182bfb1bab9d1fa9baaf` |
| Checksum sidecar | Matches `ai/best.pt.sha256` |
| Task/runtime | Ultralytics detection, YOLO11n |
| Runtime versions | Python 3.11.16, PyTorch 2.12.1+cpu, Ultralytics 8.4.127 |
| Input | RGB, aspect-ratio-preserving letterbox to 640 x 640, padding value 114 |
| Checkpoint labels | `crazing`, `inclusion`, `patches`, `pitted_surface`, `rolled-in_scale`, `scratches` |
| API labels | `Crazing`, `Inclusion`, `Patches`, `Pitted Surface`, `Rolled-in Scale`, `Scratches` |

The backend verifies the checksum and exact label order before model mode can
start. The confidence threshold is deployment configuration, not a model metric;
the safe code default is `0.25` and the benchmark below deliberately uses `0.0`
so a deterministic synthetic input can exercise the full path.

## Same-pass Grad-CAM validation

`ModelEngine.predict()` registers a forward hook on layer index 10 (`C2PSA`),
the shared feature layer immediately before the first `Upsample` at index 11.
One model forward pass produces the raw detection tensor. The adapter selects
one class score from that tensor, calls backward on that same score, and combines
the captured activation and its gradient into the Grad-CAM heatmap. It does not
run a second prediction to generate the explanation.

The model smoke test verifies that the bundled checkpoint produces a supported
class, finite confidence, and a decodable PNG data URI from this path.

## Reproducible CPU benchmark

Run the benchmark in the backend image:

```powershell
docker compose build backend
docker compose run --rm --no-deps backend python -m ai.benchmark --warmup 2 --runs 10
```

Recorded on 2026-08-25 using Docker Desktop/WSL2:

| Property | Result |
| --- | --- |
| CPU | Intel Core i3-7020U at 2.30 GHz, 4 logical CPUs |
| Process peak RSS | 575.59 MiB |
| Model/checksum startup | 3,524.11 ms |
| Measured runs | 10 after 2 warmups |
| Minimum | 510.45 ms |
| Mean | 614.59 ms |
| Median | 571.66 ms |
| P95 | 764.44 ms |
| Maximum | 798.85 ms |

Each latency sample includes preprocessing, one CPU forward/backward pass, class
selection, and Grad-CAM construction. It excludes model startup, which is
reported separately. The input was a deterministic synthetic 640 x 640 RGB
texture. Its returned class and confidence are not accuracy evidence and must
not be used as a quality claim.

Use `--image <authorized-image-path>` to measure a representative image. Record
that image's provenance outside Git when it cannot legally be redistributed.

## Evidence still required from the AI/domain owners

- Dataset source, version, license, class counts, and authorized access method.
- Frozen train/validation/test manifests, random seed, and duplicate/leakage audit.
- Exact training and evaluation commands/configuration that produced `best.pt`.
- Held-out precision, recall, F1, mAP, per-class results, confusion matrix,
  calibration analysis, and representative failure cases.
- Evidence comparing YOLO11n with the evaluated alternatives and the approved
  selection criteria.
- A quality-owner-approved class-to-`ACCEPT`/`REWORK`/`REJECT` mapping.

Until those items arrive, the checkpoint remains provisional and the application
must retain safe mock/dummy defaults.
