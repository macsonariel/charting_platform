// Sidebar expand/collapse and mobile behavior.
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const mobileMenuToggle = document.getElementById('mobileMenuToggle');
const analysisPanel = document.getElementById('analysisPanel');
const mobileAnalysisToggle = document.getElementById('mobileAnalysisToggle');
const analysisPanelOverlay = document.getElementById('analysisPanelOverlay');
const mainContent = document.getElementById('main-content');
let sidebarOverlay = null;

if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', (event) => {
        event.stopPropagation();
        sidebar.classList.toggle('expanded');
        localStorage.setItem('sidebarExpanded', sidebar.classList.contains('expanded'));
    });
}

if (sidebar && localStorage.getItem('sidebarExpanded') === 'true') {
    sidebar.classList.add('expanded');
}

function createSidebarOverlay() {
    if (!sidebarOverlay) {
        sidebarOverlay = document.createElement('div');
        sidebarOverlay.className = 'sidebar-overlay';
        sidebarOverlay.addEventListener('click', closeSidebar);
        document.body.appendChild(sidebarOverlay);
    }
    return sidebarOverlay;
}

function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.add('open');
    mobileMenuToggle?.setAttribute('aria-expanded', 'true');
    mobileMenuToggle?.setAttribute('aria-label', 'Close navigation');
    createSidebarOverlay().classList.add('active');
}

function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove('open');
    mobileMenuToggle?.setAttribute('aria-expanded', 'false');
    mobileMenuToggle?.setAttribute('aria-label', 'Open navigation');
    if (sidebarOverlay) sidebarOverlay.classList.remove('active');
}

function toggleSidebar() {
    if (sidebar?.classList.contains('open')) {
        closeSidebar();
    } else {
        openSidebar();
    }
}

if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleSidebar();
    });
}

document.querySelectorAll('.menu-link').forEach((link) => {
    link.addEventListener('click', () => {
        if (window.innerWidth <= 1024) closeSidebar();
    });
});

document.addEventListener('click', (event) => {
    if (window.innerWidth > 1024 || !sidebar?.classList.contains('open')) return;

    const clickedInsideSidebar = sidebar.contains(event.target);
    const clickedToggle = mobileMenuToggle?.contains(event.target);
    if (!clickedInsideSidebar && !clickedToggle) closeSidebar();
});

window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) closeSidebar();
    if (window.innerWidth > 1100) closeAnalysisPanel();
});

function isHomeRoute() {
    return mainContent?.dataset.route === 'home';
}

function openAnalysisPanel() {
    if (!analysisPanel || window.innerWidth > 1100 || !isHomeRoute()) return;
    closeSidebar();
    analysisPanel.inert = false;
    analysisPanel.removeAttribute('aria-hidden');
    analysisPanel.classList.add('is-mobile-open');
    analysisPanelOverlay?.classList.add('active');
    mobileAnalysisToggle?.setAttribute('aria-expanded', 'true');
    mobileAnalysisToggle?.setAttribute('aria-label', 'Close market analysis');
}

function closeAnalysisPanel() {
    analysisPanel?.classList.remove('is-mobile-open');
    if (analysisPanel) {
        const isDrawer = window.innerWidth <= 1100;
        analysisPanel.inert = isDrawer;
        if (isDrawer) {
            analysisPanel.setAttribute('aria-hidden', 'true');
        } else {
            analysisPanel.removeAttribute('aria-hidden');
        }
    }
    analysisPanelOverlay?.classList.remove('active');
    mobileAnalysisToggle?.setAttribute('aria-expanded', 'false');
    mobileAnalysisToggle?.setAttribute('aria-label', 'Open market analysis');
}

function syncAnalysisToggle() {
    const shouldShow = window.innerWidth <= 1100 && isHomeRoute();
    if (mobileAnalysisToggle) mobileAnalysisToggle.hidden = !shouldShow;
    if (!shouldShow || !analysisPanel?.classList.contains('is-mobile-open')) closeAnalysisPanel();
}

mobileAnalysisToggle?.addEventListener('click', (event) => {
    event.stopPropagation();
    if (analysisPanel?.classList.contains('is-mobile-open')) {
        closeAnalysisPanel();
    } else {
        openAnalysisPanel();
    }
});

analysisPanelOverlay?.addEventListener('click', closeAnalysisPanel);

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        closeSidebar();
        closeAnalysisPanel();
    }
});

if (mainContent) {
    new MutationObserver(syncAnalysisToggle).observe(mainContent, {
        attributes: true,
        attributeFilter: ['data-route']
    });
}

window.addEventListener('resize', syncAnalysisToggle);
syncAnalysisToggle();

function setActiveMenuItem(route) {
    document.querySelectorAll('.menu-link').forEach((link) => {
        link.classList.toggle('active', link.dataset.route === route);
    });
}

window.sidebarUtils = {
    open: openSidebar,
    close: closeSidebar,
    toggle: toggleSidebar,
    setActiveMenuItem
};

window.analysisPanelUtils = {
    open: openAnalysisPanel,
    close: closeAnalysisPanel,
    sync: syncAnalysisToggle
};
