"""Single-image upload controls for the SteelGuard AI MVP."""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.image_validator import (
    UploadLimitConfigurationError,
    format_file_size,
    load_max_upload_bytes,
)


SUPPORTED_UPLOAD_TYPES = ["jpg", "jpeg", "png"]


def render_upload_section(widget_key: str, *, disabled: bool = False) -> Any | None:
    """Render the one-file uploader and return its current selection."""

    try:
        max_upload_bytes = load_max_upload_bytes()
    except UploadLimitConfigurationError:
        max_upload_bytes = None
        st.warning(
            "Upload limit configuration is invalid. Contact the system administrator."
        )
    limit_guidance = (
        '<span class="upload-guidance-separator" aria-hidden="true"></span>'
        f'<span><strong>Maximum:</strong> {format_file_size(max_upload_bytes)}</span>'
        if max_upload_bytes is not None
        else ""
    )

    st.markdown(
        '<h2 class="section-eyebrow inspection-heading">'
        "STEEL SURFACE INSPECTION</h2>",
        unsafe_allow_html=True,
    )
    st.subheader("Upload Steel Surface Image")
    st.markdown(
        '<div class="upload-guidance" aria-label="Upload requirements">'
        '<span><strong>Supported:</strong> JPG, JPEG, PNG</span>'
        '<span class="upload-guidance-separator" aria-hidden="true"></span>'
        '<span>One image per inspection</span>'
        f"{limit_guidance}"
        "</div>",
        unsafe_allow_html=True,
    )

    return st.file_uploader(
        "Select steel surface image",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=False,
        disabled=disabled,
        key=widget_key,
        help="Select one image, review its preview, then choose Analyze Surface.",
    )
