"""POST /api/cadence — the concrete cadence node map and CRM build order."""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import ToolUnavailable, as_bool, as_int, load_tool, read_body, send_error_json, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        ToolUnavailable, as_bool, as_int, load_tool, read_body, send_error_json, send_json,
    )


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value or "").split(",") if v.strip()]


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        data, error = read_body(self)
        if error:
            send_error_json(self, error)
            return

        channels = _as_list(data.get("channels")) or ["email"]
        default_lane = str(data.get("default_lane") or "").strip() or None

        try:
            mod = load_tool("cadence_builder")
            cadence = mod.build_cadence(
                segments=_as_list(data.get("segments")),
                channels=channels,
                length=as_int(data.get("length"), 8),
                segment_field=str(data.get("segment_field") or "{{SEGMENT_FIELD}}"),
                default_lane=default_lane,
                sms_consent_confirmed=as_bool(data.get("sms_consent_confirmed"), False),
            )
        except ToolUnavailable as exc:
            send_error_json(self, str(exc), 503)
            return
        except (ValueError, TypeError) as exc:
            send_error_json(self, str(exc), 400)
            return

        send_json(self, cadence)

    def log_message(self, *args) -> None:
        return
