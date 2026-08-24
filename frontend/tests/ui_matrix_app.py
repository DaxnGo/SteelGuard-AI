"""Development-only Streamlit harness for visual response-matrix inspection.

Run with:
    streamlit run frontend/tests/ui_matrix_app.py

This module is not imported by the production application.
"""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from pathlib import Path
import sys

from PIL import Image
import streamlit as st


FRONTEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(FRONTEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIRECTORY))

import app as production_app  # noqa: E402
from components.image_preview import render_image_preview  # noqa: E402
from services.api_client import (  # noqa: E402
    PredictionServiceError,
    validate_prediction_response,
)
from tests.scenario_matrix import (  # noqa: E402
    INVALID_SCENARIOS,
    VALID_SCENARIOS,
    ResponseScenario,
)
from utils.image_validator import ValidatedImage, validate_image_bytes  # noqa: E402


def build_test_image() -> ValidatedImage:
    """Create a neutral local image fixture for layout inspection only."""

    encoded_image = BytesIO()
    Image.new("RGB", (640, 360), color=(148, 163, 184)).save(
        encoded_image,
        format="PNG",
    )
    return validate_image_bytes("qa-steel-surface.png", encoded_image.getvalue())


def evaluate_scenario(scenario: ResponseScenario) -> dict:
    """Return validated test data or the normalized simulated service error."""

    if scenario.service_error is not None:
        raise PredictionServiceError(scenario.service_error)
    return validate_prediction_response(deepcopy(scenario.response))


def render_scenario(scenario: ResponseScenario, image: ValidatedImage) -> None:
    """Render the exact production success or error presentation boundary."""

    try:
        response = evaluate_scenario(scenario)
    except PredictionServiceError as exc:
        st.session_state[production_app.STATE_KEY] = production_app.ERROR
        st.session_state[production_app.IMAGE_KEY] = image
        st.session_state[production_app.PREDICTION_KEY] = None
        st.session_state[production_app.ERROR_KEY] = str(exc)
        st.session_state[production_app.ERROR_RETRYABLE_KEY] = exc.retryable
        st.session_state[production_app.ERROR_CATEGORY_KEY] = exc.category
        render_image_preview(image)
        production_app.render_error_state()
        return

    st.session_state[production_app.STATE_KEY] = production_app.SUCCESS
    st.session_state[production_app.IMAGE_KEY] = image
    st.session_state[production_app.PREDICTION_KEY] = response["prediction"]
    st.session_state[production_app.ERROR_KEY] = None
    st.session_state[production_app.ERROR_RETRYABLE_KEY] = False
    st.session_state[production_app.ERROR_CATEGORY_KEY] = None
    production_app.render_success_state(image, response["prediction"])


def main() -> None:
    """Render a non-production selector and the production result components."""

    st.set_page_config(
        page_title="SteelGuard AI Frontend QA Matrix",
        page_icon="SG",
        layout="centered",
    )
    production_app.load_stylesheet()
    production_app.initialize_session_state()

    st.sidebar.title("Frontend QA Matrix")
    st.sidebar.warning(
        "Development/testing only. This selector is not part of the production app."
    )
    group_name = st.sidebar.radio(
        "Scenario group",
        ("Valid responses", "Invalid and error responses"),
    )
    scenarios = VALID_SCENARIOS if group_name == "Valid responses" else INVALID_SCENARIOS
    scenarios_by_id = {scenario.case_id: scenario for scenario in scenarios}
    selected_id = st.sidebar.selectbox(
        "Response scenario",
        options=tuple(scenarios_by_id),
        format_func=lambda case_id: scenarios_by_id[case_id].label,
        key=f"qa-scenario-{group_name}",
    )
    selected_scenario = scenarios_by_id[selected_id]
    st.sidebar.caption(f"Expected UI state: {selected_scenario.expected_state}")
    st.sidebar.code(selected_scenario.expected_result, language=None)

    production_app.render_header()
    render_scenario(selected_scenario, build_test_image())


if __name__ == "__main__":
    main()
