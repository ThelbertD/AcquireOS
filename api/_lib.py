"""Shared plumbing for the API functions.

The underscore prefix keeps Vercel from exposing this file as a route.

Nothing here implements any of the system's logic. Every endpoint loads the real planner out
of the numbered directories and calls the same function the CLI calls, so the web app and the
command line cannot disagree about what the system does.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

TOOL_PATHS = {
    "domain_plan": "02-infrastructure/domain_plan.py",
    "dns_records": "02-infrastructure/dns_records.py",
    "audit_report": "03-audit/audit_report.py",
    "cadence_builder": "04-cadence/cadence_builder.py",
    "intake_to_spec": "06-onboarding/intake_to_spec.py",
}

# Documents the browser is allowed to serve. An allowlist rather than a path check, so a
# traversal attempt cannot reach anything regardless of how it is encoded.
DOC_GROUPS: list[tuple[str, list[str]]] = [
    ("Root", ["README.md", "VARIABLES.md"]),
    (
        "01 · Sales",
        [
            "01-sales/sprint-scope-template.md",
            "01-sales/retainer-scope-template.md",
            "01-sales/pricing-model.md",
        ],
    ),
    (
        "02 · Infrastructure",
        [
            "02-infrastructure/infrastructure-runbook.md",
            "02-infrastructure/warmup-checklist.md",
        ],
    ),
    ("03 · Audit", ["03-audit/audit-template.md"]),
    (
        "04 · Cadence",
        ["04-cadence/cadence-spec.md", "04-cadence/crm-build-checklist.md"],
    ),
    (
        "05 · Copy",
        [
            "05-copy/brain-file-template.md",
            "05-copy/copy-rules.md",
            "05-copy/variant_prompt.md",
        ],
    ),
    ("06 · Onboarding", ["06-onboarding/intake-form.md"]),
    ("07 · Data", ["07-data/enrichment-spec.md"]),
]

ALLOWED_DOCS = {p for _, paths in DOC_GROUPS for p in paths}

_CACHE: dict[str, Any] = {}


class ToolUnavailable(RuntimeError):
    """The planner could not be loaded — on Vercel this is almost always a bundling problem."""


def load_tool(name: str):
    """Import one planner by path, cached for the life of the process.

    The directories are numbered (02-infrastructure), which is not a valid module name, so a
    plain import cannot reach them.
    """
    if name in _CACHE:
        return _CACHE[name]

    relative = TOOL_PATHS.get(name)
    if relative is None:
        raise ToolUnavailable(f"unknown tool {name!r}")

    path = REPO_ROOT / relative
    if not path.exists():
        raise ToolUnavailable(
            f"{relative} was not bundled with this function. Check includeFiles in vercel.json."
        )

    spec = importlib.util.spec_from_file_location(f"_acq_{name}", path)
    if spec is None or spec.loader is None:
        raise ToolUnavailable(f"could not load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CACHE[name] = module
    return module


def read_doc(relative: str) -> str | None:
    """Read one allowlisted document, or None if it is missing."""
    if relative not in ALLOWED_DOCS:
        return None
    path = REPO_ROOT / relative
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# --------------------------------------------------------------------------------------
# HTTP helpers for the BaseHTTPRequestHandler functions
# --------------------------------------------------------------------------------------


def send_json(h, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.send_header("Cache-Control", "no-store")
    h.end_headers()
    h.wfile.write(body)


def send_error_json(h, message: str, status: int = 400) -> None:
    send_json(h, {"error": message}, status)


def read_body(h) -> tuple[dict | None, str | None]:
    """Read and parse a JSON request body. Returns (data, error_message)."""
    try:
        length = int(h.headers.get("Content-Length") or 0)
    except (TypeError, ValueError):
        return None, "Content-Length header is missing or not a number"

    if length <= 0:
        return None, "the request body is empty"
    if length > 2_000_000:
        return None, "the request body is larger than 2 MB"

    try:
        raw = h.rfile.read(length).decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"could not read the request body: {exc}"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"

    if not isinstance(data, dict):
        return None, "the request body must be a JSON object"
    return data, None


def query(h) -> dict[str, str]:
    """Parse the query string into a flat dict."""
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(h.path)
    return {k: v[0] for k, v in parse_qs(parsed.query).items() if v}


def as_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")
