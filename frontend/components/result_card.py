"""Presentation container for one validated prediction result."""

from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from components.confidence import render_confidence
from components.recommendation import render_recommendation


def render_result_card(prediction: Mapping[str, Any]) -> None:
    """Coordinate defect, confidence, and recommendation presentation."""

    with st.container(border=True):
        st.markdown(
            '<h2 class="section-eyebrow">INSPECTION RESULT</h2>',
            unsafe_allow_html=True,
        )
        render_recommendation(prediction["recommendation"])

        st.markdown('<div class="result-divider"></div>', unsafe_allow_html=True)
        defect_column, confidence_column = st.columns([1.35, 1], gap="large")

        with defect_column:
            st.markdown(
                '<p class="result-field-label">Detected Defect</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="defect-value">{prediction["class_name"]}</div>',
                unsafe_allow_html=True,
            )

        with confidence_column:
            render_confidence(prediction["confidence"])
