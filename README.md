# Trading Buddy

Trading Buddy is a development-stage trading analysis application. A FastAPI process serves both the JSON API and the browser assets for the market chart and profile/settings experience.

This repository is not a static website and is not production-ready. GitHub Pages cannot run it because the UI depends on same-project API routes and server-side Python analysis.

## What currently works

- FastAPI application entry point: `backend.main:app`
- Dashboard served at `/html/dashboard/index.html` (the root URL redirects there)
- Two browser routes: Home (market chart) and Settings/Profile
- Swing-first Core Engine analysis shared by the chart, right panel, bottom overview, and narrative projections
- No-lookahead Core replay reports for checking historical regime and direction behaviour
- Technical indicators remain available as optional chart overlays
- Crypto market data from Binance by default, with Yahoo Finance as a selectable alternative

Several screens still contain placeholder content, and some integrations require external services. Treat analysis output as experimental software output, not financial advice.

## Repository layout

```text
app/                         Browser HTML, CSS, JavaScript, and images
  js/engines/                Browser-side chart engine renderers
  css/engines/               Browser-side engine styles
backend/
  main.py                    FastAPI application and static-file mounts
  api/                       HTTP route modules
  chart/                     Market-data and analysis engines
docs/                        Current architecture, references, and archived notes
tests/                       Automated tests and evaluation material
requirements-dev.txt         Test-only dependencies
requirements.txt             Runtime dependencies
```

The root README and `backend/main.py` are the canonical setup references. Some files under `docs/` describe older iterations and may not match the current application.

## Local setup

Python 3.11 or 3.12 is recommended. Run all commands from the repository root.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

If the Python launcher is unavailable, use the path to an installed Python executable in place of `py -3.12`.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- Dashboard: <http://127.0.0.1:8000/>
- Health check: <http://127.0.0.1:8000/api/health>
- Interactive API documentation: <http://127.0.0.1:8000/docs>

Do not open the HTML files directly. The dashboard loads fragments and API routes over HTTP and must be served by FastAPI.

## Configuration

No credentials are required to start the base application. Network-backed data and account features have additional requirements:

| Setting | Required for | Notes |
| --- | --- | --- |
| `DATA_SOURCE` | Selecting a default market-data provider | Optional; `binance` is the default. The implemented alternatives are `yahoo` and `massive`. |
| `MASSIVE_API_KEY` | Massive/Polygon forex data | Forex symbols are automatically routed to this provider. `polygon-api-client` is also required but is not included in `requirements.txt`. |

The market-data code will read a `.env` file only when `python-dotenv` is installed separately. Shell or hosting-platform environment variables are the supported baseline.

Profile and preference values are currently saved only in the browser's local storage. There is no account system, server-side user store, or cloud identity provider in this version.

## Deployment model

Deploy the repository as one Python/ASGI web service, from the repository root. The service must serve both the API and the checked-in browser assets from the same release.

A generic provider configuration is:

```text
Build:  python -m pip install -r requirements.txt
Start:  python -m uvicorn backend.main:app --host 0.0.0.0 --port <provider PORT>
Health: /api/health
```

Use a platform-provided `PORT` value in the actual start command. The process needs outbound HTTPS access for market-data APIs and browser clients need access to the external D3 CDN used by the current frontend.

An AWS App Runner configuration is included for the current single-service
architecture. See [the AWS App Runner deployment guide](docs/AWS_APP_RUNNER.md)
for setup, verification, production limitations, and rollback guidance. The
configuration prepares the application for deployment but does not create AWS
resources.

There is deliberately no automatic deployment workflow in this repository. `.github/workflows/ci.yml` validates pushes and pull requests, but a deploy job should be added only after a hosting provider, environment, secrets, and rollback policy have been chosen.

GitHub Pages, object storage, and other static-only hosts are unsupported: they cannot execute the FastAPI application, and publishing the repository would also expose source files that are not intended to be public web assets.

### Before calling a deployment production-ready

The current code still needs production hardening:

- Choose and implement an authentication and server-side user-storage model before exposing private or multi-user data.
- Replace the wildcard CORS policy with explicit trusted origins.
- Remove or configure frontend API URLs that currently default to `localhost`/`127.0.0.1`.
- Pin and audit dependencies, add automated tests, and define logging, monitoring, backups, and rollback behavior.
- Confirm the external data providers' terms, rate limits, and availability for the intended use.

Until those items are addressed, use deployments only for controlled development or evaluation.

## Verification

The current CI performs dependency installation, `pip check`, Python bytecode compilation, starts the FastAPI application, and calls `/api/health`. The focused test suite covers application routing, removed-feature regressions, Core contracts, swing-derived direction/ranges, narrative consistency, and replay lookahead protection; it is not yet comprehensive production coverage.

To run the same basic checks locally after installing dependencies:

```bash
python -m pip install -r requirements-dev.txt
python -m pip check
python -m compileall -q backend
python -m unittest discover -s tests -p "test_*.py" -v
```

Start the server with the command above and verify that `/api/health` returns a JSON response whose `status` is `healthy`.

For historical Core evaluation, run `python -m backend.chart.engines.core.evaluation --help`. Prefer a fixed local OHLCV CSV so the generated report's dataset fingerprint and results remain reproducible. See [the Core Engine replay guide](backend/chart/engines/core/README.md#historical-replay-and-evaluation) for the report contract and its limitations.

## License

This public repository intentionally has no open-source license. Viewing the
source does not grant permission to copy, modify, redistribute, or reuse it.
