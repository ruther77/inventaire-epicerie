"""Navigation components aligning Streamlit workspace with the SPA styling."""

from __future__ import annotations

from html import escape
from typing import Any, Dict, Final, List, Sequence

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
                "description": "Suivi des écarts d\'inventaire et plans d\'actions.",
                "page_key": "audit",
            },
        ),
    },
    {
        "id": "operations",
        "label": "Opérations",
        "subtitle": "Achats & ventes",
        "title": "Opérations quotidiennes",
        "description": "Accédez aux modules d\'exécution et aux outils de saisie.",
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


  const header = rootDocument.querySelector('[data-workspace-nav]');
  if (!header || header.dataset.enhanced === 'true') {
    return;
  }

  header.dataset.enhanced = 'true';

  const megaMenu = header.querySelector('[data-mega-menu]');
  const toggleButton = megaMenu?.querySelector('.mega-menu-trigger');
  const brandToggle = header.querySelector('.hamburger');
  const tabButtons = megaMenu ? Array.from(megaMenu.querySelectorAll('[data-mega-tab]')) : [];
  const panels = megaMenu ? Array.from(megaMenu.querySelectorAll('[data-mega-panel]')) : [];

  const toggleElements = [toggleButton, brandToggle].filter(Boolean);

  const setActiveSection = (sectionId) => {
    tabButtons.forEach((tab) => {
      const isActive = tab.dataset.megaTab === sectionId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-expanded', isActive ? 'true' : 'false');
    });
    panels.forEach((panel) => {
      const isActive = panel.dataset.megaPanel === sectionId;
      panel.classList.toggle('visible', isActive);
      panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
    });
  };

  if (tabButtons.length > 0) {
    setActiveSection(tabButtons[0].dataset.megaTab);
  }

  const closeMenu = () => {
    if (!megaMenu) return;
    megaMenu.classList.remove('mega-menu-open');
    toggleElements.forEach((toggle) => {
      toggle.setAttribute('aria-expanded', 'false');
    });
  };

  const selectWorkspaceTab = (index) => {
    const tabButtons = rootDocument.querySelectorAll('[data-baseweb="tab"]');
    const target = tabButtons?.[index];
    if (target) {
      target.click();
    }
  };

  const updateActiveLinks = (pageKey) => {
    if (!pageKey) return;
    rootDocument.body?.setAttribute('data-current-page', pageKey);
    header.querySelectorAll('[data-page-key]').forEach((node) => {
      node.classList.toggle('is-active', node.getAttribute('data-page-key') === pageKey);
    });
  };

  const syncFromStreamlitTabs = () => {
    const streamlitTabs = Array.from(rootDocument.querySelectorAll('[data-baseweb="tab"]'));
    const activeIndex = streamlitTabs.findIndex((tab) => tab.getAttribute('aria-selected') === 'true');
    if (activeIndex >= 0) {
      const activeLink = header.querySelector(`[data-tab-target="${activeIndex}"][data-page-key]`);
      const pageKey = activeLink?.getAttribute('data-page-key');
      if (pageKey) {
        updateActiveLinks(pageKey);
      }
    }
  };

  tabButtons.forEach((tab) => {
    tab.addEventListener('mouseenter', () => setActiveSection(tab.dataset.megaTab));
    tab.addEventListener('focus', () => setActiveSection(tab.dataset.megaTab));
    tab.addEventListener('click', (event) => {
      event.preventDefault();
      setActiveSection(tab.dataset.megaTab);
    });
  });

  panels.forEach((panel) => {
    const links = panel.querySelectorAll('[data-tab-target]');
    links.forEach((link) => {
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
        closeMenu();
      });
    });
  });

  const actionLinks = header.querySelectorAll('.header-actions [data-tab-target]');
  actionLinks.forEach((action) => {
    action.addEventListener('click', (event) => {
      const targetIndex = Number(action.getAttribute('data-tab-target'));
      const hasTarget = Number.isFinite(targetIndex);
      const pageKey = action.getAttribute('data-page-key');
      if (hasTarget) {
        event.preventDefault();
        selectWorkspaceTab(targetIndex);
      }
      if (pageKey) {
        updateActiveLinks(pageKey);
      }
      closeMenu();
    });
  });

  toggleElements.forEach((toggle) => {
    toggle.addEventListener('click', () => {
      if (!megaMenu) return;
      const isOpen = megaMenu.classList.toggle('mega-menu-open');
      toggleElements.forEach((btn) => {
        btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    });
  });

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

  rootDocument.addEventListener('click', (event) => {
    if (!megaMenu) return;
    const target = event.target;
    const clickedToggle = toggleElements.some((btn) => btn.contains(target));
    if (!megaMenu.contains(target) && !clickedToggle) {
      closeMenu();
    }
  });
})();
</script>
"""


def _badge_markup(badge: Dict[str, str] | None) -> str:
    if not badge:
        return ""
    label = escape(badge.get("label", ""))
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
    return (
        f" data-tab-target=\"{tab_index}\" data-page-key=\"{escape(page_key)}\""
    )


def _build_tabs_markup() -> str:
    buttons: List[str] = []
    for section in _MEGA_MENU_SECTIONS:
        section_id = escape(section["id"])
        label = escape(section["label"])
        subtitle = escape(section.get("subtitle", ""))
        buttons.append(
            "".join(
                [
                    f"<button class=\"mega-menu-tab\" type=\"button\" data-mega-tab=\"{section_id}\" ",
                    f"aria-controls=\"mega-panel-{section_id}\" aria-expanded=\"false\">",
                    f"<span class=\"mega-menu-tab-label\">{label}</span>",
                    (
                        f"<span class=\"mega-menu-tab-subtitle\">{subtitle}</span>"
                        if subtitle
                        else ""
                    ),
                    "</button>",
                ]
            )
        return "".join(parts)

    def _build_sections() -> str:
        section_parts: List[str] = []
        for section in _NAV_SECTIONS:
            section_id = escape(section["id"])
            header = (
                f"<button class=\"workspace-primary__toggle\" type=\"button\" "
                f"id=\"mega-trigger-{section_id}\" data-mega-trigger data-mega-target=\"{section_id}\" "
                f"aria-controls=\"mega-panel-{section_id}\" aria-expanded=\"false\" "
                "role=\"tab\" aria-selected=\"false\">"
                f"<i class=\"bi {escape(section['icon'])}\"></i>"
                f"<span>{escape(section['label'])}</span></button>"
            )
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
                f"data-mega-panel=\"{section_id}\" role=\"tabpanel\" "
                f"aria-labelledby=\"mega-trigger-{section_id}\" aria-hidden=\"true\">"
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
        )

    return "".join(
        [
            f"<div class=\"mega-menu-panel\" data-mega-panel=\"{section_id}\" ",
            f"id=\"mega-panel-{section_id}\" aria-hidden=\"true\">",
            "<div class=\"mega-menu-panel-header\">",
            "<div>",
            f"<h3>{title}</h3>",
            (f"<p>{description}</p>" if description else ""),
            "</div>",
            "<div class=\"mega-menu-featured-actions\">",
            "".join(featured_markup),
            "</div></div>",
            "<div class=\"mega-menu-grid\">",
            "".join(items_markup),
            "</div>",
            "</div>",
        ]
    )


def _build_panels_markup() -> str:
    return "".join(_build_panel_markup(section) for section in _MEGA_MENU_SECTIONS)


def _build_header_actions() -> str:
    links: List[str] = []
    for action in _HEADER_ACTIONS:
        label = escape(action.get("label", ""))
        icon = escape(action.get("icon", ""))
        attrs = _tab_target_attrs(action.get("page_key"))
        links.append(
            "".join(
                [
                    f"<a class=\"quick-action\" href=\"#\"{attrs}>",
                    (f"<i class=\"bi {icon}\"></i>" if icon else ""),
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
        "<div class=\"mega-menu-tabs\">",
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
        f"<div class=\"workspace-primary\">{_build_sections()}</div>",
        "</section>",
        _ENHANCEMENT_SCRIPT,
    ]

    st.markdown("".join(html_parts), unsafe_allow_html=True)


__all__ = ["render_workspace_navigation", "_PAGE_KEY_TO_INDEX", "_PAGE_KEYS"]
