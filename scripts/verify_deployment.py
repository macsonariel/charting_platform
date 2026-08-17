"""Verify that a deployed Trading Buddy service and its Core Engine are usable."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def get_json(base_url: str, path: str, timeout: float) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urlopen(url, timeout=timeout) as response:  # noqa: S310 - operator supplies URL
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{url} returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach {url}: {error.reason}") from error

    if not isinstance(payload, dict):
        raise RuntimeError(f"{url} returned an unexpected payload")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="App Runner or custom-domain URL")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--periods", type=int, default=300)
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    health = get_json(args.base_url, "/api/health", args.timeout)
    if health.get("status") != "healthy":
        raise RuntimeError(f"Health check is not healthy: {health}")
    print("PASS health endpoint")

    query = urlencode(
        {"symbol": args.symbol, "timeframe": args.timeframe, "periods": args.periods}
    )
    summary = get_json(args.base_url, f"/api/core/summary?{query}", args.timeout)
    if summary.get("engine") != "core":
        raise RuntimeError(f"Core summary has an unexpected contract: {summary}")
    print(
        "PASS Core analysis "
        f"({args.symbol} {args.timeframe}, schema {summary.get('schema_version', 'unknown')})"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        sys.exit(1)
