(function () {
    function init() {
        const toggle = document.getElementById('profileToggleChart');
        const menu = document.getElementById('profileDropdownChart');
        const container = toggle?.closest('.profile-dropdown');
        const settingsButton = document.getElementById('openSettingsFromChart');

        if (!toggle || !menu || !container || container.dataset.profileMenuInitialized === 'true') {
            return;
        }

        container.dataset.profileMenuInitialized = 'true';

        const closeMenu = () => {
            menu.classList.remove('show');
            toggle.setAttribute('aria-expanded', 'false');
        };

        toggle.addEventListener('click', (event) => {
            event.stopPropagation();
            const isOpen = menu.classList.toggle('show');
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        document.addEventListener('click', (event) => {
            if (!container.contains(event.target)) {
                closeMenu();
            }
        });

        toggle.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                closeMenu();
                toggle.focus();
            }
        });

        settingsButton?.addEventListener('click', () => {
            closeMenu();
            window.loadView?.('settings');
        });
    }

    window.ProfileMenu = { init };
})();
