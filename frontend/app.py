"""SteelGuard AI Streamlit entry point.

This foundation intentionally contains no upload or inference workflow yet.
"""

from pathlib import Path

import streamlit as st


APP_DIRECTORY = Path(__file__).resolve().parent
STYLESHEET_PATH = APP_DIRECTORY / "styles" / "main.css"

REFERENCE_DOCS = [
    "docs/PROJECT_PLAN.md",
    "docs/FEATURES.md",
    "docs/ARCHITECTURE.md",
    "docs/API_CONTRACT.md",
    "docs/UI_FLOW.md",
    "docs/FRONTEND_SPEC.md",
]


def load_stylesheet() -> None:
    """Load the repository-owned stylesheet when it is available."""

    if STYLESHEET_PATH.is_file():
        css = STYLESHEET_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_foundation_overview() -> None:
    """Show the current repository foundation and next-phase boundaries."""

    st.info(
        "SteelGuard AI currently exposes the monorepo foundation only. "
        "The frontend upload flow, backend prediction API, and AI adapter are "
        "documented for later phases and intentionally not implemented yet."
    )

    left, middle, right = st.columns(3)

    with left:
        st.subheader("Available now")
        st.markdown(
            "- Documented monorepo layout\n"
            "- Streamlit readiness page\n"
            "- Contract-shaped mock response"
        )

    with middle:
        st.subheader("Planned next")
        st.markdown(
            "- Single-image upload and preview\n"
            "- FastAPI prediction endpoint\n"
            "- AI inference and Grad-CAM output"
        )

    with right:
        st.subheader("Boundaries")
        st.markdown(
            "- Frontend stays presentation-only\n"
            "- Backend owns request validation\n"
            "- AI owns prediction policy"
        )

    st.subheader("Reference docs")
    st.markdown("\n".join(f"- `{path}`" for path in REFERENCE_DOCS))


def main() -> None:
    """Render the minimal frontend readiness page."""

    st.set_page_config(
        page_title="SteelGuard AI",
        page_icon="SG",
        layout="centered",
    )
    load_stylesheet()

    st.title("SteelGuard AI")
    st.caption("Intelligent Steel Surface Defect Detection for Smart Manufacturing")
    render_foundation_overview()


if __name__ == "__main__":
    main()
