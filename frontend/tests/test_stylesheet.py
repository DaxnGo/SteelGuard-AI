"""Regression checks for the Streamlit light and dark theme stylesheet."""

from __future__ import annotations

from pathlib import Path
import unittest


STYLESHEET_PATH = Path(__file__).resolve().parents[1] / "styles" / "main.css"


class StylesheetThemeTests(unittest.TestCase):
    def test_custom_palette_follows_streamlit_color_scheme(self) -> None:
        css = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn(".stApp {", css)
        self.assertIn(
            "--steelguard-background: light-dark(#f8fafc, #0b1220);",
            css,
        )
        self.assertIn(
            "--steelguard-primary: light-dark(#1e293b, #f8fafc);",
            css,
        )
        self.assertIn(
            "--steelguard-surface: light-dark(#ffffff, #111827);",
            css,
        )

    def test_semantic_recommendations_have_dark_mode_variants(self) -> None:
        css = STYLESHEET_PATH.read_text(encoding="utf-8")

        for variable in (
            "--steelguard-accept-text",
            "--steelguard-rework-text",
            "--steelguard-reject-text",
        ):
            declaration = next(
                line for line in css.splitlines() if variable in line
            )
            self.assertIn("light-dark(", declaration)

    def test_keyboard_and_reduced_motion_rules_are_present(self) -> None:
        css = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn(":focus-visible", css)
        self.assertIn("outline: 3px solid", css)
        self.assertIn(".skip-link", css)
        self.assertIn("#steel-surface-inspection:focus-visible", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn("stFileUploaderDropzoneInstructions", css)
        self.assertNotIn("transition: all", css)

    def test_narrow_layout_stacks_columns_without_horizontal_overflow(self) -> None:
        css = STYLESHEET_PATH.read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 48rem)", css)
        self.assertIn('[data-testid="stColumn"]', css)
        self.assertIn("min-width: 100% !important", css)
        self.assertIn("overflow-wrap: anywhere", css)


if __name__ == "__main__":
    unittest.main()
