"""Development-only response scenarios for frontend contract and UI testing."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any


DEFECT_CLASSES = (
    "Crazing",
    "Inclusion",
    "Patches",
    "Pitted Surface",
    "Rolled-in Scale",
    "Scratches",
)
RECOMMENDATIONS = ("ACCEPT", "REWORK", "REJECT")
CONFIDENCE_VALUES = (0.51, 0.72, 0.88, 0.95, 0.999)


@dataclass(frozen=True)
class ResponseScenario:
    """One backend-response condition and its expected frontend outcome."""

    case_id: str
    label: str
    response: object | None
    expected_state: str
    expected_result: str
    service_error: str | None = None


def prediction_response(
    *,
    class_name: Any = "Scratches",
    confidence: Any = 0.95,
    recommendation: Any = "REWORK",
    gradcam_image: Any = "mock_gradcam.png",
) -> dict[str, Any]:
    """Build contract-shaped test data without deriving any AI field."""

    return {
        "success": True,
        "prediction": {
            "class_name": class_name,
            "confidence": confidence,
            "recommendation": recommendation,
            "gradcam_image": gradcam_image,
        },
    }


def build_valid_scenarios() -> tuple[ResponseScenario, ...]:
    """Return the complete 6 x 3 x 5 valid response Cartesian product."""

    scenarios: list[ResponseScenario] = []
    combinations = product(DEFECT_CLASSES, RECOMMENDATIONS, CONFIDENCE_VALUES)
    for index, (class_name, recommendation, confidence) in enumerate(
        combinations,
        start=1,
    ):
        case_id = f"VALID-{index:03d}"
        confidence_text = f"{confidence * 100:.1f}%"
        scenarios.append(
            ResponseScenario(
                case_id=case_id,
                label=(
                    f"{case_id} · {class_name} · {recommendation} · "
                    f"{confidence_text}"
                ),
                response=prediction_response(
                    class_name=class_name,
                    confidence=confidence,
                    recommendation=recommendation,
                ),
                expected_state="SUCCESS",
                expected_result=(
                    f"{class_name} | {confidence_text} | {recommendation}"
                ),
            )
        )
    return tuple(scenarios)


def build_invalid_scenarios() -> tuple[ResponseScenario, ...]:
    """Return invalid-contract and normalized service-failure conditions."""

    missing_prediction = {"success": True}

    missing_class_name = prediction_response()
    del missing_class_name["prediction"]["class_name"]

    missing_confidence = prediction_response()
    del missing_confidence["prediction"]["confidence"]

    missing_recommendation = prediction_response()
    del missing_recommendation["prediction"]["recommendation"]

    missing_gradcam = prediction_response()
    del missing_gradcam["prediction"]["gradcam_image"]

    return (
        ResponseScenario(
            case_id="INVALID-CONFIDENCE-NEGATIVE",
            label="Negative confidence",
            response=prediction_response(confidence=-0.1),
            expected_state="ERROR",
            expected_result="The AI service returned an invalid confidence score.",
        ),
        ResponseScenario(
            case_id="INVALID-CONFIDENCE-ABOVE-ONE",
            label="Confidence greater than one",
            response=prediction_response(confidence=1.01),
            expected_state="ERROR",
            expected_result="The AI service returned an invalid confidence score.",
        ),
        ResponseScenario(
            case_id="INVALID-CONFIDENCE-NULL",
            label="Null confidence",
            response=prediction_response(confidence=None),
            expected_state="ERROR",
            expected_result="The AI service returned an invalid confidence score.",
        ),
        ResponseScenario(
            case_id="INVALID-CONFIDENCE-STRING",
            label="String confidence",
            response=prediction_response(confidence="0.95"),
            expected_state="ERROR",
            expected_result="The AI service returned an invalid confidence score.",
        ),
        ResponseScenario(
            case_id="ERROR-SUCCESS-FALSE",
            label="success is false",
            response={
                "success": False,
                "prediction": prediction_response()["prediction"],
            },
            expected_state="ERROR",
            expected_result="The AI service returned an invalid response.",
        ),
        ResponseScenario(
            case_id="ERROR-MISSING-PREDICTION",
            label="Missing prediction",
            response=missing_prediction,
            expected_state="ERROR",
            expected_result="The AI service response is missing prediction data.",
        ),
        ResponseScenario(
            case_id="ERROR-MISSING-CLASS-NAME",
            label="Missing class_name",
            response=missing_class_name,
            expected_state="ERROR",
            expected_result="The AI service response is incomplete.",
        ),
        ResponseScenario(
            case_id="ERROR-MISSING-CONFIDENCE",
            label="Missing confidence",
            response=missing_confidence,
            expected_state="ERROR",
            expected_result="The AI service response is incomplete.",
        ),
        ResponseScenario(
            case_id="ERROR-MISSING-RECOMMENDATION",
            label="Missing recommendation",
            response=missing_recommendation,
            expected_state="ERROR",
            expected_result="The AI service response is incomplete.",
        ),
        ResponseScenario(
            case_id="ERROR-MISSING-GRADCAM",
            label="Missing gradcam_image",
            response=missing_gradcam,
            expected_state="ERROR",
            expected_result="The AI service response is incomplete.",
        ),
        ResponseScenario(
            case_id="ERROR-MALFORMED-RESPONSE",
            label="Malformed non-object response",
            response="{malformed-response",
            expected_state="ERROR",
            expected_result="The AI service returned an invalid response.",
        ),
        ResponseScenario(
            case_id="ERROR-TIMEOUT",
            label="Simulated timeout",
            response=None,
            expected_state="ERROR",
            expected_result="The AI service timed out. Please try again.",
            service_error="The AI service timed out. Please try again.",
        ),
        ResponseScenario(
            case_id="ERROR-SERVICE-UNAVAILABLE",
            label="Simulated service unavailable",
            response=None,
            expected_state="ERROR",
            expected_result=(
                "The AI service is temporarily unavailable. Please try again."
            ),
            service_error=(
                "The AI service is temporarily unavailable. Please try again."
            ),
        ),
    )


VALID_SCENARIOS = build_valid_scenarios()
INVALID_SCENARIOS = build_invalid_scenarios()
ALL_SCENARIOS = VALID_SCENARIOS + INVALID_SCENARIOS
