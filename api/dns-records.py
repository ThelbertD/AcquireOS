"""POST /api/dns-records — the DNS record set for one sending domain.

GET returns the available ESP profiles, so the form can populate its select without
hardcoding a list that would drift from dns_records.py.
"""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import ToolUnavailable, as_bool, load_tool, read_body, send_error_json, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        ToolUnavailable, as_bool, load_tool, read_body, send_error_json, send_json,
    )


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        try:
            mod = load_tool("dns_records")
            profiles = [
                {
                    "value": key,
                    "label": profile["label"],
                    "spf_include": profile["spf_include"],
                    "dkim_selector": profile["dkim_selector"],
                }
                for key, profile in sorted(mod.ESP_PROFILES.items())
            ]
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        send_json(self, {"esps": profiles})

    def do_POST(self) -> None:  # noqa: N802
        data, error = read_body(self)
        if error:
            send_error_json(self, error)
            return

        try:
            mod = load_tool("dns_records")
            records = mod.build_records(
                domain=str(data.get("domain", "")).strip(),
                esp=str(data.get("esp") or "generic"),
                dkim_selector=(str(data.get("dkim_selector")).strip() or None)
                if data.get("dkim_selector")
                else None,
                rua=str(data.get("rua") or "{{DMARC_RUA_ADDRESS}}"),
                tracking_subdomain=(str(data.get("tracking_subdomain")).strip() or None)
                if data.get("tracking_subdomain")
                else None,
                tracking_target=str(data.get("tracking_target") or "{{TRACKING_CNAME_TARGET}}"),
                include_tracking=as_bool(data.get("include_tracking"), True),
            )
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        except (ValueError, TypeError) as exc:
            send_error_json(self, str(exc), 400)
            return

        send_json(self, records)

    def log_message(self, *args) -> None:
        return
