"""Navigation components aligning Streamlit workspace with the SPA styling."""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Final, Iterable, List, Sequence

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

_HEADER_ACTIONS: Final[Sequence[Dict[str, Any]]] = (
    {
        "label": "Tableau de bord",
        "icon": "bi-speedometer2",
        "page_key": "dashboard",
    },
    {
        "label": "Approvisionnement",
        "icon": "bi-truck",
        "page_key": "supply",
    },
)

_MEGA_MENU_SECTIONS: Final[Sequence[Dict[str, Any]]] = (
    {
        "id": "catalogue",
        "label": "Catalogue",
        "subtitle": "Rayons & produits",
        "title": "Catalogue & merchandising",
        "description": "Filtrez, pilotez les rayons et surveillez les alertes critiques.",
        "featured": (
            {
                "label": "Vitrine produits",
                "page_key": "showcase",
                "badge": {"label": "Client", "variant": "new"},
            },
            {
                "label": "Gestion catalogue",
                "page_key": "catalog",
            },
            {
                "label": "Flux de stock",
                "page_key": "movements",
            },
        ),
        "items": (
            {
                "label": "Vitrine produits",
                "description": "Vue client enrichie des performances ventes & stocks.",
                "page_key": "showcase",
                "badge": {"label": "Rayons", "variant": "count"},
            },
            {
                "label": "Catalogue",
                "description": "Gestion détaillée des fiches, options et variantes.",
                "page_key": "catalog",
            },
            {
                "label": "Stocks & mouvements",
                "description": "Flux, projections et alertes de rupture.",
                "page_key": "movements",
            },
            {
                "label": "Audit & écarts",
                "description": "Suivi des écarts d'inventaire et plans d'actions.",
                "page_key": "audit",
            },
        ),
    },
    {
        "id": "operations",
        "label": "Opérations",
        "subtitle": "Achats & ventes",
        "title": "Opérations quotidiennes",
        "description": "Accédez aux modules d'exécution et aux outils de saisie.",
        "featured": (
            {
                "label": "Approvisionnement",
                "page_key": "supply",
            },
            {
                "label": "Point de vente",
                "page_key": "pos",
                "badge": {"label": "Live", "variant": "warning"},
            },
            {
                "label": "Scanner codes-barres",
                "page_key": "scanner",
            },
        ),
        "items": (
            {
                "label": "Approvisionnements",
                "description": "Commandes fournisseurs, réassorts et réceptions.",
                "page_key": "supply",
            },
            {
                "label": "Vente (PoS)",
                "description": "Encaissement rapide et gestion panier.",
                "page_key": "pos",
            },
            {
                "label": "Scanner",
                "description": "Lecture webcam des codes-barres & recherche instantanée.",
                "page_key": "scanner",
            },
            {
                "label": "Extraction facture",
                "description": "Analyse des factures fournisseurs et import automatique.",
                "page_key": "extract",
            },
            {
                "label": "Import catalogue",
                "description": "Import massif de références et contrôles de cohérence.",
                "page_key": "import",
            },
        ),
    },
    {
        "id": "pilotage",
        "label": "Pilotage",
        "subtitle": "Analyse & reporting",
        "title": "Pilotage de la performance",
        "description": "Suivez vos indicateurs clés et préparez vos arbitrages.",
        "featured": (
            {
                "label": "Tableau de bord",
                "page_key": "dashboard",
                "badge": {"label": "Synthèse", "variant": "success"},
            },
            {
                "label": "Produits critiques",
                "page_key": "movements",
            },
        ),
        "items": (
            {
                "label": "Dashboard",
                "description": "KPIs consolidés, top ventes et valeur de stock.",
                "page_key": "dashboard",
            },
            {
                "label": "Diagnostic stock",
                "description": "Analyse des écarts, rotations et projections.",
                "page_key": "movements",
            },
            {
                "label": "Top ventes",
                "description": "Visualisation des produits performants sur 30 jours.",
                "page_key": "showcase",
            },
            {
                "label": "Maintenance & Admin",
                "description": "Outils techniques, sauvegardes et réglages.",
                "page_key": "admin",
            },
        ),
    },
)

