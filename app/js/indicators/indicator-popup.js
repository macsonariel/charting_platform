/**
 * Indicator Popup Controller
 * Handles UI for indicators button, dropdown, and modal
 */

const IndicatorPopup = (function () {
    let isInitialized = false;
    let currentCategory = 'favorites';
    let searchQuery = '';

    // DOM Elements (cached after init)
    let elements = {};

    // Initialize the popup
    function init() {
        if (isInitialized) return;

        // Cache DOM elements
        elements = {
            mainBtn: document.getElementById('indicatorsBtn'),
            dropdownBtn: document.getElementById('indicatorsFavDropdown'),
            favoritesMenu: document.getElementById('indicatorsFavoritesMenu'),
            modalOverlay: document.getElementById('indicatorsModalOverlay'),
            modal: document.getElementById('indicatorsModal'),
            modalClose: document.getElementById('indicatorsModalClose'),
            searchInput: document.getElementById('indicatorsSearch'),
            categoriesContainer: document.getElementById('indicatorsCategories'),
            indicatorsGrid: document.getElementById('indicatorsGrid'),
            activeChipsContainer: document.getElementById('activeIndicatorsChips')
        };

        // Validate required elements
        if (!elements.mainBtn) {
            console.warn('Indicators button not found, popup not initialized');
            return;
        }

        // Bind events
        bindEvents();

        // Listen for indicator manager changes
        IndicatorManager.addListener(handleIndicatorChange);

        // Initial render
        renderFavoritesDropdown();
        renderActiveChips();

        isInitialized = true;
        console.log('✅ IndicatorPopup initialized');
    }

    // Bind all event handlers
    function bindEvents() {
        // Main button - opens modal
        elements.mainBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            openModal();
        });

        // Dropdown button - opens favorites
        elements.dropdownBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFavoritesDropdown();
        });

        // Modal close button
        elements.modalClose?.addEventListener('click', closeModal);

        // Modal overlay click to close
        elements.modalOverlay?.addEventListener('click', (e) => {
            if (e.target === elements.modalOverlay) {
                closeModal();
            }
        });

        // Search input
        elements.searchInput?.addEventListener('input', (e) => {
            searchQuery = e.target.value;
            renderIndicatorsList();
        });

        // Close dropdown on outside click
        document.addEventListener('click', (e) => {
            if (elements.favoritesMenu?.classList.contains('show')) {
                if (!elements.favoritesMenu.contains(e.target) &&
                    !elements.dropdownBtn?.contains(e.target)) {
                    closeFavoritesDropdown();
                }
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (elements.modalOverlay?.classList.contains('show')) {
                    closeModal();
                } else if (elements.favoritesMenu?.classList.contains('show')) {
                    closeFavoritesDropdown();
                }
            }
        });

        // Browse all button in favorites dropdown
        const browseBtn = elements.favoritesMenu?.querySelector('.favorites-browse-btn');
        browseBtn?.addEventListener('click', () => {
            closeFavoritesDropdown();
            openModal();
        });
    }

    // Toggle favorites dropdown
    function toggleFavoritesDropdown() {
        if (elements.favoritesMenu?.classList.contains('show')) {
            closeFavoritesDropdown();
        } else {
            openFavoritesDropdown();
        }
    }

    function openFavoritesDropdown() {
        renderFavoritesDropdown();
        elements.favoritesMenu?.classList.add('show');
        elements.dropdownBtn?.classList.add('active');
    }

    function closeFavoritesDropdown() {
        elements.favoritesMenu?.classList.remove('show');
        elements.dropdownBtn?.classList.remove('active');
    }

    // Render favorites dropdown content
    function renderFavoritesDropdown() {
        const listContainer = elements.favoritesMenu?.querySelector('.favorites-list');
        if (!listContainer) return;

        const favorites = IndicatorManager.getFavorites();

        if (favorites.length === 0) {
            listContainer.innerHTML = `
                <div class="favorites-empty">
                    <div class="favorites-empty-icon">⭐</div>
                    <div>No favorite indicators yet</div>
                    <div style="margin-top: 4px; opacity: 0.7;">Star indicators to add them here</div>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = favorites.map(indicator => {
            const isActive = IndicatorManager.isActive(indicator.id);
            const paramDisplay = Object.entries(indicator.params || {})
                .map(([key, val]) => `${indicator.paramLabels?.[key] || key}: ${val}`)
                .join(' | ');

            return `
                <div class="favorite-indicator-item" data-id="${indicator.id}">
                    <div class="favorite-indicator-toggle ${isActive ? 'active' : ''}" 
                         data-action="toggle" data-id="${indicator.id}"></div>
                    <div class="favorite-indicator-info">
                        <div class="favorite-indicator-name">${indicator.name}</div>
                        ${paramDisplay ? `<div class="favorite-indicator-params">${paramDisplay}</div>` : ''}
                    </div>
                    <button class="favorite-indicator-settings" data-action="settings" data-id="${indicator.id}" title="Settings">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="3"/>
                            <path d="M12 1v6m0 6v6m9-9h-6m-6 0H3"/>
                        </svg>
                    </button>
                </div>
            `;
        }).join('');

        // Bind click events for favorites list
        listContainer.querySelectorAll('[data-action="toggle"]').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = el.dataset.id;
                IndicatorManager.toggleIndicator(id);
            });
        });

        listContainer.querySelectorAll('[data-action="settings"]').forEach(el => {
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = el.dataset.id;
                // TODO: Open settings for this indicator
                console.log('Open settings for:', id);
            });
        });
    }

    // Open modal
    function openModal() {
        currentCategory = 'favorites';
        searchQuery = '';

        if (elements.searchInput) {
            elements.searchInput.value = '';
        }

        renderCategories();
        renderIndicatorsList();

        elements.modalOverlay?.classList.add('show');
        elements.searchInput?.focus();
    }

    // Close modal
    function closeModal() {
        elements.modalOverlay?.classList.remove('show');
    }

    // Render category sidebar
    function renderCategories() {
        if (!elements.categoriesContainer) return;

        const catalog = IndicatorManager.getCatalog();
        const favorites = IndicatorManager.getFavorites();

        let html = `
            <button class="indicators-category-btn ${currentCategory === 'favorites' ? 'active' : ''}" 
                    data-category="favorites">
                <span class="indicators-category-icon">⭐</span>
                <span>Favorites</span>
                <span class="indicators-category-count">${favorites.length}</span>
            </button>
        `;

        for (const [catId, category] of Object.entries(catalog)) {
            const count = category.indicators.length;
            html += `
                <button class="indicators-category-btn ${currentCategory === catId ? 'active' : ''}" 
                        data-category="${catId}">
                    <span class="indicators-category-icon">${category.icon}</span>
                    <span>${category.name}</span>
                    <span class="indicators-category-count">${count}</span>
                </button>
            `;
        }

        elements.categoriesContainer.innerHTML = html;

        // Bind category clicks
        elements.categoriesContainer.querySelectorAll('.indicators-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentCategory = btn.dataset.category;
                renderCategories();
                renderIndicatorsList();
            });
        });
    }

    // Render indicators list/grid
    function renderIndicatorsList() {
        if (!elements.indicatorsGrid) return;

        let indicators = [];
        let title = '';

        if (searchQuery) {
            indicators = IndicatorManager.searchIndicators(searchQuery);
            title = `Search Results`;
        } else if (currentCategory === 'favorites') {
            indicators = IndicatorManager.getFavorites();
            title = 'Favorite Indicators';
        } else {
            indicators = IndicatorManager.getIndicatorsByCategory(currentCategory);
            const catalog = IndicatorManager.getCatalog();
            title = `${catalog[currentCategory]?.icon || ''} ${catalog[currentCategory]?.name || ''} Indicators`;
        }

        // Update header
        const header = elements.indicatorsGrid.closest('.indicators-list-container')?.querySelector('.indicators-list-header');
        if (header) {
            header.innerHTML = `
                <span class="indicators-list-title">${title}</span>
                <span class="indicators-list-count">${indicators.length} indicator${indicators.length !== 1 ? 's' : ''}</span>
            `;
        }

        // Render grid
        if (indicators.length === 0) {
            elements.indicatorsGrid.innerHTML = `
                <div class="indicators-empty-state">
                    <div class="indicators-empty-icon">${currentCategory === 'favorites' ? '⭐' : '🔍'}</div>
                    <div class="indicators-empty-text">
                        ${currentCategory === 'favorites' ? 'No favorite indicators yet' : 'No indicators found'}
                    </div>
                    <div class="indicators-empty-subtext">
                        ${currentCategory === 'favorites' ? 'Star indicators to add them to favorites' : 'Try a different search term'}
                    </div>
                </div>
            `;
            return;
        }

        elements.indicatorsGrid.innerHTML = indicators.map(indicator => {
            const isFavorite = IndicatorManager.isFavorite(indicator.id);
            const isActive = IndicatorManager.isActive(indicator.id);

            const paramChips = Object.entries(indicator.params || {})
                .slice(0, 3) // Limit to 3 params for compact view
                .map(([key, val]) => `<span class="indicator-param-chip">${indicator.paramLabels?.[key] || key}: ${val}</span>`)
                .join('');

            return `
                <div class="indicator-card ${isActive ? 'active' : ''}" data-id="${indicator.id}">
                    <span class="indicator-card-name">${indicator.name}</span>
                    <span class="indicator-card-description">${indicator.description}</span>
                    ${paramChips ? `<div class="indicator-card-params">${paramChips}</div>` : ''}
                    <div class="indicator-card-actions">
                        <button class="indicator-action-btn favorite ${isFavorite ? 'active' : ''}" 
                                data-action="favorite" data-id="${indicator.id}" title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="${isFavorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                            </svg>
                        </button>
                        <button class="indicator-add-btn ${isActive ? 'added' : ''}" data-action="toggle" data-id="${indicator.id}">
                            ${isActive ? '✓' : '+'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Bind events
        elements.indicatorsGrid.querySelectorAll('[data-action="favorite"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                IndicatorManager.toggleFavorite(id);
            });
        });

        elements.indicatorsGrid.querySelectorAll('[data-action="toggle"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                IndicatorManager.toggleIndicator(id);
            });
        });
    }

    // Render active indicator chips in header
    function renderActiveChips() {
        if (!elements.activeChipsContainer) return;

        const active = IndicatorManager.getActiveIndicators();

        if (active.length === 0) {
            elements.activeChipsContainer.innerHTML = '';
            elements.activeChipsContainer.style.display = 'none';
            return;
        }

        elements.activeChipsContainer.style.display = 'flex';
        elements.activeChipsContainer.innerHTML = active.map(indicator => `
            <div class="active-indicator-chip" data-instance="${indicator.instanceId}" title="Click to edit settings">
                <span class="chip-label">${indicator.name}${indicator.params?.period ? `(${indicator.params.period})` : ''}</span>
                <span class="chip-remove" data-action="remove" data-instance="${indicator.instanceId}" title="Remove">×</span>
            </div>
        `).join('');

        // Bind chip click events (open settings)
        elements.activeChipsContainer.querySelectorAll('.active-indicator-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                // Don't open settings if clicking the remove button
                if (e.target.classList.contains('chip-remove')) return;

                const instanceId = chip.dataset.instance;
                if (window.IndicatorSettings?.openSettings) {
                    window.IndicatorSettings.openSettings(instanceId);
                } else {
                    console.warn('IndicatorSettings not loaded');
                }
            });
        });

        // Bind remove events
        elements.activeChipsContainer.querySelectorAll('[data-action="remove"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const instanceId = btn.dataset.instance;
                IndicatorManager.removeIndicator(instanceId);
            });
        });
    }

    // Handle indicator manager state changes
    function handleIndicatorChange(event, data) {
        console.log('Indicator event:', event, data);

        // Update all UI components
        renderFavoritesDropdown();
        renderActiveChips();

        // If modal is open, update it too
        if (elements.modalOverlay?.classList.contains('show')) {
            renderCategories();
            renderIndicatorsList();
        }

        // Dispatch custom event for chart integration
        document.dispatchEvent(new CustomEvent('indicatorChange', {
            detail: { event, data }
        }));
    }

    // Public API
    return {
        init,
        openModal,
        closeModal,
        openFavoritesDropdown,
        closeFavoritesDropdown
    };
})();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => IndicatorPopup.init());
} else {
    // DOM already loaded, wait a tick for other scripts
    setTimeout(() => IndicatorPopup.init(), 100);
}
