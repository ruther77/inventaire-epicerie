(function () {
    const pinnedKey = 'inventaire_pinned_categories';
    const savedSearchKey = 'inventaire_saved_searches';

    const body = document.body;
    const workspacePanel = document.querySelector('[data-workspace-panel]');
    const workspaceBackdrop = document.querySelector('[data-workspace-backdrop]');
    const workspaceToggles = document.querySelectorAll('[data-workspace-toggle]');

    const globalSearch = document.querySelector('[data-global-search]');
    const searchToggles = document.querySelectorAll('[data-search-toggle]');

    const megaNav = document.querySelector('.mega-nav');
    const megaToggles = document.querySelectorAll('[data-mega-toggle]');
    const megaPanels = document.querySelectorAll('[data-mega-panel]');
    const megaPreview = document.querySelector('[data-mega-preview]');
    const megaPreviewTitle = megaPreview ? megaPreview.querySelector('[data-mega-preview-title]') : null;
    const megaPreviewSummary = megaPreview ? megaPreview.querySelector('[data-mega-preview-summary]') : null;
    const megaPreviewBadge = megaPreview ? megaPreview.querySelector('[data-mega-preview-badge]') : null;
    const megaPreviewLink = megaPreview ? megaPreview.querySelector('[data-mega-preview-link]') : null;
    const megaPreviewTriggers = document.querySelectorAll('[data-mega-preview-trigger]');

    const pinnedContainer = document.querySelector('[data-pinned-container]');
    const pinnedList = pinnedContainer ? pinnedContainer.querySelector('[data-pinned-list]') : null;
    const pinnedEmpty = pinnedContainer ? pinnedContainer.querySelector('[data-empty-message]') : null;
    const pinnedClear = pinnedContainer ? pinnedContainer.querySelector('[data-clear-pins]') : null;
    const pinnedButtons = document.querySelectorAll('[data-pin-toggle]');
    const pinnedSummaries = document.querySelectorAll('[data-pinned-summary]');

    const savedSearchContainers = document.querySelectorAll('[data-saved-searches]');
    const savedPlaceholder = document.querySelector('[data-no-saved-search]');
    const saveSearchButton = document.querySelector('[data-save-search]');
    const clearSearchesButton = document.querySelector('[data-clear-searches]');
    const searchInput = document.querySelector('[data-global-search-input]');
    const searchForm = document.querySelector('[data-global-search-form]');

    const productCards = document.querySelectorAll('[data-product-card]');
    const filterPills = document.querySelectorAll('[data-filter]');
    const contextTabs = document.querySelectorAll('[data-context-tab]');

    const megaMenu = document.querySelector('[data-mega-menu]');
    const megaTriggers = megaMenu ? megaMenu.querySelectorAll('[data-mega-trigger]') : [];
    const megaPanels = megaMenu ? megaMenu.querySelectorAll('[data-mega-panel]') : [];
    const megaOverlay = document.querySelector('[data-mega-overlay]');
    const megaMobileToggle = document.querySelector('[data-mega-mobile-toggle]');
    const desktopBreakpoint = window.matchMedia('(min-width: 992px)');

    let activeMegaId = null;

    function tryParse(json, fallback) {
        try {
            const parsed = JSON.parse(json);
            return Array.isArray(parsed) ? parsed : fallback;
        } catch (error) {
            console.error('Unable to parse stored data', error);
            return fallback;
        }
    }

    function loadPinned() {
        return tryParse(localStorage.getItem(pinnedKey), []);
    }

    function savePinned(items) {
        localStorage.setItem(pinnedKey, JSON.stringify(items));
        document.dispatchEvent(new CustomEvent('pinned:updated', { detail: items }));
    }

    function loadSavedSearches() {
        return tryParse(localStorage.getItem(savedSearchKey), []);
    }

    function saveSavedSearches(items) {
        localStorage.setItem(savedSearchKey, JSON.stringify(items));
        document.dispatchEvent(new CustomEvent('saved-searches:updated', { detail: items }));
    }

    function lockBodyScroll(shouldLock) {
        body.classList.toggle('overflow-hidden', shouldLock);
    }

    function openPanel(panel) {
        if (!panel) {
            return;
        }
        panel.classList.add('is-open');
        panel.setAttribute('aria-hidden', 'false');
        lockBodyScroll(true);
    }

    function closePanel(panel) {
        if (!panel) {
            return;
        }
        panel.classList.remove('is-open');
        panel.setAttribute('aria-hidden', 'true');
        lockBodyScroll(anyPanelOpen());
    }

    function anyPanelOpen() {
        return (
            (workspacePanel && workspacePanel.classList.contains('is-open')) ||
            (globalSearch && globalSearch.classList.contains('is-open')) ||
            (megaMenu && (megaMenu.classList.contains('is-open') || activeMegaId !== null))
        );
    }

    function syncMegaOverlay() {
        if (!megaOverlay) {
            return;
        }
        const isDesktop = desktopBreakpoint.matches;
        const shouldShow = isDesktop
            ? activeMegaId !== null
            : megaMenu && megaMenu.classList.contains('is-open');
        megaOverlay.classList.toggle('is-visible', shouldShow);
    }

    function setMegaActive(id) {
        if (!megaMenu) {
            return;
        }
        activeMegaId = id;
        megaTriggers.forEach((trigger) => {
            const targetId = trigger.getAttribute('data-mega-target');
            const isActive = targetId === id;
            trigger.classList.toggle('is-active', isActive);
            trigger.setAttribute('aria-expanded', String(isActive));
        });
        megaPanels.forEach((panel) => {
            const isActive = id ? panel.id === `mega-panel-${id}` : false;
            panel.classList.toggle('is-active', isActive);
            panel.setAttribute('aria-hidden', isActive ? 'false' : 'true');
        });
        megaMenu.classList.toggle('has-active', Boolean(id));

        if (id && desktopBreakpoint.matches) {
            lockBodyScroll(true);
        }
        if (!id) {
            lockBodyScroll(anyPanelOpen());
        }
        syncMegaOverlay();
    }

    function clearMegaActive() {
        setMegaActive(null);
    }

    function openMegaMenu(targetId) {
        if (!megaMenu) {
            return;
        }
        megaMenu.classList.add('is-open');
        if (megaMobileToggle) {
            megaMobileToggle.setAttribute('aria-expanded', 'true');
        }
        const defaultId = targetId || (megaTriggers[0] && megaTriggers[0].getAttribute('data-mega-target'));
        if (defaultId) {
            setMegaActive(defaultId);
        } else {
            lockBodyScroll(true);
            syncMegaOverlay();
        }

        if (!desktopBreakpoint.matches) {
            lockBodyScroll(true);
            syncMegaOverlay();
        }
    }

    function closeMegaMenu() {
        if (!megaMenu) {
            return;
        }
        megaMenu.classList.remove('is-open');
        if (megaMobileToggle) {
            megaMobileToggle.setAttribute('aria-expanded', 'false');
        }
        clearMegaActive();
        lockBodyScroll(anyPanelOpen());
        syncMegaOverlay();
    }

    function closeAllPanels() {
        closeMegaMenu();
        closePanel(workspacePanel);
        closePanel(globalSearch);
        closeMegaPanels();
        if (workspaceBackdrop) {
            workspaceBackdrop.classList.remove('is-visible');
        }
        workspaceToggles.forEach((toggle) => {
            toggle.setAttribute('aria-expanded', 'false');
        });
    }

    function closeMegaPanels() {
        megaPanels.forEach((panel) => {
            if (!panel.hidden) {
                panel.hidden = true;
            }
            panel.classList.remove('is-open');
            const item = panel.closest('[data-mega-item]');
            if (item) {
                item.classList.remove('is-open');
            }
        });
        megaToggles.forEach((toggle) => {
            toggle.setAttribute('aria-expanded', 'false');
            const item = toggle.closest('[data-mega-item]');
            if (item) {
                item.classList.remove('is-open');
            }
        });
    }

    function openMegaPanel(id, trigger) {
        const panel = document.querySelector(`[data-mega-panel="${id}"]`);
        if (!panel) {
            return;
        }
        const alreadyOpen = !panel.hidden;
        closeMegaPanels();
        if (alreadyOpen) {
            return;
        }
        panel.hidden = false;
        panel.classList.add('is-open');
        const item = trigger ? trigger.closest('[data-mega-item]') : panel.closest('[data-mega-item]');
        if (item) {
            item.classList.add('is-open');
        }
        if (trigger) {
            trigger.setAttribute('aria-expanded', 'true');
        }
    }

    function isMegaOpen() {
        return Array.from(megaPanels).some((panel) => !panel.hidden);
    }

    function updateMegaPreview(trigger) {
        if (!megaPreview || !trigger) {
            return;
        }
        const label = trigger.getAttribute('data-preview-label') || trigger.textContent;
        const summary = trigger.getAttribute('data-preview-summary');
        const badge = trigger.getAttribute('data-preview-badge');
        const badgeClass = trigger.getAttribute('data-preview-badge-class');

        if (megaPreviewTitle && label) {
            megaPreviewTitle.textContent = label;
        }
        if (megaPreviewSummary && summary) {
            megaPreviewSummary.textContent = summary;
        }
        if (megaPreviewLink) {
            const href = trigger.getAttribute('href');
            if (href) {
                megaPreviewLink.setAttribute('href', href);
            }
        }
        if (megaPreviewBadge) {
            if (badgeClass) {
                megaPreviewBadge.className = `mega-preview__badge badge ${badgeClass}`;
            }
            if (badge) {
                megaPreviewBadge.textContent = badge;
            }
        }
    }

    function toggleWorkspace(trigger) {
        if (!workspacePanel) {
            return;
        }
        const isOpen = workspacePanel.classList.contains('is-open');
        closeAllPanels();
        if (!isOpen) {
            openPanel(workspacePanel);
            if (workspaceBackdrop) {
                workspaceBackdrop.classList.add('is-visible');
            }
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'true');
            }
        }
    }

    function toggleSearch() {
        if (!globalSearch) {
            return;
        }
        const isOpen = globalSearch.classList.contains('is-open');
        closeAllPanels();
        if (!isOpen) {
            openPanel(globalSearch);
        }
    }

    function renderPinned() {
        const pinnedItems = loadPinned();

        if (pinnedList) {
            pinnedList.innerHTML = '';
            pinnedItems.forEach((item) => {
                const col = document.createElement('div');
                col.className = 'col-12 col-md-6';

                const card = document.createElement('div');
                card.className = 'pinned-card';

                const name = document.createElement('span');
                name.className = 'pinned-card__name';
                name.textContent = item.name;

                const actions = document.createElement('div');
                actions.className = 'pinned-card__actions';

                const link = document.createElement('a');
                link.className = 'btn btn-sm btn-outline-primary';
                link.href = item.url;
                link.textContent = 'Ouvrir';

                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'btn btn-sm btn-outline-secondary';
                remove.innerHTML = '<i class="bi bi-x-lg"></i>';
                remove.addEventListener('click', () => {
                    savePinned(pinnedItems.filter((entry) => entry.name !== item.name));
                });

                actions.append(link, remove);
                card.append(name, actions);
                col.append(card);
                pinnedList.append(col);
            });

            if (pinnedEmpty) {
                pinnedEmpty.classList.toggle('d-none', pinnedItems.length > 0);
                pinnedEmpty.classList.toggle('d-block', pinnedItems.length === 0);
            }
        }

        pinnedSummaries.forEach((summary) => {
            summary.innerHTML = '';
            if (pinnedItems.length) {
                summary.classList.add('pinned-summary');
                pinnedItems.forEach((item) => {
                    const chip = document.createElement('a');
                    chip.className = 'pinned-summary__chip';
                    chip.href = item.url;
                    chip.textContent = item.name;
                    summary.append(chip);
                });
            } else {
                summary.classList.remove('pinned-summary');
                summary.textContent = 'Épinglez des catégories pour les retrouver ici.';
            }
        });

        pinnedButtons.forEach((button) => {
            const card = button.closest('[data-category-card]');
            if (!card) {
                return;
            }
            const name = card.getAttribute('data-category-name');
            const isPinned = pinnedItems.some((item) => item.name === name);
            button.classList.toggle('btn-outline-secondary', !isPinned);
            button.classList.toggle('btn-outline-danger', isPinned);
            button.setAttribute('aria-pressed', String(isPinned));
            button.innerHTML = isPinned
                ? '<i class="bi bi-pin-angle-fill"></i><span class="ms-1">Épinglé</span>'
                : '<i class="bi bi-pin-angle"></i><span class="ms-1">Épingler</span>';
        });
    }

    function handlePin(button) {
        const card = button.closest('[data-category-card]');
        if (!card) {
            return;
        }
        const name = card.getAttribute('data-category-name');
        const url = card.getAttribute('data-category-url');
        if (!name || !url) {
            return;
        }
        const pinnedItems = loadPinned();
        const exists = pinnedItems.some((item) => item.name === name);
        if (exists) {
            savePinned(pinnedItems.filter((item) => item.name !== name));
        } else {
            const next = [{ name, url }, ...pinnedItems.filter((item) => item.name !== name)];
            savePinned(next.slice(0, 8));
        }
    }

    function renderSavedSearches() {
        const items = loadSavedSearches();
        const destination = (searchForm && searchForm.getAttribute('action')) || 'Customer/shop.php';

        savedSearchContainers.forEach((container) => {
            container.innerHTML = '';
            if (!items.length) {
                if (container.dataset.placeholder !== 'false') {
                    const empty = document.createElement('span');
                    empty.className = 'saved-search-empty';
                    empty.textContent = 'Aucune recherche enregistrée';
                    container.append(empty);
                }
                return;
            }

            items.forEach((term) => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'saved-search-chip';
                button.textContent = term;
                button.addEventListener('click', () => {
                    const url = new URL(destination, window.location.origin);
                    url.searchParams.set('q', term);
                    window.location.href = url.toString();
                });
                container.append(button);
            });
        });

        if (savedPlaceholder) {
            savedPlaceholder.classList.toggle('d-none', items.length > 0);
        }
    }

    function handleSaveSearch() {
        if (!searchInput) {
            return;
        }
        const term = searchInput.value.trim();
        if (!term) {
            return;
        }
        const items = loadSavedSearches();
        if (!items.includes(term)) {
            const updated = [term, ...items].slice(0, 6);
            saveSavedSearches(updated);
        }
    }

    function handleClearSearches() {
        saveSavedSearches([]);
    }

    function applyFilter(filter) {
        const normalized = (filter || '').toLowerCase();
        productCards.forEach((card) => {
            const category = (card.getAttribute('data-category') || '').toLowerCase();
            const tags = (card.getAttribute('data-tags') || '').split(',').map((tag) => tag.trim().toLowerCase()).filter(Boolean);
            let visible = false;
            if (!normalized || normalized === 'all') {
                visible = true;
            } else if (['promo', 'top', 'nouveau', 'new'].includes(normalized)) {
                visible = tags.includes(normalized) || (normalized === 'nouveau' && tags.includes('new'));
            } else {
                visible = category === normalized;
            }
            card.classList.toggle('not-active-prod', !visible);
        });
    }

    function setActive(elements, value, attribute) {
        elements.forEach((element) => {
            const elementValue = (element.getAttribute(attribute) || '').toLowerCase();
            const targetValue = (value || 'all').toLowerCase();
            element.classList.toggle('active', elementValue === targetValue);
        });
    }

    function initFiltersFromUrl() {
        if (!productCards.length) {
            return;
        }
        const params = new URLSearchParams(window.location.search);
        let initial = params.get('id');
        if (params.get('promo') === '1') {
            initial = 'promo';
        } else if (params.get('tag')) {
            initial = params.get('tag');
        }
        applyFilter(initial || 'all');
        setActive(filterPills, initial || 'all', 'data-filter');
        setActive(contextTabs, initial || 'all', 'data-context-tab');
    }

    if (megaMenu) {
        megaTriggers.forEach((trigger) => {
            const targetId = trigger.getAttribute('data-mega-target');
            trigger.addEventListener('click', (event) => {
                event.preventDefault();
                const isDesktop = desktopBreakpoint.matches;
                const isActive = activeMegaId === targetId;

                closePanel(workspacePanel);
                closePanel(globalSearch);
                if (workspaceBackdrop) {
                    workspaceBackdrop.classList.remove('is-visible');
                }
                workspaceToggles.forEach((button) => {
                    button.setAttribute('aria-expanded', 'false');
                });

                if (!isDesktop && !megaMenu.classList.contains('is-open')) {
                    openMegaMenu(targetId);
                    return;
                }

                if (!isDesktop) {
                    if (isActive) {
                        clearMegaActive();
                    } else {
                        setMegaActive(targetId);
                    }
                    return;
                }

                if (isActive) {
                    clearMegaActive();
                } else {
                    setMegaActive(targetId);
                }
            });

            trigger.addEventListener('mouseenter', () => {
                if (desktopBreakpoint.matches) {
                    setMegaActive(targetId);
                }
            });

            trigger.addEventListener('focus', () => {
                if (desktopBreakpoint.matches) {
                    setMegaActive(targetId);
                }
            });
        });

        megaMenu.addEventListener('mouseleave', () => {
            if (desktopBreakpoint.matches) {
                clearMegaActive();
            }
        });

        megaMenu.addEventListener('focusout', (event) => {
            if (desktopBreakpoint.matches && megaMenu && !megaMenu.contains(event.relatedTarget)) {
                clearMegaActive();
            }
        });
    }

    if (megaOverlay) {
        megaOverlay.addEventListener('click', () => {
            if (megaMenu && (megaMenu.classList.contains('is-open') || activeMegaId !== null)) {
                closeMegaMenu();
            }
        });
    }

    if (megaMobileToggle) {
        megaMobileToggle.addEventListener('click', (event) => {
            event.preventDefault();
            closePanel(workspacePanel);
            closePanel(globalSearch);
            if (workspaceBackdrop) {
                workspaceBackdrop.classList.remove('is-visible');
            }
            workspaceToggles.forEach((button) => {
                button.setAttribute('aria-expanded', 'false');
            });
            if (megaMenu && megaMenu.classList.contains('is-open')) {
                closeMegaMenu();
            } else {
                openMegaMenu();
            }
        });
    }

    if (typeof desktopBreakpoint.addEventListener === 'function') {
        desktopBreakpoint.addEventListener('change', (event) => {
            if (event.matches) {
                if (megaMenu) {
                    megaMenu.classList.remove('is-open');
                }
                clearMegaActive();
                if (megaMobileToggle) {
                    megaMobileToggle.setAttribute('aria-expanded', 'false');
                }
                syncMegaOverlay();
                lockBodyScroll(anyPanelOpen());
            } else {
                closeMegaMenu();
            }
        });
    } else if (typeof desktopBreakpoint.addListener === 'function') {
        desktopBreakpoint.addListener((event) => {
            if (event.matches) {
                if (megaMenu) {
                    megaMenu.classList.remove('is-open');
                }
                clearMegaActive();
                if (megaMobileToggle) {
                    megaMobileToggle.setAttribute('aria-expanded', 'false');
                }
                syncMegaOverlay();
                lockBodyScroll(anyPanelOpen());
            } else {
                closeMegaMenu();
            }
        });
    }

    workspaceToggles.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            toggleWorkspace(button);
        });
    });

    megaToggles.forEach((toggle) => {
        toggle.addEventListener('click', (event) => {
            event.preventDefault();
            const id = toggle.getAttribute('data-mega-toggle');
            if (!id) {
                return;
            }
            const panel = document.querySelector(`[data-mega-panel="${id}"]`);
            const isOpen = panel && !panel.hidden;
            if (isOpen) {
                closeMegaPanels();
            } else {
                openMegaPanel(id, toggle);
            }
        });
    });

    megaPreviewTriggers.forEach((trigger) => {
        trigger.addEventListener('mouseenter', () => updateMegaPreview(trigger));
        trigger.addEventListener('focus', () => updateMegaPreview(trigger));
    });

    if (megaNav) {
        document.addEventListener('click', (event) => {
            if (!megaNav.contains(event.target)) {
                closeMegaPanels();
            }
        });
    }

    window.addEventListener('resize', closeMegaPanels);

    if (workspaceBackdrop) {
        workspaceBackdrop.addEventListener('click', () => {
            closeAllPanels();
        });
    }

    searchToggles.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            toggleSearch();
            if (globalSearch && globalSearch.classList.contains('is-open') && searchInput) {
                setTimeout(() => searchInput.focus(), 120);
            }
        });
    });

    pinnedButtons.forEach((button) => {
        button.addEventListener('click', () => handlePin(button));
    });

    if (pinnedClear) {
        pinnedClear.addEventListener('click', () => {
            savePinned([]);
        });
    }

    if (saveSearchButton) {
        saveSearchButton.addEventListener('click', handleSaveSearch);
    }

    if (clearSearchesButton) {
        clearSearchesButton.addEventListener('click', handleClearSearches);
    }

    filterPills.forEach((pill) => {
        pill.addEventListener('click', () => {
            const value = pill.getAttribute('data-filter');
            applyFilter(value);
            setActive(filterPills, value, 'data-filter');
            setActive(contextTabs, value, 'data-context-tab');
        });
    });

    contextTabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const value = tab.getAttribute('data-context-tab');
            applyFilter(value);
            setActive(contextTabs, value, 'data-context-tab');
            setActive(filterPills, value, 'data-filter');
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && (anyPanelOpen() || isMegaOpen())) {
            if (isMegaOpen()) {
                closeMegaPanels();
            }
            if (anyPanelOpen()) {
                closeAllPanels();
            }
            return;
        }

        const key = event.key.toLowerCase();
        if ((event.ctrlKey || event.metaKey) && key === 'k') {
            event.preventDefault();
            toggleSearch();
            if (globalSearch && globalSearch.classList.contains('is-open') && searchInput) {
                setTimeout(() => searchInput.focus(), 120);
            }
        }
    });

    document.addEventListener('pinned:updated', renderPinned);
    document.addEventListener('saved-searches:updated', renderSavedSearches);

    renderPinned();
    renderSavedSearches();
    initFiltersFromUrl();
})();
