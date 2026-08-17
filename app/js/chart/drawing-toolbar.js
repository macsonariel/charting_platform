(function () {
    window.DrawingToolbarUI?.destroy?.();

    let listeners = null;

    function init() {
        const toolbar = document.getElementById('drawingToolbar');
        if (!toolbar || toolbar.dataset.drawingUiInitialized === 'true') return;

        toolbar.dataset.drawingUiInitialized = 'true';
        listeners = new AbortController();
        const { signal } = listeners;
        const menus = [...toolbar.querySelectorAll('.drawing-tool-menu')];

        const closeMenu = menu => {
            const trigger = menu.querySelector('.drawing-tool-trigger');
            const panel = menu.querySelector('.drawing-menu');
            if (!trigger || !panel) return;
            panel.hidden = true;
            trigger.setAttribute('aria-expanded', 'false');
        };

        const closeAll = except => {
            menus.forEach(menu => {
                if (menu !== except) closeMenu(menu);
            });
        };

        menus.forEach(menu => {
            const trigger = menu.querySelector('.drawing-tool-trigger');
            const panel = menu.querySelector('.drawing-menu');
            if (!trigger || !panel) return;

            trigger.addEventListener('click', () => {
                const willOpen = panel.hidden;
                closeAll(menu);
                panel.hidden = !willOpen;
                trigger.setAttribute('aria-expanded', String(willOpen));
            }, { signal });

            trigger.addEventListener('keydown', event => {
                if (event.key === 'Escape') {
                    closeMenu(menu);
                    trigger.focus();
                }
            }, { signal });
        });

        toolbar.querySelectorAll('[data-drawing-tool]').forEach(item => {
            item.addEventListener('click', () => {
                const group = item.closest('.drawing-tool-menu');
                group?.querySelectorAll('[data-drawing-tool]').forEach(option => {
                    option.setAttribute('aria-checked', String(option === item));
                });

                const trigger = group?.querySelector('.drawing-tool-trigger');
                if (trigger) {
                    trigger.classList.add('has-selection');
                    trigger.dataset.selectedTool = item.dataset.drawingTool;
                    trigger.title = `${item.textContent.trim()} (UI preview)`;
                }

                closeMenu(group);
                window.dispatchEvent(new CustomEvent('drawingToolUiSelected', {
                    detail: { tool: item.dataset.drawingTool },
                }));
            }, { signal });
        });

        document.addEventListener('click', event => {
            if (!toolbar.contains(event.target)) closeAll();
        }, { signal });

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') closeAll();
        }, { signal });
    }

    function destroy() {
        listeners?.abort();
        listeners = null;
    }

    window.DrawingToolbarUI = { init, destroy };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
