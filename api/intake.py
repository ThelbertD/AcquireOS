"""POST /api/intake — turn a completed client intake into a build specification."""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import REPO_ROOT, ToolUnavailable, load_tool, read_body, send_error_json, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        REPO_ROOT, ToolUnavailable, load_tool, read_body, send_error_json, send_json,
    )

SAMPLE = "06-onboarding/sample-intake.json"


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = REPO_ROOT / SAMPLE
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
            mod = load_tool("intake_to_spec")
            spec = mod.build_spec(data)
            markdown = mod.render(spec)
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        except Exception as exc:  # noqa: BLE001
            send_error_json(self, f"the builder failed on this input: {exc}", 400)
            return

        send_json(
            self,
            {
                "markdown": markdown,
                "blockers": spec["blockers"],
                "warnings": spec["warnings"],
                "resolved_variables": spec["resolved_variables"],
                "domain_plan": spec["domain_plan"],
                "cadence": spec["cadence"],
            },
        )

    def log_message(self, *args) -> None:
        return
