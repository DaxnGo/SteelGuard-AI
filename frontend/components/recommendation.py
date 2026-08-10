"""Presentation component for a backend-supplied quality recommendation."""

from __future__ import annotations

import streamlit as st


RECOMMENDATION_CLASSES = {
    "ACCEPT": "recommendation--accept",
    "REWORK": "recommendation--rework",
    "REJECT": "recommendation--reject",
}


def render_recommendation(recommendation: str) -> None:
    """Render an exact recommendation using both text and color."""

    css_class = RECOMMENDATION_CLASSES.get(recommendation)
    if css_class is None:
        raise ValueError("Unsupported recommendation value.")

    st.markdown(
        '<div class="recommendation-panel '
        f'{css_class}" role="status" aria-label="Quality recommendation: '
        f'{recommendation}">'
        '<span class="recommendation-label">Quality Recommendation</span>'
        '<span class="recommendation-value">'
        '<span class="recommendation-dot" aria-hidden="true"></span>'
        f"{recommendation}</span>"
        '<span class="recommendation-note">AI-assisted inspection outcome</span>'
        "</div>",
        unsafe_allow_html=True,
    )
