# SteelGuard AI Frontend Response Test Matrix

> **Purpose:** Development and testing only
> **Production impact:** None. The production Streamlit interface does not
> import or expose the QA scenario selector.

## Test mechanism

The response matrix is defined in
`frontend/tests/scenario_matrix.py`. It generates every valid Cartesian
combination:

```text
6 defect classes × 3 recommendations × 5 confidence values = 90 valid cases
```

It also defines 13 invalid-contract and simulated service-error cases. No case
derives a recommendation from confidence, performs inference, or generates a
Grad-CAM image.

For visual inspection, run the isolated test harness:

```powershell
streamlit run frontend/tests/ui_matrix_app.py
```

The harness uses the production result, confidence, recommendation, Grad-CAM,
preview, and error renderers. Its selector exists only under `frontend/tests/`
and is not referenced by `frontend/app.py`.

Run the automated matrix tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover `
  -s frontend/tests `
  -t frontend `
  -p "test_response_matrix.py" `
  -v
```

## Valid response matrix

Each range below covers the Cartesian product of all three recommendations and
all five confidence values for the named class. Every case uses
`gradcam_image: "mock_gradcam.png"`.

| Test Case | Input | Expected UI State | Expected Result |
| --- | --- | --- | --- |
| `VALID-001`–`VALID-015` | `class_name=Crazing`; recommendation ∈ `{ACCEPT, REWORK, REJECT}`; confidence ∈ `{0.51, 0.72, 0.88, 0.95, 0.999}` | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |
| `VALID-016`–`VALID-030` | `class_name=Inclusion`; same recommendation and confidence Cartesian product | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |
| `VALID-031`–`VALID-045` | `class_name=Patches`; same recommendation and confidence Cartesian product | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |
| `VALID-046`–`VALID-060` | `class_name=Pitted Surface`; same recommendation and confidence Cartesian product | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |
| `VALID-061`–`VALID-075` | `class_name=Rolled-in Scale`; same recommendation and confidence Cartesian product | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |
| `VALID-076`–`VALID-090` | `class_name=Scratches`; same recommendation and confidence Cartesian product | `SUCCESS` | Exact class, unchanged confidence formatted as a percentage, exact recommendation, and Grad-CAM area |

### Confidence preservation

| Test Case | Input | Expected UI State | Expected Result |
| --- | --- | --- | --- |
| `CONFIDENCE-051` | `confidence=0.51` | `SUCCESS` | Stored value remains `0.51`; UI displays `51.0%` |
| `CONFIDENCE-072` | `confidence=0.72` | `SUCCESS` | Stored value remains `0.72`; UI displays `72.0%` |
| `CONFIDENCE-088` | `confidence=0.88` | `SUCCESS` | Stored value remains `0.88`; UI displays `88.0%` |
| `CONFIDENCE-095` | `confidence=0.95` | `SUCCESS` | Stored value remains `0.95`; UI displays `95.0%` |
| `CONFIDENCE-0999` | `confidence=0.999` | `SUCCESS` | Stored value remains `0.999`; UI displays `99.9%` |

Formatting a confidence value for display must not change the normalized decimal
held by the frontend and must never affect class or recommendation.

## Invalid and error matrix

All cases below must render `Inspection failed.`, show no partial inspection
result, and avoid an uncaught exception.

| Test Case | Input | Expected UI State | Expected Result |
| --- | --- | --- | --- |
| `INVALID-CONFIDENCE-NEGATIVE` | `confidence=-0.1` | `ERROR` | `The AI service returned an invalid confidence score.` |
| `INVALID-CONFIDENCE-ABOVE-ONE` | `confidence=1.01` | `ERROR` | `The AI service returned an invalid confidence score.` |
| `INVALID-CONFIDENCE-NULL` | `confidence=null` | `ERROR` | `The AI service returned an invalid confidence score.` |
| `INVALID-CONFIDENCE-STRING` | `confidence="0.95"` | `ERROR` | `The AI service returned an invalid confidence score.` |
| `ERROR-SUCCESS-FALSE` | `success=false` | `ERROR` | `The AI service returned an invalid response.` |
| `ERROR-MISSING-PREDICTION` | Missing `prediction` object | `ERROR` | `The AI service response is missing prediction data.` |
| `ERROR-MISSING-CLASS-NAME` | Missing `prediction.class_name` | `ERROR` | `The AI service response is incomplete.` |
| `ERROR-MISSING-CONFIDENCE` | Missing `prediction.confidence` | `ERROR` | `The AI service response is incomplete.` |
| `ERROR-MISSING-RECOMMENDATION` | Missing `prediction.recommendation` | `ERROR` | `The AI service response is incomplete.` |
| `ERROR-MISSING-GRADCAM` | Missing `prediction.gradcam_image` | `ERROR` | `The AI service response is incomplete.` |
| `ERROR-MALFORMED-RESPONSE` | Non-object malformed response | `ERROR` | `The AI service returned an invalid response.` |
| `ERROR-TIMEOUT` | Simulated normalized timeout | `ERROR` | `The AI service timed out. Please try again.` |
| `ERROR-SERVICE-UNAVAILABLE` | Simulated normalized unavailable service | `ERROR` | `The AI service is temporarily unavailable. Please try again.` |

## Pass criteria

- All 90 valid cases render `SUCCESS` with exact backend-supplied values.
- All five confidence values remain numerically unchanged after validation.
- All 13 invalid/error cases render `ERROR` without a partial result.
- No scenario calculates a class, confidence, recommendation, or Grad-CAM.
- The production application contains no QA selector or scenario import.
