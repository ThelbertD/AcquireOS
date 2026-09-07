"""POST /api/domain-plan — turn a volume target into a sending estate plan."""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import ToolUnavailable, as_float, as_int, load_tool, read_body, send_error_json, send_json
except ImportError:  # bundled flat by some runtimes
    from api._lib import (  # type: ignore[no-redef]
        ToolUnavailable, as_float, as_int, load_tool, read_body, send_error_json, send_json,
    )


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - required name
        data, error = read_body(self)
        if error:
            send_error_json(self, error)
            return

        try:
            mod = load_tool("domain_plan")
            plan = mod.build_plan(
                primary_domain=str(data.get("primary_domain", "")).strip(),
                monthly_volume=as_int(data.get("monthly_volume"), 0),
                daily_ceiling=as_int(data.get("daily_ceiling"), 40),
                mailboxes_per_domain=as_int(data.get("mailboxes_per_domain"), 3),
                sending_days=as_int(data.get("sending_days"), 22),
                headroom=as_float(data.get("headroom"), 0.2),
            )
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        except (ValueError, TypeError) as exc:
            send_error_json(self, str(exc), 400)
            return

        send_json(self, plan)

    def log_message(self, *args) -> None:  # keep the function logs quiet
        return
