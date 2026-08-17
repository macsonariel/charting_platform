# Trading Buddy documentation

The root `README.md` is the canonical setup and deployment reference.

## Current architecture

- `app/` contains every browser-served asset.
- `backend/main.py` creates the FastAPI application and mounts only `app/` asset directories.
- `backend/api/` contains HTTP route modules.
- `backend/chart/data/` contains market-data providers and normalization.
- `backend/chart/engines/` contains server-side analysis engines.
- `tests/` contains automated smoke tests and algorithm evaluation material.

The browser application currently has two client routes: Home (the market chart) and Settings/Profile. Profile and preference values are stored only in browser local storage.

## Documentation folders

- `reference/` contains algorithm design references and historical detector snapshots. Files here are not imported by the application.
- `evals/` contains evaluation findings.
- `archive/` contains older implementation and setup notes. These documents are retained for context but are not authoritative and may reference paths or features that no longer exist.

## Runtime boundary

Python source under `backend/` must never be exposed through a static-file mount. Browser renderers for the analysis engines live under `app/js/engines/`, with their styles under `app/css/engines/`.
