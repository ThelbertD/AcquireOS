"""GET /api/health — is this deployment intact?

Loads every planner and checks every document is present. The fastest way to tell a broken
bundle from a broken app: if includeFiles is wrong, everything here fails at once and says so,
rather than each page failing mysteriously on its own.
"""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import ALLOWED_DOCS, REPO_ROOT, TOOL_PATHS, load_tool, read_doc, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        ALLOWED_DOCS, REPO_ROOT, TOOL_PATHS, load_tool, read_doc, send_json,
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        tools: dict[str, str] = {}
        ok = True

        for name in TOOL_PATHS:
            try:
                load_tool(name)
                tools[name] = "ok"
            except Exception as exc:  # noqa: BLE001 - a health check reports, never raises
                tools[name] = f"unavailable: {exc}"
                ok = False

        missing = sorted(p for p in ALLOWED_DOCS if read_doc(p) is None)
        if missing:
            ok = False

        send_json(
            self,
            {
                "ok": ok,
                "repo_root": str(REPO_ROOT),
                "tools": tools,
                "documents_expected": len(ALLOWED_DOCS),
                "documents_missing": missing,
            },
            200 if ok else 503,
        )

    def log_message(self, *args) -> None:
        return
