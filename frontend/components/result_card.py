"""Presentation container for one validated prediction result."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from components.confidence import render_confidence
from components.recommendation import render_recommendation


def render_result_card(prediction: Mapping[str, Any]) -> None:
    """Coordinate defect, confidence, and recommendation presentation."""

    with st.container(border=True):
        st.markdown('<p class="section-eyebrow">INSPECTION RESULT</p>', unsafe_allow_html=True)

        defect_column, confidence_column, recommendation_column = st.columns(
            [1.25, 1, 1.1], gap="large"
        )

        with defect_column:
            st.caption("Detected Defect")
            st.markdown(
                f'<div class="defect-value">{prediction["class_name"]}</div>',
                unsafe_allow_html=True,
            )

        with confidence_column:
            render_confidence(prediction["confidence"])

        with recommendation_column:
            render_recommendation(prediction["recommendation"])
