"""Navigation components for the Streamlit workspace."""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Final, List

import streamlit as st

_PAGE_KEYS: Final[List[str]] = [
    "showcase",
    "supply",
    "pos",
    "catalog",
    "movements",
    "audit",
    "dashboard",
    "scanner",
    "extract",
    "import",
    "admin",
]

_PAGE_KEY_TO_INDEX: Final[Dict[str, int]] = {key: idx for idx, key in enumerate(_PAGE_KEYS)}

_NAV_SHORTCUTS: Final[List[Dict[str, Any]]] = [
    {
        "label": "Approvisionnement",
        "icon": "bi-truck",
        "tab_index": _PAGE_KEY_TO_INDEX["supply"],
        "page_key": "supply",
    },
    {
        "label": "Vente (PoS)",
        "icon": "bi-bag",
        "tab_index": _PAGE_KEY_TO_INDEX["pos"],
        "page_key": "pos",
    },
    {
        "label": "Dashboard",
        "icon": "bi-speedometer2",
        "tab_index": _PAGE_KEY_TO_INDEX["dashboard"],
        "page_key": "dashboard",
    },
]

_NAV_SECTIONS: Final[List[Dict[str, Any]]] = [
    {
        "id": "catalogue",
        "label": "Catalogue",
        "icon": "bi-grid",
        "description": "Suivez vos rayons, vos stocks et vos contrôles qualité.",
        "items": [
            {
                "label": "Vitrine produits",
                "description": "Aperçu client, ventes et mises en avant.",
                "badge": "Rayons",
                "tab_index": _PAGE_KEY_TO_INDEX["showcase"],
                "page_key": "showcase",
            },
            {
                "label": "Catalogue",
                "description": "Gestion détaillée des fiches et options produits.",
                "badge": "Catalogue",
                "tab_index": _PAGE_KEY_TO_INDEX["catalog"],
                "page_key": "catalog",
            },
            {
                "label": "Stock & mouvements",
                "description": "Flux, projections et alertes de ruptures.",
                "badge": "Stock",
                "tab_index": _PAGE_KEY_TO_INDEX["movements"],
                "page_key": "movements",
            },
            {
                "label": "Audit & écarts",
                "description": "Suivi des écarts inventaires et plans d'actions.",
                "badge": "Audit",
                "tab_index": _PAGE_KEY_TO_INDEX["audit"],
                "page_key": "audit",
            },
        ],
        "links": [
            {
                "label": "Top ventes",
                "icon": "bi-graph-up",
                "tab_index": _PAGE_KEY_TO_INDEX["showcase"],
                "page_key": "showcase",
            },
            {
                "label": "Produits critiques",
                "icon": "bi-exclamation-octagon",
                "tab_index": _PAGE_KEY_TO_INDEX["movements"],
                "page_key": "movements",
            },
            {
                "label": "Plans d'audit",
                "icon": "bi-clipboard-check",
                "tab_index": _PAGE_KEY_TO_INDEX["audit"],
                "page_key": "audit",
            },
        ],
    },
    {
        "id": "explorer",
        "label": "Explorer",
        "icon": "bi-compass",
        "description": "Accédez directement aux opérations et outils spécialisés.",
        "items": [
            {
                "label": "Approvisionnement",
                "description": "Commandes fournisseurs et réassorts.",
                "badge": "Achats",
                "tab_index": _PAGE_KEY_TO_INDEX["supply"],
                "page_key": "supply",
            },
            {
                "label": "Vente (PoS)",
                "description": "Encaissement rapide et gestion panier.",
                "badge": "Caisse",
                "tab_index": _PAGE_KEY_TO_INDEX["pos"],
                "page_key": "pos",
            },
            {
                "label": "Dashboard",
                "description": "Pilotage global et indicateurs clés.",
                "badge": "Pilotage",
                "tab_index": _PAGE_KEY_TO_INDEX["dashboard"],
                "page_key": "dashboard",
            },
            {
                "label": "Maintenance & Admin",
                "description": "Tâches de support et outils techniques.",
                "badge": "Admin",
                "tab_index": _PAGE_KEY_TO_INDEX["admin"],
                "page_key": "admin",
            },
        ],
        "links": [
            {
                "label": "Scanner codes-barres",
                "icon": "bi-upc-scan",
                "tab_index": _PAGE_KEY_TO_INDEX["scanner"],
                "page_key": "scanner",
            },
            {
                "label": "Extraction facture",
                "icon": "bi-receipt-cutoff",
                "tab_index": _PAGE_KEY_TO_INDEX["extract"],
                "page_key": "extract",
            },
            {
                "label": "Importation catalogues",
                "icon": "bi-cloud-upload",
                "tab_index": _PAGE_KEY_TO_INDEX["import"],
                "page_key": "import",
            },
        ],
    },
]


