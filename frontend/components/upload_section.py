"""Single-image upload controls for the SteelGuard AI MVP."""

from __future__ import annotations

from typing import Any

import streamlit as st


SUPPORTED_UPLOAD_TYPES = ["jpg", "jpeg", "png"]


def render_upload_section(widget_key: str) -> Any | None:
    """Render the one-file uploader and return its current selection."""

    st.subheader("Upload Steel Surface Image")
    st.caption("Upload one steel surface image for AI inspection.")

    return st.file_uploader(
        "Choose a JPG, JPEG, or PNG image",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=False,
        key=widget_key,
        help="Only one image can be analyzed per inspection.",
    )
