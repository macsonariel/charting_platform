// Routing Configuration
const routes = {
    'home': {
        title: 'Market Chart',
        fragment: '/html/fragments/market-chart.html',
        onLoad: () => {
            // Chart will be initialized by the fragment's script
            console.log('Market chart fragment loaded');
        }
    },
    'settings': {
        title: 'Settings',
        fragment: '/html/fragments/settings.html',
        onLoad: () => {
            console.log('📝 Settings fragment onLoad callback fired');
            // Re-initialize settings page - wait for elements to be ready
            const waitAndInit = (attempts = 0) => {
                const container = document.querySelector('.settings-container');
                const tabBtns = container ? container.querySelectorAll('.tab-btn') : [];
                const hasSettings = typeof SettingsPage !== 'undefined';

                console.log(`🔍 waitAndInit attempt ${attempts}: container=${!!container}, tabs=${tabBtns.length}, SettingsPage=${hasSettings}`);

                if (tabBtns.length > 0 && hasSettings) {
                    console.log('✅ Calling SettingsPage.init()');
                    SettingsPage.init();
                } else if (attempts < 20) {
                    setTimeout(() => waitAndInit(attempts + 1), 100);
                } else {
                    console.warn('⚠️ Settings page initialization timed out');
                }
            };
            setTimeout(waitAndInit, 100);
        }
    }
};

