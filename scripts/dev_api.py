#!/usr/bin/env python3
"""Local stand-in for the Vercel Python functions.

On Vercel each file in api/ is deployed as its own serverless function and routed by filename.
Nothing runs them locally, so this serves the same handlers on one port and `next dev` proxies
/api/* here (see next.config.mjs).

    python scripts/dev_api.py          # serves on 127.0.0.1:8787

This exists only for development. It is not deployed and Vercel never sees it.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "api"

# api/_lib.py is imported by the function modules as a top-level module, exactly as it is on
# Vercel, so the same import works in both places.
sys.path.insert(0, str(API_DIR))

ROUTES = {
    "/api/domain-plan": "domain-plan.py",
    "/api/dns-records": "dns-records.py",
    "/api/cadence": "cadence.py",
    "/api/audit": "audit.py",
    "/api/intake": "intake.py",
    "/api/docs": "docs.py",
    "/api/health": "health.py",
}

_loaded: dict[str, type] = {}


def handler_for(route: str) -> type | None:
    """Load the handler class for a route, cached."""
    if route in _loaded:
        return _loaded[route]

    filename = ROUTES.get(route)
    if filename is None:
        return None

    path = API_DIR / filename
    if not path.is_file():
        return None

    module_name = f"_devapi_{filename.replace('-', '_').replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    cls = getattr(module, "handler", None)
    if cls is None:
        return None
    _loaded[route] = cls
    return cls


class Router(BaseHTTPRequestHandler):
    """Dispatches to the real function handlers.

    The function handlers subclass BaseHTTPRequestHandler and only ever touch `self.path`,
    `self.headers`, `self.rfile` and the response helpers, so their methods can be called with
    this instance as `self`. That keeps one implementation rather than a development copy.
    """

    server_version = "AcquireOS-dev"

    def _dispatch(self, method: str) -> None:
        route = urlparse(self.path).path.rstrip("/") or "/"
        cls = handler_for(route)

        if cls is None:
            self._json(404, {"error": f"no route at {route}", "routes": sorted(ROUTES)})
            return

        func = getattr(cls, method, None)
        if func is None:
            self._json(405, {"error": f"{method[3:].upper()} not allowed on {route}"})
            return

        try:
            func(self)
        except Exception as exc:  # noqa: BLE001 - dev server reports rather than dying
            import traceback

            traceback.print_exc()
            try:
                self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            except Exception:  # noqa: BLE001 - response already partly written
                pass

    def _json(self, status: int, payload: dict) -> None:
        import json

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("do_GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("do_POST")

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"  api  {fmt % args}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    missing = [r for r in ROUTES if handler_for(r) is None]
    if missing:
        print(f"error: could not load handlers for: {', '.join(missing)}", file=sys.stderr)
        return 1

    server = ThreadingHTTPServer((args.host, args.port), Router)
    print(f"AcquireOS dev API on http://{args.host}:{args.port}")
    for route in sorted(ROUTES):
        print(f"  {route}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
