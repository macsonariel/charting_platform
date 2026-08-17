# Contributing

Development changes should be made on a short-lived branch and merged through a
pull request. Do not push directly to `main`.

## Local verification

Create a virtual environment, install the development dependencies, and run:

```bash
python -m pip check
python -m compileall -q backend
python -m unittest discover -s tests -p "test_*.py" -v
```

For UI changes, start FastAPI and test the affected chart, panels, settings, and
responsive states in a browser. Do not open HTML files directly from disk.

## Pull requests

- Keep each pull request focused on one coherent change.
- Explain user-visible behavior, verification, risk, and rollback.
- Preserve the Core Engine as the authoritative source of market-analysis data.
- Add or update tests when changing an API contract or analysis behavior.
- Never commit credentials, `.env` files, virtual environments, logs, local
  databases, or private market datasets.
- Treat analysis results as experimental software output, not financial advice.

All required CI checks and reviews must pass before merging.
