"""Presentation component for a backend-supplied confidence score."""

from __future__ import annotations

import math

import streamlit as st


def format_confidence(confidence: float) -> str:
    """Format a normalized confidence value as an accessible percentage."""

    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not math.isfinite(confidence)
        or not 0.0 <= confidence <= 1.0
    ):
        raise ValueError("Confidence must be a finite value from 0 to 1.")
    return f"{confidence * 100:.1f}%"


def render_confidence(confidence: float) -> None:
    """Render confidence without deriving any prediction decision."""

    percentage = format_confidence(confidence)
    st.markdown(
        '<p class="result-field-label">Confidence</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="confidence-value" aria-label="Model confidence {percentage}">'
        f"{percentage}</div>",
        unsafe_allow_html=True,
    )
    st.progress(float(confidence), text=f"Model confidence: {percentage}")
