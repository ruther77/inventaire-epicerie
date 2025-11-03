"""Theme and styling helpers for the Streamlit workspace."""

from __future__ import annotations

import os
from typing import Final

import streamlit as st

THEME_LABELS: Final[dict[str, str]] = {"Thème clair": "light", "Thème sombre": "dark"}


def local_css(file_name: str) -> None:
    """Load a CSS file relative to the project root and inject it into the page."""

    file_path = os.path.join(os.path.dirname(__file__), "..", "..", file_name)
    file_path = os.path.abspath(file_path)

    try:
        with open(file_path, encoding="utf-8") as stylesheet:
            st.markdown(f"<style>{stylesheet.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        current_dir = os.getcwd()
        st.error(
            "Erreur: Le fichier de style '%s' est introuvable. Chemin relatif tenté (CWD): %s/%s. "
            "Le fichier n'est PAS dans le conteneur ou le CWD est incorrect." % (file_name, current_dir, file_name)
        )


def apply_ui_theme(theme_key: str) -> None:
    """Inject a small script that toggles the current theme on the parent frame."""

    safe_theme = theme_key if theme_key in {"light", "dark"} else "light"
    st.markdown(
        f"""
        <script>
        const rootDocument = window.parent.document;
        if (rootDocument && rootDocument.body) {{
            rootDocument.body.setAttribute('data-theme', '{safe_theme}');
        }}
        </script>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["THEME_LABELS", "apply_ui_theme", "local_css"]