_ENHANCEMENT_SCRIPT: Final[str] = """
<script>
(function () {
  const rootDocument = window.parent?.document ?? document;
  if (!rootDocument) {
    return;
  }

  const header = rootDocument.querySelector('[data-workspace-nav]');
  if (!header || header.dataset.enhanced === 'true') {
    return;
  }

  header.dataset.enhanced = 'true';

  const toggles = header.querySelectorAll('[data-mega-trigger]');
  const panels = header.querySelectorAll('[data-mega-panel]');

  const setActiveSection = (sectionId) => {
    toggles.forEach((toggle) => {
      const isActive = toggle.getAttribute('data-mega-target') === sectionId;
      toggle.classList.toggle('is-active', isActive);
      toggle.setAttribute('aria-expanded', isActive ? 'true' : 'false');
      toggle.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    panels.forEach((panel) => {
      const isActive = panel.getAttribute('data-mega-panel') === sectionId;
      panel.classList.toggle('is-active', isActive);
      panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    });
  };

  const selectWorkspaceTab = (index) => {
    const tabButtons = rootDocument.querySelectorAll('[data-baseweb="tab"]');
    const target = tabButtons?.[index];
    if (target instanceof HTMLElement) {
      target.click();
    }
  };

  const updateActiveLinks = (pageKey) => {
    if (!pageKey) {
      return;
    }

    rootDocument.body?.setAttribute('data-current-page', pageKey);
    header.querySelectorAll('[data-page-key]').forEach((node) => {
      const isActive = node.getAttribute('data-page-key') === pageKey;
      node.classList.toggle('is-active', isActive);
      if (isActive) {
        node.setAttribute('aria-current', 'page');
      } else {
        node.removeAttribute('aria-current');
      }
    });
  };

  const syncFromStreamlitTabs = () => {
    const streamlitTabs = Array.from(
      rootDocument.querySelectorAll('[data-baseweb="tab"]')
    );
    const activeIndex = streamlitTabs.findIndex(
      (tab) => tab.getAttribute('aria-selected') === 'true'
    );
    if (activeIndex >= 0) {
      const activeLink = header.querySelector(
        `[data-tab-target="${activeIndex}"][data-page-key]`
      );
      const pageKey = activeLink?.getAttribute('data-page-key');
      if (pageKey) {
        updateActiveLinks(pageKey);
      }
    }
  };

  toggles.forEach((toggle) => {
    const targetSection = toggle.getAttribute('data-mega-target');
    if (!targetSection) {
      return;
    }

    toggle.addEventListener('click', (event) => {
      event.preventDefault();
      setActiveSection(targetSection);
    });

    toggle.addEventListener('mouseenter', () => setActiveSection(targetSection));
    toggle.addEventListener('focus', () => setActiveSection(targetSection));
  });

  const tabLinks = header.querySelectorAll('[data-tab-target]');
  tabLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      const targetIndex = Number(link.getAttribute('data-tab-target'));
      const hasTarget = Number.isFinite(targetIndex);
      const pageKey = link.getAttribute('data-page-key');
      if (hasTarget) {
        event.preventDefault();
        selectWorkspaceTab(targetIndex);
      }
      if (pageKey) {
        updateActiveLinks(pageKey);
      }
    });
  });

  const initialSection = toggles[0]?.getAttribute('data-mega-target');
  if (initialSection) {
    setActiveSection(initialSection);
  }

  syncFromStreamlitTabs();

  rootDocument.addEventListener('click', (event) => {
    const target = event.target;
    if (target && typeof target.closest === 'function') {
      const tab = target.closest('[data-baseweb="tab"]');
      if (tab) {
        window.requestAnimationFrame(syncFromStreamlitTabs);
      }
    }
  });
})();
</script>
"""


def _badge_markup(badge: Dict[str, str] | None) -> str:
    if not badge:
        return ""
    label = escape(badge.get("label", "").strip())
    if not label:
        return ""
    variant = badge.get("variant", "").strip()
    variant_class = f" badge-{escape(variant)}" if variant else ""
    return f"<span class=\"badge{variant_class}\">{label}</span>"


def _tab_target_attrs(page_key: str | None) -> str:
    if not page_key:
        return ""
    tab_index = _PAGE_KEY_TO_INDEX.get(page_key)
    if tab_index is None:
        return ""
    return f" data-tab-target=\"{tab_index}\" data-page-key=\"{escape(page_key)}\""


def _build_tabs_markup() -> str:
    buttons: List[str] = []
    for section in _MEGA_MENU_SECTIONS:
        section_id = escape(section["id"])
        label = escape(section["label"])
        subtitle = escape(section.get("subtitle", ""))
        subtitle_markup = (
            f'<span class="mega-menu-tab-subtitle">{subtitle}</span>'
            if subtitle
            else ""
        )
        buttons.append(
            "".join(
                [
                    (
                        f'<button class="mega-menu-tab" type="button" data-mega-trigger '
                        f'data-mega-target="{section_id}" aria-controls="mega-panel-{section_id}" '
                        'aria-expanded="false" role="tab" aria-selected="false">'
                    ),
                    f'<span class="mega-menu-tab-label">{label}</span>',
                    subtitle_markup,
                    "</button>",
                ]
            )
        )
    return "".join(buttons)


