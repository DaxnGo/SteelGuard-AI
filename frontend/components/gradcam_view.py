"""Original-image and backend-supplied Grad-CAM comparison component."""

from __future__ import annotations

import base64
import binascii
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
import streamlit as st

from utils.image_validator import ValidatedImage


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIRECTORY = Path(__file__).resolve().parents[1]
PNG_DATA_URI_PREFIX = "data:image/png;base64,"
MAX_GRADCAM_BYTES = 10 * 1024 * 1024


def decode_gradcam_data_uri(reference: str | None) -> bytes | None:
    """Decode one bounded backend PNG data URI, or reject it safely."""

    if not isinstance(reference, str) or not reference.startswith(PNG_DATA_URI_PREFIX):
        return None
    encoded = reference[len(PNG_DATA_URI_PREFIX) :]
    if len(encoded) > ((MAX_GRADCAM_BYTES + 2) // 3) * 4:
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True)
        if not decoded or len(decoded) > MAX_GRADCAM_BYTES:
            return None
        with Image.open(BytesIO(decoded)) as image:
            if image.format != "PNG":
                return None
            image.verify()
    except (binascii.Error, OSError, UnidentifiedImageError):
        return None
    return decoded


def find_local_gradcam(reference: str | None) -> Path | None:
    """Resolve a mock Grad-CAM filename only within known project folders."""

    if reference is None or reference.startswith("data:"):
        return None

    safe_name = Path(reference).name
    if not safe_name or Path(safe_name).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return None

    candidates = (
        REPOSITORY_ROOT / "mock" / safe_name,
        FRONTEND_DIRECTORY / "assets" / safe_name,
    )
    return next((path for path in candidates if path.is_file()), None)


def render_gradcam_view(image: ValidatedImage, gradcam_reference: str | None) -> None:
    """Render original versus Grad-CAM, or an honest empty placeholder."""

    st.markdown(
        '<h2 class="section-eyebrow explanation-heading">AI EXPLANATION</h2>',
        unsafe_allow_html=True,
    )
    original_column, gradcam_column = st.columns(2, gap="large")

    with original_column:
        with st.container(border=True):
            st.markdown("### Original Image")
            st.image(
                image.preview,
                caption=f"Uploaded steel surface — {image.filename}",
                width="stretch",
            )

    with gradcam_column:
        with st.container(border=True):
            st.markdown("### AI Attention Map")
            gradcam_bytes = decode_gradcam_data_uri(gradcam_reference)
            gradcam_path = (
                None
                if gradcam_bytes is not None
                else find_local_gradcam(gradcam_reference)
            )
            if gradcam_bytes is not None:
                st.image(
                    gradcam_bytes,
                    caption="Backend-supplied Grad-CAM attention map",
                    width="stretch",
                )
            elif gradcam_path is not None:
                st.image(
                    str(gradcam_path),
                    caption="Backend-supplied Grad-CAM attention map",
                    width="stretch",
                )
            else:
                st.markdown(
                    '<div class="gradcam-placeholder" role="img" '
                    'aria-label="Grad-CAM visualization is not available in mock mode">'
                    '<span class="gradcam-placeholder-icon" aria-hidden="true">AI</span>'
                    '<strong>Grad-CAM visualization will appear here.</strong>'
                    '<span>The mock response does not include a generated heatmap.</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )

    st.caption(
        "Highlighted regions indicate areas that contributed to the model prediction. "
        "They do not show causality or a precise defect boundary."
    )
