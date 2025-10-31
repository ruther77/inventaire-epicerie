(function () {
    const pinnedKey = 'inventaire_pinned_categories';
    const savedSearchKey = 'inventaire_saved_searches';

    const catalogPanel = document.getElementById('catalogPanel');
    const catalogBackdrop = document.querySelector('[data-catalog-backdrop]');
    const catalogToggles = document.querySelectorAll('[data-catalog-toggle]');
    const searchOverlay = document.getElementById('globalSearch');
    const searchToggles = document.querySelectorAll('[data-search-toggle]');
    const mobileNav = document.getElementById('mobileNavigation');
    const mobileToggles = document.querySelectorAll('[data-mobile-toggle]');
    const pinButtons = document.querySelectorAll('[data-pin-toggle]');
    const pinnedContainer = document.querySelector('[data-pinned-container]');
    const pinnedList = pinnedContainer ? pinnedContainer.querySelector('[data-pinned-list]') : null;
    const pinnedEmptyMessage = pinnedContainer ? pinnedContainer.querySelector('[data-empty-message]') : null;
    const clearPinsButton = pinnedContainer ? pinnedContainer.querySelector('[data-clear-pins]') : null;
    const pinnedSummary = document.querySelector('[data-pinned-summary]');

    const savedSearchContainers = document.querySelectorAll('[data-saved-searches]');
    const savedSearchPlaceholder = document.querySelector('[data-no-saved-search]');
    const saveSearchButton = document.querySelector('[data-save-search]');
    const clearSearchesButton = document.querySelector('[data-clear-searches]');
    const searchInput = document.getElementById('globalSearchInput');

    const quickFilterButtons = document.querySelectorAll('[data-quick-filter]');
    const body = document.body;

    const categoryLinks = {};
    document.querySelectorAll('.catalog-card').forEach((card) => {
        const name = card.getAttribute('data-category-name');
        const link = card.querySelector('.stretched-link');
        if (name && link) {
            categoryLinks[name] = link.getAttribute('href');
        }
    });

    const getPinned = () => {
        try {
            return JSON.parse(localStorage.getItem(pinnedKey) || '[]');
        } catch (error) {
            console.error('Unable to read pinned categories', error);
            return [];
        }
    };

    const setPinned = (items) => {
        localStorage.setItem(pinnedKey, JSON.stringify(items));
        document.dispatchEvent(new CustomEvent('pinned:updated', { detail: items }));
    };

    const getSavedSearches = () => {
        try {
            return JSON.parse(localStorage.getItem(savedSearchKey) || '[]');
        } catch (error) {
            console.error('Unable to read saved searches', error);
            return [];
        }
    };

    const setSavedSearches = (items) => {
        localStorage.setItem(savedSearchKey, JSON.stringify(items));
        document.dispatchEvent(new CustomEvent('saved-searches:updated', { detail: items }));
    };

    const toggleClass = (element, className, force) => {
        if (!element) {
            return;
        }
        if (typeof force === 'boolean') {
            element.classList.toggle(className, force);
        } else {
            element.classList.toggle(className);
        }
    };

    const trapFocus = (element) => {
        if (!element) {
            return;
        }
        if (element.dataset.trapInitialized === 'true') {
            return;
        }
        const focusable = element.querySelectorAll('a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])');
        if (!focusable.length) {
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        const handleKeydown = (event) => {
            if (event.key !== 'Tab') {
                return;
            }
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };

        element.addEventListener('keydown', handleKeydown);
        element.dataset.trapInitialized = 'true';
        first.focus();
    };

    const isCatalogOpen = () => Boolean(catalogPanel && catalogPanel.classList.contains('is-open'));
    const isSearchOpen = () => Boolean(searchOverlay && searchOverlay.classList.contains('is-open'));
    const isMobileOpen = () => Boolean(mobileNav && mobileNav.classList.contains('is-open'));

    function updateBodyScrollLock() {
        if (isCatalogOpen() || isSearchOpen() || isMobileOpen()) {
            body.classList.add('overflow-hidden');
        } else {
            body.classList.remove('overflow-hidden');
        }
    }

    function closeCatalog() {
        toggleClass(catalogPanel, 'is-open', false);
        toggleClass(catalogBackdrop, 'is-visible', false);
        updateBodyScrollLock();
        if (catalogPanel) {
            catalogPanel.setAttribute('aria-hidden', 'true');
            catalogPanel.removeAttribute('data-trap-initialized');
        }
    }

    function closeSearch() {
        toggleClass(searchOverlay, 'is-open', false);
        updateBodyScrollLock();
        if (searchOverlay) {
            searchOverlay.setAttribute('aria-hidden', 'true');
            searchOverlay.removeAttribute('data-trap-initialized');
        }
    }

    function closeMobileNav() {
        toggleClass(mobileNav, 'is-open', false);
        updateBodyScrollLock();
        if (mobileNav) {
            mobileNav.setAttribute('aria-hidden', 'true');
            mobileNav.removeAttribute('data-trap-initialized');
        }
    }

    function openCatalog() {
        closeSearch();
        closeMobileNav();
        toggleClass(catalogPanel, 'is-open', true);
        toggleClass(catalogBackdrop, 'is-visible', true);
        updateBodyScrollLock();
        if (catalogPanel) {
            catalogPanel.setAttribute('aria-hidden', 'false');
            trapFocus(catalogPanel);
        }
    }

    function openSearch() {
        closeCatalog();
        closeMobileNav();
        toggleClass(searchOverlay, 'is-open', true);
        updateBodyScrollLock();
        if (searchOverlay) {
            searchOverlay.setAttribute('aria-hidden', 'false');
            trapFocus(searchOverlay);
        }
    }

    function openMobileNav() {
        closeCatalog();
        closeSearch();
        toggleClass(mobileNav, 'is-open', true);
        updateBodyScrollLock();
        if (mobileNav) {
            mobileNav.setAttribute('aria-hidden', 'false');
            trapFocus(mobileNav);
        }
    }

    catalogToggles.forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
            event.preventDefault();
            if (catalogPanel && catalogPanel.classList.contains('is-open')) {
                closeCatalog();
            } else {
                openCatalog();
            }
        });
    });

    if (catalogBackdrop) {
        catalogBackdrop.addEventListener('click', closeCatalog);
    }

    searchToggles.forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
            event.preventDefault();
            if (searchOverlay && searchOverlay.classList.contains('is-open')) {
                closeSearch();
            } else {
                openSearch();
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    });

    mobileToggles.forEach((trigger) => {
        trigger.addEventListener('click', (event) => {
            event.preventDefault();
            if (mobileNav && mobileNav.classList.contains('is-open')) {
                closeMobileNav();
            } else {
                openMobileNav();
            }
        });
    });

    const updatePinnedSummary = (items) => {
        if (!pinnedSummary) {
            return;
        }
        if (!items.length) {
            pinnedSummary.textContent = 'Aucune section épinglée pour le moment.';
            return;
        }
        const preview = items.slice(0, 3).join(', ');
        const more = items.length > 3 ? ` (+${items.length - 3})` : '';
        pinnedSummary.textContent = `Sections épinglées : ${preview}${more}`;
    };

    const renderPinnedList = () => {
        const pinned = getPinned();
        if (pinnedList) {
            pinnedList.innerHTML = '';
            pinned.forEach((name) => {
                const link = categoryLinks[name] || '#';
                const col = document.createElement('div');
                col.className = 'col-12 col-md-4';
                const anchor = document.createElement('a');
                anchor.className = 'quick-link-chip w-100 justify-content-between';
                anchor.href = link;
                anchor.innerHTML = `<span>${name}</span><i class="bi bi-arrow-up-right"></i>`;
                col.appendChild(anchor);
                pinnedList.appendChild(col);
            });
        }
        if (pinnedEmptyMessage) {
            pinnedEmptyMessage.style.display = pinned.length ? 'none' : '';
        }
        updatePinnedSummary(pinned);
    };

    const syncPinButtons = () => {
        const pinned = getPinned();
        pinButtons.forEach((button) => {
            const card = button.closest('.catalog-card');
            if (!card) {
                return;
            }
            const categoryName = card.getAttribute('data-category-name');
            const isPinned = categoryName && pinned.includes(categoryName);
            button.setAttribute('aria-pressed', isPinned ? 'true' : 'false');
            button.querySelector('i').className = isPinned ? 'bi bi-pin-angle-fill' : 'bi bi-pin-angle';
            button.querySelector('span').textContent = isPinned ? 'Épinglé' : 'Épingler';
            card.classList.toggle('is-pinned', Boolean(isPinned));
        });
    };

    pinButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const card = button.closest('.catalog-card');
            if (!card) {
                return;
            }
            const categoryName = card.getAttribute('data-category-name');
            if (!categoryName) {
                return;
            }
            const pinned = getPinned();
            const index = pinned.indexOf(categoryName);
            if (index === -1) {
                pinned.push(categoryName);
            } else {
                pinned.splice(index, 1);
            }
            setPinned(pinned);
            syncPinButtons();
            renderPinnedList();
        });
    });

    if (clearPinsButton) {
        clearPinsButton.addEventListener('click', () => {
            setPinned([]);
            syncPinButtons();
            renderPinnedList();
        });
    }

    document.addEventListener('pinned:updated', (event) => {
        updatePinnedSummary(event.detail || getPinned());
    });

    const renderSavedSearches = () => {
        const saved = getSavedSearches();
        savedSearchContainers.forEach((container) => {
            if (container.dataset.skipGlobal === 'true') {
                return;
            }
            container.innerHTML = '';
            if (!saved.length) {
                return;
            }
            saved.forEach((term) => {
                const link = document.createElement('a');
                link.className = 'saved-search-chip';
                link.href = `${window.location.origin}${window.location.pathname.includes('shop.php') ? window.location.pathname : '/Customer/shop.php'}?q=${encodeURIComponent(term)}`;
                link.textContent = term;
                container.appendChild(link);
            });
        });
        if (savedSearchPlaceholder) {
            savedSearchPlaceholder.style.display = saved.length ? 'none' : '';
        }
    };

    if (saveSearchButton) {
        saveSearchButton.addEventListener('click', (event) => {
            event.preventDefault();
            if (!searchInput) {
                return;
            }
            const value = searchInput.value.trim();
            if (value.length < 2) {
                searchInput.focus();
                return;
            }
            const saved = getSavedSearches();
            if (!saved.includes(value)) {
                saved.unshift(value);
            }
            setSavedSearches(saved.slice(0, 10));
            renderSavedSearches();
        });
    }

    if (clearSearchesButton) {
        clearSearchesButton.addEventListener('click', (event) => {
            event.preventDefault();
            setSavedSearches([]);
            renderSavedSearches();
        });
    }

    document.addEventListener('saved-searches:updated', renderSavedSearches);

    quickFilterButtons.forEach((button) => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const value = button.getAttribute('data-quick-filter');
            if (!value) {
                return;
            }
            const url = `${window.location.origin}/Customer/shop.php?id=${encodeURIComponent(value)}`;
            window.location.href = url;
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeCatalog();
            closeSearch();
            closeMobileNav();
        }
    });

    renderPinnedList();
    syncPinButtons();
    renderSavedSearches();
})();
