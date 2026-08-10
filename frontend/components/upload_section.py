"""Single-image upload controls for the SteelGuard AI MVP."""

from __future__ import annotations

from typing import Any

import streamlit as st


SUPPORTED_UPLOAD_TYPES = ["jpg", "jpeg", "png"]


def render_upload_section(widget_key: str, *, disabled: bool = False) -> Any | None:
    """Render the one-file uploader and return its current selection."""

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
        "</div>",
        unsafe_allow_html=True,
    )

    return st.file_uploader(
        "Select steel surface image",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=False,
        disabled=disabled,
        key=widget_key,
        help="Only one image can be analyzed per inspection.",
    )
