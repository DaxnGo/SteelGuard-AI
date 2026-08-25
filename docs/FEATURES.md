# Features

## Core interaction

The preliminary MVP contains one user journey:

```text
Upload ONE steel image
-> Preview image
-> Analyze
-> AI inference
-> Defect classification
-> Confidence score
-> Grad-CAM
-> Quality recommendation
-> Analyze another image
```

## Feature inventory

| Capability | Current status | MVP owner |
| --- | --- | --- |
| Streamlit single-page inspection UI | Available | Frontend |
| Single JPEG/PNG selection | Available | Frontend |
| Local validation and image preview | Available | Frontend |
| One mock prediction service call | Available | Frontend |
| One live `POST /predict` request | Available | Frontend and backend |
| Six-class inference | Provisional; evidence pending | AI |
| Six-class result presentation | Available | Frontend |
| Confidence presentation | Available | Frontend |
| Generated Grad-CAM output | Provisional PNG data URI available | AI and backend |
| Honest Grad-CAM placeholder | Available | Frontend |
| Recommendation presentation | Available | Frontend |
| Recommendation logic | Demo policy approved; configuration-gated | AI, backend, and product |
| Recoverable error, retry, and reset states | Available | Frontend |
| Contract-shaped mock response | Available | Shared |

"Available" means implemented in the repository. "Provisional" means the
technical path works but is not final model-quality evidence or production
approval. "Planned" means specified but intentionally not implemented yet.

## Supported defect classes

The class label is case-sensitive and must be one of:

1. `Crazing`
2. `Inclusion`
3. `Patches`
4. `Pitted Surface`
5. `Rolled-in Scale`
6. `Scratches`

## Quality recommendations

- `ACCEPT`
- `REWORK`
- `REJECT`

Recommendation policy belongs to the AI subsystem. The backend transports the
value, and the frontend presents it without applying thresholds or remapping
labels.

## Result integrity rules

- Classification, confidence, recommendation, and Grad-CAM must come from the
  same backend prediction response.
- Client-side validation may check file type and readability for usability but
  is never a substitute for backend validation.
- Mock mode is implemented for independent frontend development and is visibly
  identified in the page. A live request must never silently fall back to it.
- An error must never fall back to a plausible-looking prediction.

## Explicitly out of scope

- Authentication, login, registration, or user accounts
- Inspection history or saved reports
- Advanced analytics dashboards
- Automated image or prediction logging
- Background jobs or task queues
- Distributed databases or storage systems
- Batch inference
- Multiple-image upload or inference
- Frontend classification, confidence, Grad-CAM, or recommendation logic
