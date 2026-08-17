/**
 * Indicator Settings Modal
 * Provides a settings modal for configuring indicator parameters
 * Tabs: Inputs, Style, Visibility
 */

const IndicatorSettings = (function () {
    let isInitialized = false;
    let currentInstanceId = null;
    let currentIndicator = null;
    let currentTab = 'inputs';

    // DOM elements
    let elements = {};

    // Default settings structure
    const DEFAULT_STYLE = {
        color: null, // null = auto-assign
        lineWidth: 2,
        lineStyle: 'solid', // solid, dashed, dotted
        showLabel: true
    };

    const DEFAULT_VISIBILITY = {
        timeframes: ['1m', '5m', '15m', '1h', '4h', '1d'] // all visible by default
    };

    const SOURCE_OPTIONS = [
        { value: 'close', label: 'Close' },
        { value: 'open', label: 'Open' },
        { value: 'high', label: 'High' },
        { value: 'low', label: 'Low' },
        { value: 'hl2', label: 'HL2 (High+Low)/2' },
        { value: 'hlc3', label: 'HLC3 (High+Low+Close)/3' },
        { value: 'ohlc4', label: 'OHLC4 (Open+High+Low+Close)/4' }
    ];

    const TIMEFRAME_OPTIONS = ['1m', '5m', '15m', '1h', '4h', '1d'];

    const LINE_STYLE_OPTIONS = [
        { value: 'solid', label: 'Solid ───' },
        { value: 'dashed', label: 'Dashed - - -' },
        { value: 'dotted', label: 'Dotted ···' }
    ];

    /**
     * Initialize the settings modal
     */
    function init() {
        if (isInitialized) return;

        // Create modal HTML if not exists
        createModalHTML();

        // Cache DOM elements
        cacheElements();

        // Bind events
        bindEvents();

        isInitialized = true;
        console.log('✅ IndicatorSettings initialized');
    }

    /**
     * Create modal HTML structure
     */
    function createModalHTML() {
        // Check if already exists
        if (document.getElementById('indicatorSettingsOverlay')) return;

        const modalHTML = `
            <div class="indicator-settings-overlay" id="indicatorSettingsOverlay">
                <div class="indicator-settings-modal" id="indicatorSettingsModal">
                    <div class="settings-header">
                        <h3 id="settingsTitle">Indicator Settings</h3>
                        <button class="settings-close-btn" id="settingsCloseBtn">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    
                    <div class="settings-tabs">
                        <button class="settings-tab active" data-tab="inputs">Inputs</button>
                        <button class="settings-tab" data-tab="style">Style</button>
                        <button class="settings-tab" data-tab="visibility">Visibility</button>
                    </div>
                    
                    <div class="settings-content" id="settingsContent">
                        <!-- Content will be dynamically populated -->
                    </div>
                    
                    <div class="settings-footer">
                        <button class="settings-btn settings-btn--reset" id="settingsResetBtn">Reset</button>
                        <div class="settings-footer-right">
                            <button class="settings-btn settings-btn--cancel" id="settingsCancelBtn">Cancel</button>
                            <button class="settings-btn settings-btn--ok" id="settingsOkBtn">OK</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    /**
     * Cache DOM elements
     */
    function cacheElements() {
        elements = {
            overlay: document.getElementById('indicatorSettingsOverlay'),
            modal: document.getElementById('indicatorSettingsModal'),
            title: document.getElementById('settingsTitle'),
            content: document.getElementById('settingsContent'),
            closeBtn: document.getElementById('settingsCloseBtn'),
            resetBtn: document.getElementById('settingsResetBtn'),
            cancelBtn: document.getElementById('settingsCancelBtn'),
            okBtn: document.getElementById('settingsOkBtn'),
            tabs: document.querySelectorAll('.settings-tab')
        };
    }

    /**
     * Bind event handlers
     */
    function bindEvents() {
        // Close button
        elements.closeBtn?.addEventListener('click', closeSettings);
        elements.cancelBtn?.addEventListener('click', closeSettings);

        // OK button
        elements.okBtn?.addEventListener('click', saveAndClose);

        // Reset button
        elements.resetBtn?.addEventListener('click', resetToDefaults);

        // Overlay click to close
        elements.overlay?.addEventListener('click', (e) => {
            if (e.target === elements.overlay) {
                closeSettings();
            }
        });

        // Tab switching
        elements.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                switchTab(tab.dataset.tab);
            });
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && elements.overlay?.classList.contains('show')) {
                closeSettings();
            }
        });
    }

    /**
     * Switch between tabs
     */
    function switchTab(tabName) {
        currentTab = tabName;

        // Update tab buttons
        elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Render content
        renderTabContent();
    }

    /**
     * Render content for current tab
     */
    function renderTabContent() {
        if (!currentIndicator) return;

        switch (currentTab) {
            case 'inputs':
                renderInputsTab();
                break;
            case 'style':
                renderStyleTab();
                break;
            case 'visibility':
                renderVisibilityTab();
                break;
        }
    }

    /**
     * Render Inputs tab
     */
    function renderInputsTab() {
        const params = currentIndicator.params || {};

        // Build inputs based on indicator type
        let html = '<div class="settings-inputs">';

        // Period/Length input (most common)
        if ('period' in params || currentIndicator.id === 'sma' || currentIndicator.id === 'ema') {
            html += `
                <div class="settings-row">
                    <label>Length</label>
                    <input type="number" class="settings-input" id="inputPeriod" 
                           value="${params.period || 20}" min="1" max="500" step="1">
                </div>
            `;
        }

        // Source input
        html += `
            <div class="settings-row">
                <label>Source</label>
                <select class="settings-select" id="inputSource">
                    ${SOURCE_OPTIONS.map(opt => `
                        <option value="${opt.value}" ${(params.source || 'close') === opt.value ? 'selected' : ''}>
                            ${opt.label}
                        </option>
                    `).join('')}
                </select>
            </div>
        `;

        // Offset input
        html += `
            <div class="settings-row">
                <label>Offset</label>
                <input type="number" class="settings-input" id="inputOffset" 
                       value="${params.offset || 0}" min="-100" max="100" step="1">
            </div>
        `;

        html += '</div>';
        elements.content.innerHTML = html;
    }

    /**
     * Render Style tab
     */
    function renderStyleTab() {
        const style = currentIndicator.style || DEFAULT_STYLE;
        const color = style.color || IndicatorRenderer?.getIndicatorColor(currentInstanceId) || '#2962ff';

        let html = '<div class="settings-style">';

        // Color picker
        html += `
            <div class="settings-row">
                <label>Color</label>
                <div class="color-input-wrapper">
                    <input type="color" class="settings-color" id="styleColor" value="${color}">
                    <span class="color-preview" style="background: ${color}"></span>
                </div>
            </div>
        `;

        // Line width
        html += `
            <div class="settings-row">
                <label>Line Width</label>
                <input type="range" class="settings-range" id="styleLineWidth" 
                       value="${style.lineWidth || 2}" min="1" max="5" step="1">
                <span class="range-value" id="lineWidthValue">${style.lineWidth || 2}</span>
            </div>
        `;

        // Line style
        html += `
            <div class="settings-row">
                <label>Line Style</label>
                <select class="settings-select" id="styleLineStyle">
                    ${LINE_STYLE_OPTIONS.map(opt => `
                        <option value="${opt.value}" ${(style.lineStyle || 'solid') === opt.value ? 'selected' : ''}>
                            ${opt.label}
                        </option>
                    `).join('')}
                </select>
            </div>
        `;

        // Show last value label toggle
        html += `
            <div class="settings-row">
                <label>Show Price Label</label>
                <label class="toggle-switch">
                    <input type="checkbox" id="styleShowLabel" ${style.showLabel !== false ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
            </div>
        `;

        html += '</div>';
        elements.content.innerHTML = html;

        // Bind range input display
        const rangeInput = document.getElementById('styleLineWidth');
        const rangeValue = document.getElementById('lineWidthValue');
        rangeInput?.addEventListener('input', () => {
            rangeValue.textContent = rangeInput.value;
        });
    }

    /**
     * Render Visibility tab
     */
    function renderVisibilityTab() {
        const visibility = currentIndicator.visibility || DEFAULT_VISIBILITY;
        const enabledTimeframes = visibility.timeframes || TIMEFRAME_OPTIONS;

        let html = '<div class="settings-visibility">';

        html += '<p class="settings-description">Show indicator on these timeframes:</p>';

        html += '<div class="timeframe-checkboxes">';
        TIMEFRAME_OPTIONS.forEach(tf => {
            const isChecked = enabledTimeframes.includes(tf);
            html += `
                <label class="checkbox-label">
                    <input type="checkbox" class="timeframe-checkbox" data-tf="${tf}" ${isChecked ? 'checked' : ''}>
                    <span>${tf.toUpperCase()}</span>
                </label>
            `;
        });
        html += '</div>';

        // Select all / Deselect all
        html += `
            <div class="visibility-actions">
                <button class="settings-link-btn" id="selectAllTf">Select All</button>
                <button class="settings-link-btn" id="deselectAllTf">Deselect All</button>
            </div>
        `;

        html += '</div>';
        elements.content.innerHTML = html;

        // Bind select/deselect all
        document.getElementById('selectAllTf')?.addEventListener('click', () => {
            document.querySelectorAll('.timeframe-checkbox').forEach(cb => cb.checked = true);
        });
        document.getElementById('deselectAllTf')?.addEventListener('click', () => {
            document.querySelectorAll('.timeframe-checkbox').forEach(cb => cb.checked = false);
        });
    }

    /**
     * Collect current values from form
     */
    function collectValues() {
        const values = {
            params: { ...currentIndicator.params },
            style: { ...currentIndicator.style },
            visibility: { ...currentIndicator.visibility }
        };

        // Inputs tab values
        const periodInput = document.getElementById('inputPeriod');
        const sourceInput = document.getElementById('inputSource');
        const offsetInput = document.getElementById('inputOffset');

        if (periodInput) values.params.period = parseInt(periodInput.value, 10);
        if (sourceInput) values.params.source = sourceInput.value;
        if (offsetInput) values.params.offset = parseInt(offsetInput.value, 10);

        // Style tab values
        const colorInput = document.getElementById('styleColor');
        const lineWidthInput = document.getElementById('styleLineWidth');
        const lineStyleInput = document.getElementById('styleLineStyle');
        const showLabelInput = document.getElementById('styleShowLabel');

        if (colorInput) values.style.color = colorInput.value;
        if (lineWidthInput) values.style.lineWidth = parseInt(lineWidthInput.value, 10);
        if (lineStyleInput) values.style.lineStyle = lineStyleInput.value;
        if (showLabelInput) values.style.showLabel = showLabelInput.checked;

        // Visibility tab values
        const timeframeCheckboxes = document.querySelectorAll('.timeframe-checkbox');
        if (timeframeCheckboxes.length > 0) {
            values.visibility.timeframes = Array.from(timeframeCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => cb.dataset.tf);
        }

        return values;
    }

    /**
     * Open settings modal for an indicator
     * @param {string} instanceId - Indicator instance ID
     */
    function openSettings(instanceId) {
        if (!isInitialized) init();

        currentInstanceId = instanceId;

        // Get indicator data from manager
        const activeIndicators = IndicatorManager?.getActiveIndicators() || [];
        currentIndicator = activeIndicators.find(ind => ind.instanceId === instanceId);

        if (!currentIndicator) {
            console.warn('Indicator not found:', instanceId);
            return;
        }

        // Ensure style and visibility objects exist
        currentIndicator.style = currentIndicator.style || { ...DEFAULT_STYLE };
        currentIndicator.visibility = currentIndicator.visibility || { ...DEFAULT_VISIBILITY };

        // Set title
        const displayName = currentIndicator.name || 'Indicator';
        const period = currentIndicator.params?.period || '';
        elements.title.textContent = `${displayName}${period ? ` (${period})` : ''} Settings`;

        // Reset to inputs tab
        currentTab = 'inputs';
        elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === 'inputs');
        });

        // Render initial content
        renderTabContent();

        // Show modal
        elements.overlay.classList.add('show');
        document.body.style.overflow = 'hidden';

        console.log(`📊 Opened settings for ${instanceId}`);
    }

    /**
     * Close settings modal
     */
    function closeSettings() {
        elements.overlay?.classList.remove('show');
        document.body.style.overflow = '';
        currentInstanceId = null;
        currentIndicator = null;
    }

    /**
     * Save settings and close
     */
    function saveAndClose() {
        if (!currentInstanceId || !currentIndicator) {
            closeSettings();
            return;
        }

        const values = collectValues();

        // Update via IndicatorManager
        if (IndicatorManager?.updateIndicatorParams) {
            // Merge all values into params for now (we can split later)
            const fullParams = {
                ...values.params,
                style: values.style,
                visibility: values.visibility
            };

            IndicatorManager.updateIndicatorParams(currentInstanceId, fullParams);
            console.log(`💾 Saved settings for ${currentInstanceId}:`, values);
        }

        closeSettings();
    }

    /**
     * Reset to default values
     */
    function resetToDefaults() {
        if (!currentIndicator) return;

        // Get default params from catalog
        const catalogDef = IndicatorManager?.getIndicatorById(currentIndicator.id);

        if (catalogDef) {
            currentIndicator.params = { ...catalogDef.params };
            currentIndicator.style = { ...DEFAULT_STYLE };
            currentIndicator.visibility = { ...DEFAULT_VISIBILITY };

            // Re-render current tab
            renderTabContent();
        }
    }

    // Public API
    return {
        init,
        openSettings,
        closeSettings
    };
})();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => IndicatorSettings.init());
} else {
    setTimeout(() => IndicatorSettings.init(), 200);
}

// Expose globally
if (typeof window !== 'undefined') {
    window.IndicatorSettings = IndicatorSettings;
}
