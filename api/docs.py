"""GET /api/docs — the document index, or one document's markdown.

    /api/docs            the grouped index
    /api/docs?path=...   one document, allowlisted
"""

from http.server import BaseHTTPRequestHandler

try:
    from _lib import DOC_GROUPS, query, read_doc, send_error_json, send_json
except ImportError:
    from api._lib import (  # type: ignore[no-redef]
        DOC_GROUPS, query, read_doc, send_error_json, send_json,
    )


def _title(path: str) -> str:
    stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if stem.isupper():
        return stem.title()
    return stem.replace("-", " ").replace("_", " ").capitalize()


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        params = query(self)
        wanted = params.get("path")

        if not wanted:
            send_json(
                self,
                {
                    "groups": [
                        {
                            "group": group,
                            "documents": [
                                {"path": p, "title": _title(p), "available": read_doc(p) is not None}
                                for p in paths
                            ],
                        }
                        for group, paths in DOC_GROUPS
                    ]
                },
            )
            return

        text = read_doc(wanted)
        if text is None:
            send_error_json(self, f"no document at {wanted!r}", 404)
            return

        send_json(self, {"path": wanted, "title": _title(wanted), "markdown": text})

    def log_message(self, *args) -> None:
        return
