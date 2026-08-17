import re
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from backend.main import _allowed_origins, app


class ApplicationSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=transport, base_url='http://testserver')

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_health_endpoint(self):
        response = await self.client.get('/api/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')

    def test_production_cors_is_explicit(self):
        with patch.dict('os.environ', {'APP_ENV': 'production'}, clear=True):
            self.assertEqual(_allowed_origins(), [])

        with patch.dict(
            'os.environ',
            {
                'APP_ENV': 'production',
                'ALLOWED_ORIGINS': 'https://app.example.com/, https://admin.example.com',
            },
            clear=True,
        ):
            self.assertEqual(
                _allowed_origins(),
                ['https://app.example.com', 'https://admin.example.com'],
            )

    def test_ecs_express_configuration_checks_health_and_core(self):
        dockerfile = Path('Dockerfile').read_text(encoding='utf-8')
        deployment = Path('.github/workflows/deploy-ecs-express.yml').read_text(encoding='utf-8')
        verifier = Path('scripts/verify_deployment.py').read_text(encoding='utf-8')

        self.assertFalse(Path('apprunner.yaml').exists())
        self.assertIn('backend.main:app', dockerfile)
        self.assertIn('EXPOSE 8080', dockerfile)
        self.assertIn('USER app', dockerfile)
        self.assertIn("vars.AWS_DEPLOYMENT_ENABLED == 'true'", deployment)
        self.assertIn('id-token: write', deployment)
        self.assertNotIn('AWS_ACCESS_KEY_ID', deployment)
        self.assertNotIn('AWS_SECRET_ACCESS_KEY', deployment)
        self.assertIn('amazon-ecs-deploy-express-service@v1', deployment)
        self.assertIn('health-check-path: /api/health', deployment)
        self.assertIn('ECS Express endpoint or custom-domain URL', verifier)
        self.assertIn('/api/health', verifier)
        self.assertIn('/api/core/summary?', verifier)

    async def test_root_redirects_to_dashboard(self):
        response = await self.client.get('/', follow_redirects=False)

        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/html/dashboard/index.html')

    async def test_dashboard_has_only_home_and_settings_routes(self):
        response = await self.client.get('/html/dashboard/index.html')

        self.assertEqual(response.status_code, 200)
        routes = re.findall(r'data-route="([^"]+)"', response.text)
        self.assertEqual(routes, ['home', 'settings'])

    async def test_settings_uses_local_browser_persistence(self):
        html_response = await self.client.get('/html/fragments/settings.html')
        script_response = await self.client.get('/js/fragments/settings.js')

        self.assertEqual(html_response.status_code, 200)
        self.assertEqual(script_response.status_code, 200)
        self.assertIn('tradingBuddy.localSettings', script_response.text)
        self.assertNotRegex(
            f'{html_response.text}\n{script_response.text}',
            r'(?i)firebase|firestore|/backend/auth',
        )

    async def test_engine_browser_assets_are_served_from_app(self):
        asset_paths = (
            '/js/engines/core/core-engine.js',
            '/css/engines/core/core-engine.css',
            '/js/indicators/indicator-engine.js',
            '/js/indicators/indicator-renderer.js',
        )

        for path in asset_paths:
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 200)

    async def test_analysis_panels_start_without_sample_market_data(self):
        dashboard = (await self.client.get('/html/dashboard/index.html')).text
        chart = (await self.client.get('/html/fragments/market-chart.html')).text
        controller = (await self.client.get('/js/analysis-panel/panel-controller.js')).text
        panel_script = (await self.client.get('/js/analysis-panel/analysis-panel-v2.js')).text
        chart_script = (await self.client.get('/js/fragments/market-chart.js')).text

        self.assertIn('Core Engine', dashboard)
        self.assertIn('Loading Core analysis', dashboard)
        self.assertNotIn('91,442.88', dashboard)
        self.assertNotIn('89,311', dashboard)
        self.assertNotIn('BEARISH ↓', chart)
        self.assertNotIn('core-panel.js', dashboard)
        self.assertNotIn('core-panel.css', dashboard)
        self.assertNotIn('mtf-confluence.js', dashboard)
        self.assertIn('apSessionContext', dashboard)
        self.assertIn('data-session-source="unconnected"', dashboard)
        self.assertNotRegex(panel_script, r'_sessions|_killzones|Structure-based analysis')
        self.assertIn('/api/core/summary?', controller)
        self.assertIn("viewModel.engine !== 'core'", controller)
        self.assertIn("data.engine !== 'core'", panel_script)
        self.assertIn('_updateQuickStrip(data)', panel_script)
        self.assertIn("new CustomEvent('chartContextChanged'", chart_script)
        self.assertIn('this.refresh({ showLoading: false, reportErrors: false })', controller)
        self.assertNotIn(
            'PanelController?.setParams(currentSymbol, currentTimeframe, newCandleCount)',
            chart_script,
        )

    async def test_backend_source_is_not_public(self):
        source_paths = (
            '/backend/chart/data/chart_data_fetcher.py',
            '/backend/chart/engines/core/detectors/swing_detector.py',
        )

        for path in source_paths:
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 404)

    async def test_removed_landing_and_account_pages_stay_removed(self):
        removed_paths = (
            '/html/landing_page/index.html',
            '/html/landing_page/login.html',
            '/html/landing_page/signup.html',
            '/css/landing_page/styles.css',
            '/js/landing_page/script.js',
            '/img/landing_page/Landing_Page.png',
            '/backend/auth/config.js',
        )

        for path in removed_paths:
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 404)

    async def test_price_action_engine_stays_removed(self):
        fragment = (await self.client.get('/html/fragments/market-chart.html')).text
        chart_script = (await self.client.get('/js/fragments/market-chart.js')).text
        removed_paths = (
            '/api/price-action/analyze',
            '/js/engines/price-action/price-action-api.js',
            '/js/engines/price-action/price-action-engine.js',
            '/js/chart/trendline-patterns.js',
            '/css/engines/price-action/price-action.css',
            '/html/dashboard/dashboard.html',
        )

        self.assertNotRegex(
            f'{fragment}\n{chart_script}',
            r'(?i)price[-_ ]?action|PriceActionEngine|SingleCandlePatterns|TwoCandlePatterns|ThreeCandlePatterns|ChartPatterns',
        )
        for path in removed_paths:
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 404)

    async def test_removed_chart_tools_stay_removed(self):
        fragment = await self.client.get('/html/fragments/market-chart.html')
        removed_assets = (
            '/js/analysis-panel/risk-calculator.js',
            '/css/analysis-panel/risk-calculator.css',
            '/js/analysis-panel/trade-checklist.js',
            '/css/analysis-panel/trade-checklist.css',
        )

        self.assertEqual(fragment.status_code, 200)
        self.assertNotRegex(
            fragment.text,
            r'riskCalcTrigger|checklistTrigger|zoom-controls|zoomInBtn|zoomOutBtn|resetZoomBtn|'
            r'control-group drawing-tools|notification-badge|id="moreActions"',
        )
        self.assertIn('/css/dashboard/ui-polish.css?v=1.3', fragment.text)
        self.assertIn('aria-label="Open profile menu"', fragment.text)
        for path in removed_assets:
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 404)

    async def test_drawing_toolbar_ui_is_grouped_and_data_neutral(self):
        fragment = (await self.client.get('/html/fragments/market-chart.html')).text
        toolbar_script = await self.client.get('/js/chart/drawing-toolbar.js')
        toolbar_styles = await self.client.get('/css/chart/drawing-toolbar.css')

        self.assertEqual(toolbar_script.status_code, 200)
        self.assertEqual(toolbar_styles.status_code, 200)
        self.assertIn('id="drawingShapesMenu"', fragment)
        self.assertIn('data-drawing-tool="rectangle"', fragment)
        self.assertIn('id="drawingTextMenu"', fragment)
        self.assertIn('data-drawing-tool="callout"', fragment)
        self.assertIn('id="drawingsManagerMenu"', fragment)
        self.assertIn('id="drawingShowAll"', fragment)
        self.assertIn('id="drawingDeleteAll"', fragment)
        self.assertIn('id="drawingManagerItemTemplate"', fragment)
        self.assertIn('data-ui-only="true"', fragment)
        self.assertIn("new CustomEvent('drawingToolUiSelected'", toolbar_script.text)
        self.assertNotIn('DrawingManager', toolbar_script.text)

    async def test_legacy_structure_authorities_stay_removed(self):
        fragment = (await self.client.get('/html/fragments/market-chart.html')).text
        chart_script = (await self.client.get('/js/fragments/market-chart.js')).text

        self.assertNotRegex(fragment, r'phaseConfig|market-analysis\.js|orchestratorPlayBtn')
        self.assertNotRegex(
            chart_script,
            r'universalStructureData|StructureOrchestrator|phaseAnalyzerConfig|runUniversalStructurePipeline',
        )
        self.assertEqual(
            (await self.client.get('/js/dashboard/market-analysis.js')).status_code,
            404,
        )

    async def test_responsive_dashboard_controls_are_available(self):
        dashboard = await self.client.get('/html/dashboard/index.html')
        sidebar_script = await self.client.get('/js/dashboard/user_sidebar_script.js')
        chart_styles = await self.client.get('/css/dashboard/fragments/market-chart.css')
        polish_styles = await self.client.get('/css/dashboard/ui-polish.css')
        settings_styles = await self.client.get('/css/dashboard/fragments/settings.css')

        self.assertIn('id="mobileMenuToggle"', dashboard.text)
        self.assertIn('id="mobileAnalysisToggle"', dashboard.text)
        self.assertIn('aria-controls="analysisPanel"', dashboard.text)
        self.assertIn('is-mobile-open', sidebar_script.text)
        self.assertIn('analysisPanel.inert', sidebar_script.text)
        self.assertIn('@media (max-width: 600px)', chart_styles.text)
        self.assertIn('overflow-x: auto', chart_styles.text)
        self.assertEqual(polish_styles.status_code, 200)
        self.assertIn('@media (prefers-reduced-motion: reduce)', polish_styles.text)
        self.assertIn('@media (max-width: 480px)', settings_styles.text)


if __name__ == '__main__':
    unittest.main()