// Load View Function
async function loadView(viewName) {
    const mainContent = document.getElementById('main-content');

    if (!mainContent) {
        console.error('Main content container not found');
        return;
    }

    const currentRoute = mainContent.dataset.route;
    if (currentRoute === viewName) return;

    // The chart module owns long-lived DOM references. Recreate the page when
    // returning from Settings so every renderer binds to the new chart DOM.
    if (viewName === 'home' && currentRoute && currentRoute !== 'home') {
        localStorage.setItem('lastRoute', 'home');
        window.location.reload();
        return;
    }

    const route = routes[viewName];

    if (!route) {
        console.error(`Route "${viewName}" not found`);
        mainContent.innerHTML = `
            <div class="view-container">
                <h1 class="view-title">404 - Page Not Found</h1>
                <p class="view-subtitle">The requested page does not exist.</p>
                <button class="view-button" onclick="loadView('home')">Go Home</button>
            </div>
        `;
        return;
    }

    // Fade out
    mainContent.style.opacity = '0';
    mainContent.style.transform = 'translateY(10px)';

    setTimeout(async () => {
        // Load fragment or inline content
        if (route.fragment) {
            try {
                // Add cache-busting and retry logic for connection issues
                const fetchWithRetry = async (url, retries = 3) => {
                    for (let i = 0; i < retries; i++) {
                        try {
                            const cacheBuster = `?_t=${Date.now()}`;
                            const response = await fetch(url + cacheBuster, {
                                cache: 'no-store',
                                headers: { 'Cache-Control': 'no-cache' }
                            });
                            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                            return response;
                        } catch (err) {
                            console.warn(`Fetch attempt ${i + 1} failed:`, err.message);
                            if (i === retries - 1) throw err;
                            await new Promise(r => setTimeout(r, 500)); // Wait before retry
                        }
                    }
                };

                const response = await fetchWithRetry(route.fragment);
                const html = await response.text();

                // Extract body content from fragment (remove DOCTYPE, html, head, body tags)
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const links = Array.from(doc.querySelectorAll('link[rel="stylesheet"]'));
                const scripts = Array.from(doc.querySelectorAll('script')).map(script => ({
                    src: script.getAttribute('src'),
                    type: script.getAttribute('type'),
                    text: script.textContent
                }));

                // Scripts inserted through innerHTML are inert. Remove fragment
                // assets before inserting markup, then load them explicitly below.
                doc.body.querySelectorAll('script, link[rel="stylesheet"]').forEach(element => element.remove());

                mainContent.innerHTML = doc.body.innerHTML;

                // Load any CSS stylesheets from the fragment's <head>
                // IMPORTANT: Resolve relative hrefs against the fragment URL,
                // not against the dashboard page, so paths like "enhanced-chart.css"
                // work regardless of where the dashboard HTML lives.
                const fragmentUrl = new URL(route.fragment, window.location.href);
                links.forEach(link => {
                    const hrefAttr = link.getAttribute('href');
                    if (!hrefAttr) return;

                    // Compute absolute URL relative to the fragment's location
                    const absoluteHref = new URL(hrefAttr, fragmentUrl).href;

                    // Avoid duplicating the same stylesheet
                    const existingLink = document.querySelector(`link[href="${absoluteHref}"]`);
                    if (!existingLink) {
                        const newLink = document.createElement('link');
                        newLink.rel = 'stylesheet';
                        newLink.href = absoluteHref;
                        document.head.appendChild(newLink);
                    }
                });

                // Execute any scripts in the fragment
                for (const script of scripts) {
                    const newScript = document.createElement('script');

                    // Preserve the type attribute (important for ES6 modules)
                    if (script.type) {
                        newScript.type = script.type;
                    }

                    if (script.src) {
                        // Resolve relative script src against the fragment URL
                        const absoluteSrc = new URL(script.src, fragmentUrl).href;

                        // Avoid re-injecting the same script (prevents duplicate let/const errors)
                        const existingScript = Array.from(document.scripts).find(item => item.src === absoluteSrc);
                        if (existingScript) {
                            continue;
                        }

                        newScript.src = absoluteSrc;
                        newScript.async = false;
                        await new Promise((resolve, reject) => {
                            newScript.addEventListener('load', resolve, { once: true });
                            newScript.addEventListener('error', () => reject(new Error(`Failed to load ${absoluteSrc}`)), { once: true });
                            document.body.appendChild(newScript);
                        });
                    } else {
                        newScript.textContent = script.text;
                        document.body.appendChild(newScript);
                    }
                }

                // Call onLoad callback if exists
                if (route.onLoad) {
                    route.onLoad();
                }
            } catch (error) {
                console.error('Error loading fragment:', error);
                mainContent.innerHTML = `
                    <div class="view-container">
                        <h1 class="view-title">Error Loading Page</h1>
                        <p class="view-subtitle">${error.message}</p>
                        <button class="view-button" onclick="loadView('home')">Go Home</button>
                    </div>
                `;
            }
        } else {
            // Use inline content
            mainContent.innerHTML = route.content;
        }

        document.title = `${route.title} - Trading Buddy`;

        // Initialize dashboard for home view (legacy support)
        // Dashboard scripts removed - using market-chart.js fragment instead

        // Set data-route attribute for CSS styling
        mainContent.setAttribute('data-route', viewName);

        // Update active menu items
        updateActiveMenu(viewName);

        // Show/hide top-navbar based on route
        const topNavbar = document.querySelector('.top-navbar');
        if (topNavbar) {
            if (viewName === 'home') {
                topNavbar.style.display = 'none';
            } else {
                topNavbar.style.display = 'block';
            }
        }

        // Remove top margin on main-container when route is 'home'
        const mainContainer = document.querySelector('.main-container');
        if (mainContainer) {
            if (viewName === 'home') {
                mainContainer.style.marginTop = '0';
            } else {
                mainContainer.style.marginTop = '';
            }
        }

        // Show/hide nav-right based on route
        const navRight = document.querySelector('.nav-right');
        if (navRight) {
            if (viewName === 'home') {
                navRight.style.display = 'none';
            } else {
                navRight.style.display = 'flex';
            }
        }

        // Show/hide narrator-panel based on route (only show on home)
        const narratorPanel = document.querySelector('.narrator-panel');
        if (narratorPanel) {
            if (viewName === 'home') {
                narratorPanel.style.display = 'block';
            } else {
                narratorPanel.style.display = 'none';
            }
        }

        // Show/hide analysis-panel based on route (only show on home)
        const analysisPanel = document.querySelector('.ap-panel, .analysis-panel');
        if (analysisPanel) {
            if (viewName === 'home') {
                // Use grid for ap-panel (matches CSS), flex for legacy analysis-panel
                analysisPanel.style.display = analysisPanel.classList.contains('ap-panel') ? 'grid' : 'flex';
            } else {
                analysisPanel.style.display = 'none';
            }
        }

        window.dispatchEvent(new CustomEvent('viewLoaded', {
            detail: { view: viewName }
        }));

        // Save to localStorage
        localStorage.setItem('lastRoute', viewName);

        // Fade in
        setTimeout(() => {
            mainContent.style.opacity = '1';
            mainContent.style.transform = 'translateY(0)';
        }, 50);
    }, 150);
}


