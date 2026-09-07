"""POST /api/audit — render a deliverability audit from a findings file.

GET returns the sample input, so the editor can prefill without the frontend carrying its own
copy of a 17 KB fixture.
"""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import ToolUnavailable, load_tool, read_body, read_doc, send_error_json, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        ToolUnavailable, load_tool, read_body, read_doc, send_error_json, send_json,
    )

# The sample lives outside the document allowlist, so read it directly.
SAMPLE = "03-audit/sample-input.json"


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        from pathlib import Path

        try:
            from _lib import REPO_ROOT
        except ImportError:
            from api._lib import REPO_ROOT  # type: ignore[no-redef]

        path = Path(REPO_ROOT) / SAMPLE
        if not path.is_file():
            send_error_json(self, f"{SAMPLE} was not bundled with this function", 503)
            return
        send_json(self, {"sample": path.read_text(encoding="utf-8")})

    def do_POST(self) -> None:  # noqa: N802
        data, error = read_body(self)
        if error:
            send_error_json(self, error)
            return

        try:
            mod = load_tool("audit_report")
            warnings = mod.check_input(data)
            markdown = mod.render_report(data)
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        except Exception as exc:  # noqa: BLE001 - report, never 500 with a traceback
            send_error_json(self, f"the renderer failed on this input: {exc}", 400)
            return

        send_json(self, {"markdown": markdown, "warnings": warnings})

    def log_message(self, *args) -> None:
        return
