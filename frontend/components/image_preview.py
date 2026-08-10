"""Preview rendering for one validated steel surface image."""

from __future__ import annotations

import streamlit as st

from utils.image_validator import ValidatedImage


def format_file_size(size_bytes: int) -> str:
    """Return a compact human-readable file size."""

    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_image_preview(image: ValidatedImage) -> None:
    """Display the validated preview and non-inference image metadata."""

    with st.container(border=True):
        st.markdown("#### Selected Image")
        st.image(
            image.preview,
            caption=f"Original steel surface image — {image.filename}",
            use_container_width=True,
        )

        filename_column, dimensions_column, size_column = st.columns(3)
        with filename_column:
            st.caption("Filename")
            st.write(image.filename)
        with dimensions_column:
            st.caption("Dimensions")
            st.write(f"{image.width} × {image.height} px")
        with size_column:
            st.caption("File size")
            st.write(format_file_size(len(image.data)))

        st.success("Ready for inspection")
