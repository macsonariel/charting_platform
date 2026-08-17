/**
 * Trading Buddy settings and profile UI.
 *
 * Until a production backend is selected, editable values are stored only in
 * this browser. Nothing is sent to a remote account or persistence service.
 */

const LOCAL_SETTINGS_KEY = 'tradingBuddy.localSettings.v1';

const SettingsPage = (() => {
    function init() {
        const container = document.querySelector('.settings-container');
        if (!container || container.dataset.initialized === 'true') return;

        container.dataset.initialized = 'true';
        loadLocalSettings(container);
        initTabs(container);
        initThemeSwitcher(container);
        initEmojiRating(container);
        initProfilePreview(container);
        initSaveButton(container);
    }

    return { init };
})();

window.SettingsPage = SettingsPage;
setTimeout(() => SettingsPage.init(), 0);

function readLocalSettings() {
    try {
        const raw = localStorage.getItem(LOCAL_SETTINGS_KEY);
        return raw ? JSON.parse(raw) : {};
    } catch (error) {
        console.warn('Local settings could not be read:', error);
        return {};
    }
}

function writeLocalSettings(settings) {
    try {
        localStorage.setItem(LOCAL_SETTINGS_KEY, JSON.stringify(settings));
        return true;
    } catch (error) {
        console.error('Local settings could not be saved:', error);
        return false;
    }
}

function loadLocalSettings(container) {
    const settings = readLocalSettings();

    container.querySelectorAll('[data-setting]').forEach((control) => {
        const key = control.dataset.setting;
        if (!Object.prototype.hasOwnProperty.call(settings, key)) return;

        if (control.type === 'checkbox') {
            control.checked = Boolean(settings[key]);
        } else {
            control.value = settings[key];
        }
    });

    let legacyTheme = null;
    try {
        legacyTheme = localStorage.getItem('chartTheme');
    } catch (_) {
        // Use the default theme when browser storage is unavailable.
    }
    const theme = settings.theme || legacyTheme || 'dark';
    applyTheme(container, theme);
}

function collectLocalSettings(container) {
    const settings = {};

    container.querySelectorAll('[data-setting]').forEach((control) => {
        settings[control.dataset.setting] = control.type === 'checkbox'
            ? control.checked
            : control.value;
    });

    settings.theme = container.querySelector('.theme-btn.active')?.dataset.theme || 'dark';
    return settings;
}

function initTabs(container) {
    const tabButtons = container.querySelectorAll('.tab-btn');
    const panels = container.querySelectorAll('.tab-panel');

    tabButtons.forEach((button) => {
        button.addEventListener('click', () => {
            tabButtons.forEach((item) => item.classList.remove('active'));
            panels.forEach((panel) => panel.classList.remove('active'));

            button.classList.add('active');
            container.querySelector(`#panel-${button.dataset.tab}`)?.classList.add('active');
        });
    });
}

function applyTheme(container, theme) {
    const safeTheme = theme === 'light' ? 'light' : 'dark';
    container.querySelectorAll('.theme-btn').forEach((button) => {
        button.classList.toggle('active', button.dataset.theme === safeTheme);
    });
    document.body.setAttribute('data-theme', safeTheme);

    try {
        localStorage.setItem('chartTheme', safeTheme);
    } catch (_) {
        // The page still works when browser storage is unavailable.
    }
}

function initThemeSwitcher(container) {
    container.querySelectorAll('.theme-btn').forEach((button) => {
        button.addEventListener('click', () => {
            applyTheme(container, button.dataset.theme);
            const settings = collectLocalSettings(container);
            writeLocalSettings(settings);
            showToast('Theme saved in this browser');
        });
    });
}

function initEmojiRating(container) {
    const emojiButtons = container.querySelectorAll('.emoji-btn');

    emojiButtons.forEach((button) => {
        button.addEventListener('click', () => {
            emojiButtons.forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
            showToast('Thanks for your feedback!');
        });
    });
}

function initProfilePreview(container) {
    const firstName = container.querySelector('[data-setting="firstName"]');
    const lastName = container.querySelector('[data-setting="lastName"]');
    const avatar = container.querySelector('.avatar-sm > span');

    const updateInitials = () => {
        if (!avatar) return;
        const initials = `${firstName?.value?.trim()?.[0] || ''}${lastName?.value?.trim()?.[0] || ''}`;
        avatar.textContent = initials.toUpperCase() || 'U';
    };

    firstName?.addEventListener('input', updateInitials);
    lastName?.addEventListener('input', updateInitials);
    updateInitials();
}

function initSaveButton(container) {
    const saveButton = container.querySelector('#saveAllBtn');
    if (!saveButton) return;

    saveButton.addEventListener('click', () => {
        saveButton.textContent = 'Saving...';
        saveButton.disabled = true;

        const saved = writeLocalSettings(collectLocalSettings(container));
        showToast(
            saved ? 'Settings saved in this browser' : 'Unable to save browser settings',
            saved ? 'success' : 'error'
        );

        saveButton.textContent = 'Save All';
        saveButton.disabled = false;
    });
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    const messageElement = toast.querySelector('.toast-message');
    const iconElement = toast.querySelector('svg');
    if (messageElement) messageElement.textContent = message;

    if (iconElement) {
        iconElement.innerHTML = type === 'error'
            ? '<path d="M18 6L6 18M6 6l12 12"/>'
            : '<path d="M20 6L9 17l-5-5"/>';
        iconElement.style.color = type === 'error' ? '#ef4444' : '#22c55e';
    }

    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}