// Update Active Menu Item
function updateActiveMenu(routeName) {
    // Remove active class from all menu items
    document.querySelectorAll('.menu-link').forEach(link => {
        link.classList.remove('active');
    });

    // Add active class to current route
    const activeLink = document.querySelector(`[data-route="${routeName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

// Initialize App
document.addEventListener('DOMContentLoaded', function () {
    // Initialize Market Narrator panel
    if (typeof MarketNarrator !== 'undefined' && MarketNarrator.init) {
        MarketNarrator.init();
        console.log('📊 Market Narrator initialized from dashboard');
    }

    // Load last visited route or default to home
    const storedRoute = localStorage.getItem('lastRoute');
    const lastRoute = storedRoute && routes[storedRoute] ? storedRoute : 'home';

    // Set initial top-navbar visibility
    const topNavbar = document.querySelector('.top-navbar');
    if (topNavbar) {
        if (lastRoute === 'home') {
            topNavbar.style.display = 'none';
        } else {
            topNavbar.style.display = 'block';
        }
    }

    // Set initial main-container margin
    const mainContainer = document.querySelector('.main-container');
    if (mainContainer) {
        if (lastRoute === 'home') {
            mainContainer.style.marginTop = '0';
        } else {
            mainContainer.style.marginTop = '';
        }
    }

    // Set initial nav-right visibility
    const navRight = document.querySelector('.nav-right');
    if (navRight) {
        if (lastRoute === 'home') {
            navRight.style.display = 'none';
        } else {
            navRight.style.display = 'flex';
        }
    }

    // Set initial narrator-panel visibility (only show on home)
    const narratorPanel = document.querySelector('.narrator-panel');
    if (narratorPanel) {
        if (lastRoute === 'home') {
            narratorPanel.style.display = 'block';
        } else {
            narratorPanel.style.display = 'none';
        }
    }

    // Set initial analysis-panel visibility (only show on home)
    const analysisPanel = document.querySelector('.ap-panel, .analysis-panel');
    if (analysisPanel) {
        if (lastRoute === 'home') {
            // Use grid for ap-panel (matches CSS), flex for legacy analysis-panel
            analysisPanel.style.display = analysisPanel.classList.contains('ap-panel') ? 'grid' : 'flex';
        } else {
            analysisPanel.style.display = 'none';
        }
    }

    loadView(lastRoute);

    // Set up route click handlers
    document.querySelectorAll('[data-route]').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const route = this.getAttribute('data-route');

            loadView(route);
        });
    });
});


// Real-Time Price Card Functions
let priceCardInterval = null;
let priceCardSymbol = "XAUUSD";
let priceCardTimeframe = "15";

function initPriceCard() {
    // Check if price card element exists
    const priceCard = document.getElementById('priceCard');
    if (!priceCard) {
        console.error('Price card element not found in DOM');
        addHomeLogMessage('Price card element not found', 'error');
        return;
    }

    console.log('Price card found, initializing...');
    addHomeLogMessage('Initializing price card...');

    // Initialize price card with default values
    updatePriceCard(priceCardSymbol, priceCardTimeframe);

    // Start periodic updates
    startPriceCardUpdates();
}

function updatePriceCard(symbol, timeframe) {
    // Normalize symbol (remove exchange prefix if present)
    const cleanSymbol = symbol.replace(/^[A-Z]+:/, '').toUpperCase();
    priceCardSymbol = cleanSymbol;
    priceCardTimeframe = timeframe.toString();

    console.log('Updating price card:', cleanSymbol, timeframe);
    addHomeLogMessage(`Price card: ${cleanSymbol} ${timeframe}`);

    // Update display
    const symbolEl = document.getElementById('priceSymbol');
    const timeframeEl = document.getElementById('priceTimeframe');

    if (symbolEl) {
        symbolEl.textContent = cleanSymbol;
    }

    if (timeframeEl) {
        // Convert interval to readable format
        const timeframeMap = {
            "1": "1m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1h", "240": "4h", "D": "1d", "1d": "1d"
        };
        timeframeEl.textContent = timeframeMap[timeframe] || timeframe;
    }

    // Restart updates with new interval
    startPriceCardUpdates();

    // Fetch current candle data immediately
    fetchCurrentCandle(cleanSymbol, timeframe);
}

async function fetchCurrentCandle(symbol, timeframe) {
    try {
        // Convert timeframe to API format
        const timeframeMap = {
            "1": "1m", "5": "5m", "15": "15m", "30": "30m",
            "60": "1h", "240": "4h", "D": "1d", "1d": "1d"
        };
        const apiTimeframe = timeframeMap[timeframe.toString()] || "1h";

        // Clean symbol (remove any exchange prefixes)
        const cleanSymbol = symbol.replace(/^[A-Z]+:/, '').toUpperCase();

        const url = `http://localhost:8000/api/chart/current-candle?symbol=${encodeURIComponent(cleanSymbol)}&timeframe=${encodeURIComponent(apiTimeframe)}`;

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        updatePriceCardDisplay(data);

        // Update status to live
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        if (statusIndicator) {
            statusIndicator.classList.remove('offline');
        }
        if (statusText) {
            statusText.textContent = 'Live';
        }

    } catch (error) {
        console.error('Error fetching current candle:', error);
        addHomeLogMessage(`Price update error: ${error.message}`, 'error');

        // Update status to offline
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        if (statusIndicator) {
            statusIndicator.classList.add('offline');
        }
        if (statusText) {
            statusText.textContent = 'Offline';
        }
    }
}

