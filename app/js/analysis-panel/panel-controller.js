/**
 * Owns the Core view-model request and publishes one snapshot to both the
 * right analysis panel and the bottom Quick Overview strip.
 */
const PanelController = {
    symbol: 'BTCUSDT',
    timeframe: '1h',
    periods: 400,
    _refreshInterval: null,
    _abortController: null,
    _requestId: 0,

    init() {
        this._bindChartEvents();
        window.AnalysisPanelV2?.setLoading();

        window.addEventListener('viewLoaded', event => {
            if (event.detail?.view === 'home') {
                this._syncChartParams();
                this.refresh();
            }
        });

        if (document.getElementById('quickStrip')) {
            this._syncChartParams();
            this.refresh();
        }

        // Keep the snapshot current without clearing either panel. This is a
        // background sync, not a chart-context change.
        this._refreshInterval = setInterval(() => {
            if (document.getElementById('main-content')?.dataset.route === 'home') {
                this.refresh({ showLoading: false, reportErrors: false });
            }
        }, 60000);
    },

    _syncChartParams() {
        const symbolSelect = document.getElementById('symbolSelect');
        const timeframeSelect = document.getElementById('timeframeSelect');
        this.symbol = symbolSelect?.value || window.currentSymbol || this.symbol;
        this.timeframe = timeframeSelect?.value || window.currentTimeframe || this.timeframe;
    },

    _bindChartEvents() {
        window.addEventListener('chartContextChanged', event => {
            if (!event.detail) return;
            this.setParams(
                event.detail.symbol || this.symbol,
                event.detail.timeframe || this.timeframe,
                this.periods,
            );
        });
    },

    setParams(symbol, timeframe, periods = 400) {
        const nextSymbol = (symbol || this.symbol).toUpperCase();
        const nextTimeframe = timeframe || this.timeframe;
        const nextPeriods = Math.max(50, Math.min(2000, Number(periods) || this.periods));
        const contextChanged =
            nextSymbol !== this.symbol.toUpperCase() ||
            nextTimeframe !== this.timeframe ||
            nextPeriods !== this.periods;

        this.symbol = nextSymbol;
        this.timeframe = nextTimeframe;
        this.periods = nextPeriods;
        if (contextChanged) this.refresh();
    },

    async refresh({ showLoading = true, reportErrors = showLoading } = {}) {
        // A timer must never interrupt a user-initiated symbol/timeframe load.
        if (!showLoading && this._abortController) return;

        const requestId = ++this._requestId;
        const requestContext = {
            symbol: this.symbol.toUpperCase(),
            timeframe: this.timeframe,
            periods: this.periods,
        };
        this._abortController?.abort();
        const abortController = new AbortController();
        this._abortController = abortController;
        if (showLoading) {
            window.latestCoreViewModel = null;
            window.AnalysisPanelV2?.setLoading(
                `Loading ${requestContext.symbol} ${requestContext.timeframe}…`,
            );
        }

        try {
            const params = new URLSearchParams({
                symbol: requestContext.symbol,
                timeframe: requestContext.timeframe,
                periods: String(requestContext.periods),
            });
            const response = await fetch(`/api/core/summary?${params}`, {
                signal: abortController.signal,
                cache: 'no-store',
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const viewModel = await response.json();
            if (requestId !== this._requestId) return;
            if (
                viewModel.engine !== 'core' ||
                viewModel.source !== 'market_snapshot' ||
                viewModel.symbol?.toUpperCase() !== requestContext.symbol ||
                viewModel.timeframe !== requestContext.timeframe
            ) {
                throw new Error('Core response context does not match the chart');
            }
            window.latestCoreViewModel = viewModel;
            window.AnalysisPanelV2?.update(viewModel);
            window.dispatchEvent(new CustomEvent('coreSnapshotUpdated', { detail: viewModel }));
        } catch (error) {
            if (error.name === 'AbortError' || requestId !== this._requestId) return;
            console.error('Core panel refresh failed:', error);
            if (reportErrors) {
                window.AnalysisPanelV2?.setError(
                    `Core analysis unavailable (${error.message}). Retrying automatically.`,
                );
            }
        } finally {
            if (this._abortController === abortController) {
                this._abortController = null;
            }
        }
    },

    destroy() {
        this._abortController?.abort();
        if (this._refreshInterval) clearInterval(this._refreshInterval);
    },
};

document.addEventListener('DOMContentLoaded', () => PanelController.init());
window.PanelController = PanelController;
