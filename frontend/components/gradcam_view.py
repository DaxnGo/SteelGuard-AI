"""Original-image and backend-supplied Grad-CAM comparison component."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils.image_validator import ValidatedImage


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIRECTORY = Path(__file__).resolve().parents[1]


def find_local_gradcam(reference: str) -> Path | None:
    """Resolve a mock Grad-CAM filename only within known project folders."""

    safe_name = Path(reference).name
    if not safe_name or Path(safe_name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return None

    candidates = (
        REPOSITORY_ROOT / "mock" / safe_name,
        FRONTEND_DIRECTORY / "assets" / safe_name,
    )
    return next((path for path in candidates if path.is_file()), None)


def render_gradcam_view(image: ValidatedImage, gradcam_reference: str) -> None:
    """Render original versus Grad-CAM, or an honest empty placeholder."""

    st.markdown(
        '<h2 class="section-eyebrow explanation-heading">AI EXPLANATION</h2>',
        unsafe_allow_html=True,
    )
    original_column, gradcam_column = st.columns(2, gap="large")

    with original_column:
        with st.container(border=True):
            st.markdown("#### Original Image")
            st.image(
                image.preview,
                caption=f"Uploaded steel surface — {image.filename}",
                width="stretch",
            )

    with gradcam_column:
        with st.container(border=True):
            st.markdown("#### AI Attention Map")
            gradcam_path = find_local_gradcam(gradcam_reference)
            if gradcam_path is not None:
                st.image(
                    str(gradcam_path),
                    caption="Backend-supplied Grad-CAM attention map",
                    width="stretch",
                )
            else:
                st.markdown(
                    '<div class="gradcam-placeholder" role="img" '
                    'aria-label="Grad-CAM visualization is not available in mock mode">'
                    '<span class="gradcam-placeholder-icon">AI</span>'
                    '<strong>Grad-CAM visualization will appear here.</strong>'
                    '<span>The mock response does not include a generated heatmap.</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )

    st.caption(
        "Highlighted regions indicate areas that contributed to the model prediction. "
        "They do not show causality or a precise defect boundary."
    )