function updatePriceCardDisplay(data) {
    // Update status
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    if (statusIndicator) {
        statusIndicator.classList.remove('offline');
    }
    if (statusText) {
        statusText.textContent = 'Live';
    }

    // Update price
    const priceClose = document.getElementById('priceClose');
    if (priceClose) {
        priceClose.textContent = data.close.toFixed(5);
    }

    // Update change
    const changeValue = document.getElementById('changeValue');
    const changePercent = document.getElementById('changePercent');

    if (changeValue) {
        changeValue.textContent = data.change >= 0 ? `+${data.change.toFixed(5)}` : data.change.toFixed(5);
        changeValue.className = `change-value ${data.isBullish ? 'positive' : 'negative'}`;
    }

    if (changePercent) {
        changePercent.textContent = data.changePercent >= 0 ? `+${data.changePercent.toFixed(2)}%` : `${data.changePercent.toFixed(2)}%`;
        changePercent.className = `change-percent ${data.isBullish ? 'positive' : 'negative'}`;
    }

    // Update OHLC
    const priceOpen = document.getElementById('priceOpen');
    const priceHigh = document.getElementById('priceHigh');
    const priceLow = document.getElementById('priceLow');
    const priceVolume = document.getElementById('priceVolume');

    if (priceOpen) priceOpen.textContent = data.open.toFixed(5);
    if (priceHigh) priceHigh.textContent = data.high.toFixed(5);
    if (priceLow) priceLow.textContent = data.low.toFixed(5);
    if (priceVolume) priceVolume.textContent = data.volume.toLocaleString();
}

function startPriceCardUpdates() {
    // Clear existing interval
    if (priceCardInterval) {
        clearInterval(priceCardInterval);
    }

    // Determine update interval based on timeframe
    // Use shorter intervals for more real-time updates
    const updateIntervals = {
        "1": 5000,    // 5 seconds for 1m
        "5": 10000,   // 10 seconds for 5m
        "15": 15000,  // 15 seconds for 15m
        "30": 30000,  // 30 seconds for 30m
        "60": 30000,  // 30 seconds for 1h
        "240": 60000, // 1 minute for 4h
        "D": 300000   // 5 minutes for 1d
    };

    const updateMs = updateIntervals[priceCardTimeframe] || 30000;

    // Update immediately
    fetchCurrentCandle(priceCardSymbol, priceCardTimeframe);

    // Then update periodically
    priceCardInterval = setInterval(() => {
        fetchCurrentCandle(priceCardSymbol, priceCardTimeframe);
    }, updateMs);
}

function stopPriceCardUpdates() {
    if (priceCardInterval) {
        clearInterval(priceCardInterval);
        priceCardInterval = null;
    }
}

/**
 * Add log message to home view (if log element exists)
 * @param {string} message - Message to log
 * @param {string} type - Message type: 'info', 'error', 'success', 'warning'
 */
function addHomeLogMessage(message, type = 'info') {
    // Try to find log element (may not exist in current view)
    const logElement = document.getElementById('homeLog');
    if (logElement) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logElement.appendChild(logEntry);
        logElement.scrollTop = logElement.scrollHeight;
    }
    // Always log to console as well
    const consoleMethod = type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'log';
    console[consoleMethod](`[Home] ${message}`);
}

// Make loadView available globally
window.loadView = loadView;
window.addHomeLogMessage = addHomeLogMessage;
window.updatePriceCard = updatePriceCard;
