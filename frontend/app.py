"""SteelGuard AI Streamlit frontend for one-image mock inspection."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

import streamlit as st

from components.gradcam_view import render_gradcam_view
from components.image_preview import render_image_preview
from components.result_card import render_result_card
from components.upload_section import render_upload_section
from services.api_client import (
    PredictionServiceError,
    get_prediction_source_label,
    predict_image,
)
from utils.image_validator import (
    ImageValidationError,
    UploadLimitConfigurationError,
    ValidatedImage,
    validate_uploaded_image,
)


APP_DIRECTORY = Path(__file__).resolve().parent
STYLESHEET_PATH = APP_DIRECTORY / "styles" / "main.css"

EMPTY = "EMPTY"
IMAGE_SELECTED = "IMAGE_SELECTED"
ANALYZING = "ANALYZING"
SUCCESS = "SUCCESS"
ERROR = "ERROR"

STATE_KEY = "inspection_state"
IMAGE_KEY = "selected_image"
SIGNATURE_KEY = "selected_signature"
PREDICTION_KEY = "prediction"
ERROR_KEY = "inspection_error"
ERROR_RETRYABLE_KEY = "inspection_error_retryable"
ERROR_CATEGORY_KEY = "inspection_error_category"
UPLOADER_VERSION_KEY = "uploader_version"


def load_stylesheet() -> None:
    """Load the repository-owned stylesheet when it is available."""

    if STYLESHEET_PATH.is_file():
        css = STYLESHEET_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def initialize_session_state() -> None:
    """Initialize state for one independent inspection interaction."""

    defaults: dict[str, Any] = {
        STATE_KEY: EMPTY,
        IMAGE_KEY: None,
        SIGNATURE_KEY: None,
        PREDICTION_KEY: None,
        ERROR_KEY: None,
        ERROR_RETRYABLE_KEY: False,
        ERROR_CATEGORY_KEY: None,
        UPLOADER_VERSION_KEY: 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header() -> None:
    """Render project-only branding and MVP context."""

    source_label = get_prediction_source_label()
    st.markdown(
        '<a class="skip-link" href="#steel-surface-inspection">'
        "Skip to inspection</a>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="brand-kicker">INDUSTRIAL VISION INSPECTION</p>',
        unsafe_allow_html=True,
    )
    st.title("SteelGuard AI")
    st.markdown(
        '<p class="hero-subtitle">Intelligent Steel Surface Defect Detection</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="system-status" role="status" '
        f'aria-label="System status: {source_label.lower()}, '
        'single-image inspection">'
        '<span class="system-status-dot" aria-hidden="true"></span>'
        f"<strong>{source_label}</strong>"
        '<span class="system-status-separator" aria-hidden="true"></span>'
        '<span>Single-image inspection</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def selection_signature(uploaded_file: Any) -> str:
    """Return a stable identity for the current browser upload."""

    file_bytes = uploaded_file.getvalue()
    return f"{uploaded_file.name}:{len(file_bytes)}:{sha256(file_bytes).hexdigest()}"


def synchronize_selection(uploaded_file: Any | None) -> None:
    """Validate a new uploader value and synchronize the interaction state."""

    if uploaded_file is None:
        if (
            st.session_state[SIGNATURE_KEY] is not None
            and st.session_state[STATE_KEY] not in {SUCCESS, ANALYZING}
        ):
            clear_interaction(advance_uploader=False)
        return

    try:
        signature = selection_signature(uploaded_file)
    except (AttributeError, OSError, ValueError):
        signature = "unreadable-upload"

    if signature == st.session_state[SIGNATURE_KEY]:
        return

    st.session_state[SIGNATURE_KEY] = signature
    st.session_state[PREDICTION_KEY] = None
    st.session_state[ERROR_KEY] = None
    st.session_state[ERROR_RETRYABLE_KEY] = False
    st.session_state[ERROR_CATEGORY_KEY] = None

    try:
        st.session_state[IMAGE_KEY] = validate_uploaded_image(uploaded_file)
        st.session_state[STATE_KEY] = IMAGE_SELECTED
    except ImageValidationError as exc:
        st.session_state[IMAGE_KEY] = None
        st.session_state[ERROR_KEY] = str(exc)
        st.session_state[ERROR_RETRYABLE_KEY] = False
        st.session_state[ERROR_CATEGORY_KEY] = (
            "configuration"
            if isinstance(exc, UploadLimitConfigurationError)
            else "request"
        )
        st.session_state[STATE_KEY] = ERROR


def begin_analysis() -> None:
    """Enter ANALYZING before the next rerun invokes the mock service."""

    image = st.session_state[IMAGE_KEY]
    if not isinstance(image, ValidatedImage):
        st.session_state[ERROR_KEY] = "Select a valid image before starting inspection."
        st.session_state[ERROR_RETRYABLE_KEY] = False
        st.session_state[ERROR_CATEGORY_KEY] = "request"
        st.session_state[STATE_KEY] = ERROR
        return

    st.session_state[STATE_KEY] = ANALYZING
    st.session_state[PREDICTION_KEY] = None
    st.session_state[ERROR_KEY] = None
    st.session_state[ERROR_RETRYABLE_KEY] = False
    st.session_state[ERROR_CATEGORY_KEY] = None


def complete_analysis(image: ValidatedImage) -> None:
    """Run exactly one configured prediction and move to SUCCESS or ERROR."""

    try:
        with st.spinner("Analyzing steel surface…"):
            st.caption("Running AI inference…")
            response = predict_image(image)
        st.session_state[PREDICTION_KEY] = response["prediction"]
        st.session_state[ERROR_CATEGORY_KEY] = None
        st.session_state[STATE_KEY] = SUCCESS
    except PredictionServiceError as exc:
        st.session_state[ERROR_KEY] = str(exc)
        st.session_state[ERROR_RETRYABLE_KEY] = exc.retryable
        st.session_state[ERROR_CATEGORY_KEY] = exc.category
        st.session_state[STATE_KEY] = ERROR
    except Exception:
        st.session_state[ERROR_KEY] = (
            "The AI service could not process this image. Please try again."
        )
        st.session_state[ERROR_RETRYABLE_KEY] = True
        st.session_state[ERROR_CATEGORY_KEY] = "service"
        st.session_state[STATE_KEY] = ERROR

    st.rerun()


def clear_interaction(*, advance_uploader: bool = True) -> None:
    """Clear request-specific state without retaining a prior result."""

    st.session_state[STATE_KEY] = EMPTY
    st.session_state[IMAGE_KEY] = None
    st.session_state[SIGNATURE_KEY] = None
    st.session_state[PREDICTION_KEY] = None
    st.session_state[ERROR_KEY] = None
    st.session_state[ERROR_RETRYABLE_KEY] = False
    st.session_state[ERROR_CATEGORY_KEY] = None
    if advance_uploader:
        st.session_state[UPLOADER_VERSION_KEY] += 1


def reset_and_rerun() -> None:
    """Reset the interaction and render a fresh uploader."""

    clear_interaction()
    st.rerun()


def render_error_state() -> None:
    """Render a safe error and only the recovery actions that apply."""

    st.error("Inspection failed.")
    st.write(
        st.session_state[ERROR_KEY]
        or "The AI service could not process this image. Please try again."
    )

    image = st.session_state[IMAGE_KEY]
    retryable = st.session_state[ERROR_RETRYABLE_KEY]
    category = st.session_state[ERROR_CATEGORY_KEY]
    if category == "configuration":
        st.info(
            "Contact the system administrator to correct the live API settings, "
            "then restart the inspection application."
        )
        if st.button("Reset Inspection", type="primary"):
            reset_and_rerun()
    elif image is not None and retryable:
        st.info(
            "Keep this image selected. Check that the analysis service is "
            "available, then try again."
        )
        retry_column, reset_column = st.columns(2)
        with retry_column:
            st.button(
                "Try Again",
                type="primary",
                width="stretch",
                on_click=begin_analysis,
            )
        with reset_column:
            if st.button("Choose Another Image", width="stretch"):
                reset_and_rerun()
    elif image is not None:
        st.info("Choose another image that meets the upload requirements.")
        if st.button("Choose Another Image", type="primary", width="stretch"):
            reset_and_rerun()
    else:
        st.info("Select a new JPG, JPEG, or PNG image to continue.")
        if st.button("Choose Image", type="primary"):
            reset_and_rerun()


def render_success_state(image: ValidatedImage, prediction: dict[str, Any]) -> None:
    """Render one complete prediction and a reset action."""

    render_result_card(prediction)
    render_gradcam_view(image, prediction["gradcam_image"])

    st.divider()
    if st.button(
        "Analyze Another Image",
        type="primary",
        width="stretch",
    ):
        reset_and_rerun()


def render_inspection_interface() -> None:
    """Compose the current state of the single-image workflow."""

    state = st.session_state[STATE_KEY]
    if state == SUCCESS:
        image = st.session_state[IMAGE_KEY]
        prediction = st.session_state[PREDICTION_KEY]
        if isinstance(image, ValidatedImage) and isinstance(prediction, dict):
            render_success_state(image, prediction)
        else:
            st.session_state[ERROR_KEY] = "The inspection result is incomplete."
            st.session_state[ERROR_RETRYABLE_KEY] = False
            st.session_state[ERROR_CATEGORY_KEY] = "invalid_response"
            st.session_state[STATE_KEY] = ERROR
            render_error_state()
        return

    uploader_key = f"steel-image-uploader-{st.session_state[UPLOADER_VERSION_KEY]}"

    if state == ANALYZING:
        render_upload_section(uploader_key, disabled=True)
        image = st.session_state[IMAGE_KEY]
        if not isinstance(image, ValidatedImage):
            st.session_state[ERROR_KEY] = "The selected image is no longer available."
            st.session_state[ERROR_RETRYABLE_KEY] = False
            st.session_state[ERROR_CATEGORY_KEY] = "request"
            st.session_state[STATE_KEY] = ERROR
            st.rerun()

        render_image_preview(image)
        complete_analysis(image)
        return

    uploaded_file = render_upload_section(uploader_key)
    synchronize_selection(uploaded_file)

    state = st.session_state[STATE_KEY]
    image = st.session_state[IMAGE_KEY]

    if isinstance(image, ValidatedImage):
        render_image_preview(image)

    if state == IMAGE_SELECTED and isinstance(image, ValidatedImage):
        st.button(
            "Analyze Surface",
            type="primary",
            width="stretch",
            on_click=begin_analysis,
        )
    elif state == ERROR:
        render_error_state()


def main() -> None:
    """Render the SteelGuard AI frontend MVP."""

    st.set_page_config(
        page_title="SteelGuard AI",
        page_icon="SG",
        layout="centered",
    )
    load_stylesheet()
    initialize_session_state()
    render_header()
    render_inspection_interface()


if __name__ == "__main__":
    main()
