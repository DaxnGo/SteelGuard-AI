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

| Capability | Foundation status | MVP owner |
| --- | --- | --- |
| Streamlit startup page | Available | Frontend |
| Single JPEG/PNG selection | Planned | Frontend |
| Local image preview | Planned | Frontend |
| One prediction API request | Planned | Frontend and backend |
| Six-class inference | Planned | AI |
| Confidence output | Planned | AI |
| Grad-CAM output | Planned | AI and backend |
| ACCEPT/REWORK/REJECT recommendation | Planned | AI |
| Recoverable error and reset states | Planned | Frontend |
| Contract-shaped mock response | Available | Shared |

"Available" means present in the repository foundation. "Planned" means
specified but intentionally not implemented yet.

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
- Mock data may support frontend development, but the demo must make mock and
  live modes unambiguous. The foundation does not yet implement either mode.
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