def _build_featured_markup(featured: Sequence[Dict[str, Any]]) -> str:
    actions: List[str] = []
    for action in featured:
        label = escape(action.get("label", ""))
        attrs = _tab_target_attrs(action.get("page_key"))
        badge_markup = _badge_markup(action.get("badge"))
        actions.append(
            "".join(
                [
                    f"<a class=\"mega-menu-featured-action\" href=\"#\"{attrs}>",
                    f"<span class=\"mega-menu-featured-label\">{label}</span>",
                    badge_markup,
                    "</a>",
                ]
            )
        )
    return "".join(actions)


def _build_items_markup(items: Sequence[Dict[str, Any]]) -> str:
    entries: List[str] = []
    for item in items:
        label = escape(item.get("label", ""))
        description = escape(item.get("description", ""))
        attrs = _tab_target_attrs(item.get("page_key"))
        badge_markup = _badge_markup(item.get("badge"))
        description_markup = (
            f"<span class=\"mega-menu-link-description\">{description}</span>"
            if description
            else ""
        )
        entries.append(
            "".join(
                [
                    "<li>",
                    f"<a class=\"mega-menu-link\" href=\"#\"{attrs}>",
                    f"<span class=\"mega-menu-link-label\">{label}{badge_markup}</span>",
                    description_markup,
                    "</a>",
                    "</li>",
                ]
            )
        )
    return "".join(entries)


def _build_panel_markup(section: Dict[str, Any]) -> str:
    section_id = escape(section["id"])
    title = escape(section.get("title", ""))
    description = escape(section.get("description", ""))
    featured = section.get("featured", ())
    items = section.get("items", ())

    featured_markup = _build_featured_markup(featured)
    items_markup = _build_items_markup(items)

    header_description = (
        f"<p>{description}</p>"
        if description
        else ""
    )

    featured_section = (
        f"<div class=\"mega-menu-featured\">{featured_markup}</div>"
        if featured_markup
        else ""
    )

def _build_panel_markup(section: Dict[str, Any]) -> str:
    section_id = escape(section["id"])
    title = escape(section.get("title", section.get("label", "")))
    description = escape(section.get("description", ""))
    featured_markup = _build_featured_markup(section)
    items_markup = _build_items_markup(section.get("items", ()))
    description_markup = f"<p>{description}</p>" if description else ""
    return "".join(
        [
            f"<section class=\"mega-menu-panel\" data-mega-panel=\"{section_id}\" ",
            f"id=\"mega-panel-{section_id}\" role=\"tabpanel\" aria-hidden=\"true\">",
            "<div class=\"mega-menu-panel-header\">",
            "<div>",
            f"<h3>{title}</h3>",
            header_description,
            "</div>",
            featured_section,
            "</div>",
            "<div class=\"mega-menu-panel-body\">",
            f"<ul class=\"mega-menu-links\">{items_markup}</ul>",
            "</div>",
            "</section>",
        ]
    )


def _build_panels_markup() -> str:
    return "".join(_build_panel_markup(section) for section in _MEGA_MENU_SECTIONS)


def _build_header_actions() -> str:
    links: List[str] = []
    for action in _HEADER_ACTIONS:
        label = escape(action.get("label", ""))
        if not label:
            continue
        icon = escape(action.get("icon", ""))
        attrs = _tab_target_attrs(action.get("page_key"))
        icon_markup = f"<i class=\"bi {icon}\"></i>" if icon else ""
        links.append(
            "".join(
                [
                    f"<a class=\"quick-action\" href=\"#\"{attrs}>",
                    icon_markup,
                    f"<span>{label}</span>",
                    "</a>",
                ]
            )
        )
    return "".join(links)


def render_workspace_navigation() -> None:
    """Render the SPA-aligned navigation header for the Streamlit workspace."""

    html_parts: List[str] = [
        "<link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css\" />",
        "<header class=\"app-header\" data-workspace-nav>",
        "<div class=\"brand-area\">",
        "<button class=\"hamburger\" type=\"button\" aria-expanded=\"false\">",
        "<span class=\"visually-hidden\">Ouvrir le menu</span>",
        "<span></span><span></span><span></span>",
        "</button>",
        "<span class=\"brand-title\">Inventaire Épicerie</span>",
        "</div>",
        "<nav class=\"mega-menu\" data-mega-menu>",
        "<button class=\"mega-menu-trigger\" type=\"button\" aria-expanded=\"false\">Menu</button>",
        "<div class=\"mega-menu-content\">",
        "<div class=\"mega-menu-tabs\" role=\"tablist\">",
        _build_tabs_markup(),
        "</div>",
        "<div class=\"mega-menu-panels\">",
        _build_panels_markup(),
        "</div>",
        "</div>",
        "</nav>",
        "<div class=\"header-actions\">",
        _build_header_actions(),
        "</div>",
        "</header>",
        _ENHANCEMENT_SCRIPT,
    ]

    st.markdown("".join(html_parts), unsafe_allow_html=True)


__all__ = ["render_workspace_navigation", "_PAGE_KEY_TO_INDEX", "_PAGE_KEYS"]