def render_workspace_navigation() -> None:
    """Render the mega menu and shortcuts used to drive the tabs."""

    def _build_shortcuts() -> str:
        parts: List[str] = []
        for shortcut in _NAV_SHORTCUTS:
            label = escape(shortcut["label"])
            icon = escape(shortcut["icon"])
            tab_index = shortcut.get("tab_index", 0)
            page_key = shortcut.get("page_key")
            data_page = f" data-page-key=\"{escape(page_key)}\"" if page_key else ""
            href = "#"
            parts.append(
                "".join(
                    [
                        f"<a class=\"workspace-shortcut\" href=\"{href}\" data-tab-target=\"{tab_index}\"",
                        data_page,
                        ">",
                        "<span class=\"workspace-shortcut__icon\"><i class=\"bi ",
                        f"{icon}",
                        "\"></i></span>",
                        f"<span class=\"workspace-shortcut__label\">{label}</span>",
                        "</a>",
                    ]
                )
            )
        return "".join(parts)

    def _build_sections() -> str:
        section_parts: List[str] = []
        for section in _NAV_SECTIONS:
            section_id = escape(section["id"])
            header = (
                f"<button class=\"workspace-primary__toggle\" type=\"button\" "
                f"id=\"mega-trigger-{section_id}\" data-mega-trigger data-mega-target=\"{section_id}\" "
                f"aria-controls=\"mega-panel-{section_id}\" aria-expanded=\"false\">"
                f"<i class=\"bi {escape(section['icon'])}\"></i>"
                f"<span>{escape(section['label'])}</span></button>"
            )

            item_parts: List[str] = []
            for item in section["items"]:
                label = escape(item["label"])
                description = escape(item["description"])
                badge = escape(item.get("badge", ""))
                tab_index = item.get("tab_index", 0)
                page_key = item.get("page_key")
                page_data = f" data-page-key=\"{escape(page_key)}\"" if page_key else ""
                href = "#"
                badge_markup = (
                    f"<span class=\"badge workspace-preview__badge\">{badge}</span>" if badge else ""
                )
                item_parts.append(
                    "".join(
                        [
                            "<li class=\"workspace-preview__item\">",
                            f"<a class=\"workspace-preview__link\" href=\"{href}\" data-tab-target=\"{tab_index}\"{page_data}>",
                            "<span class=\"workspace-preview__icon\"><i class=\"bi bi-arrow-up-right\"></i></span>",
                            "<span class=\"workspace-preview__content\">",
                            f"<span class=\"workspace-preview__label\">{label}{badge_markup}</span>",
                            f"<span class=\"workspace-preview__desc\">{description}</span>",
                            "</span></a></li>",
                        ]
                    )
                )

            link_parts: List[str] = []
            for link in section.get("links", []):
                label = escape(link["label"])
                icon = escape(link.get("icon", "bi-arrow-right-short"))
                tab_index = link.get("tab_index", 0)
                page_key = link.get("page_key")
                page_data = f" data-page-key=\"{escape(page_key)}\"" if page_key else ""
                href = "#"
                link_parts.append(
                    "".join(
                        [
                            "<li><a class=\"workspace-preview__secondary-link\" href=\"",
                            href,
                            "\" data-tab-target=\"",
                            str(tab_index),
                            "\"",
                            page_data,
                            f"><i class=\"bi {icon}\"></i>",
                            f"<span>{label}</span></a></li>",
                        ]
                    )
                )

            panel = (
                f"<section class=\"workspace-primary__panel\" id=\"mega-panel-{section_id}\" "
                "data-mega-panel role=\"tabpanel\" aria-hidden=\"true\">"
                "<header class=\"workspace-primary__panel-header\">"
                f"<div class=\"workspace-primary__panel-title\"><span class=\"workspace-primary__panel-icon\">"
                f"<i class=\"bi {escape(section['icon'])}\"></i></span>"
                f"<div><h3 class=\"workspace-primary__panel-heading\">{escape(section['label'])}</h3>"
                f"<p class=\"workspace-primary__panel-description\">{escape(section['description'])}</p>"
                "</div></div></header>"
                "<div class=\"workspace-primary__panel-grid\">"
                "<div class=\"workspace-primary__panel-column\">"
                "<ul class=\"workspace-preview__list\">"
                + "".join(item_parts)
                + "</ul></div><div class=\"workspace-primary__panel-column\">"
                "<h4 class=\"workspace-preview__title\">Accès rapides</h4><ul class=\"workspace-preview__secondary\">"
                + "".join(link_parts)
                + "</ul></div></div></section>"
            )

            section_parts.append(header)
            section_parts.append(panel)

        toggles = "<div class=\"workspace-primary__toggles\" role=\"tablist\" aria-label=\"Navigation principale\">"
        panels_wrapper = "<div class=\"workspace-primary__panels\">"
        toggle_markup: List[str] = []
        panel_markup: List[str] = []
        for idx in range(0, len(section_parts), 2):
            toggle_markup.append(section_parts[idx])
            panel_markup.append(section_parts[idx + 1])

        toggles += "".join(toggle_markup) + "</div>"
        panels_wrapper += "".join(panel_markup) + "</div>"
        return toggles + panels_wrapper

    html_parts: List[str] = [
        "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css\" />",
        "<section class=\"workspace-header\" id=\"workspaceNavRoot\" data-workspace-nav>",
        "<div class=\"workspace-header__bar\">",
        "<div class=\"workspace-header__group workspace-header__group--left\">",
        "<div class=\"workspace-header__brand\"><span class=\"workspace-header__brand-eyebrow\">Inventaire Épicerie</span>",
        "<h1 class=\"workspace-header__brand-title\">Centre de navigation</h1></div>",
        "</div>",
        "<div class=\"workspace-header__cluster\">",
        f"<div class=\"workspace-shortcuts\">{_build_shortcuts()}</div>",
        "</div>",
        "</div>",
        f"<div class=\"workspace-primary\">{_build_sections()}</div>",
        "</section>",
    ]

    st.markdown("".join(html_parts), unsafe_allow_html=True)


__all__ = ["render_workspace_navigation", "_PAGE_KEY_TO_INDEX", "_PAGE_KEYS"]
