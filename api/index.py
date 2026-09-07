"""AcquireOS — web entrypoint.

An ASGI app exposing the toolkit's five planners as forms, plus a browser for the fifteen
markdown templates. This is the Vercel entrypoint; `app` is what the runtime looks for.

No logic lives here. Every tool is imported by path from the numbered directories and called
through the same pure functions the CLIs call, so the web app and the command line can never
disagree about what the system does.

Run locally:
    pip install -r requirements.txt
    uvicorn api.index:app --reload
    # then open http://127.0.0.1:8000
"""

from __future__ import annotations

import html
import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

REPO_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="AcquireOS",
    description="Outbound pipeline system",
    docs_url="/api/docs",
    redoc_url=None,
)


# ======================================================================================
# Loading the toolkit
#
# The directories are numbered (02-infrastructure), which is not a valid module name, so a
# plain import cannot reach them. Loading by path keeps one implementation of every planner
# rather than a second copy in the web layer that drifts from the CLI.
# ======================================================================================

_MODULE_CACHE: dict[str, Any] = {}

TOOL_PATHS = {
    "domain_plan": "02-infrastructure/domain_plan.py",
    "dns_records": "02-infrastructure/dns_records.py",
    "audit_report": "03-audit/audit_report.py",
    "cadence_builder": "04-cadence/cadence_builder.py",
    "intake_to_spec": "06-onboarding/intake_to_spec.py",
}


class ToolUnavailable(RuntimeError):
    """The tool module could not be loaded — almost always a bundling problem."""


def load_tool(name: str):
    """Import one toolkit module by path, cached for the life of the process."""
    if name in _MODULE_CACHE:
        return _MODULE_CACHE[name]

    relative = TOOL_PATHS.get(name)
    if relative is None:
        raise ToolUnavailable(f"unknown tool {name!r}")

    path = REPO_ROOT / relative
    if not path.exists():
        raise ToolUnavailable(
            f"{relative} was not found at {path}. On Vercel this means the numbered "
            f"directories were not bundled with the function — check includeFiles in "
            f"vercel.json."
        )

    spec = importlib.util.spec_from_file_location(f"_acquireos_{name}", path)
    if spec is None or spec.loader is None:
        raise ToolUnavailable(f"could not load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _MODULE_CACHE[name] = module
    return module


def read_repo_file(relative: str) -> str | None:
    """Read a file from the repo, or None if it was not bundled."""
    path = (REPO_ROOT / relative).resolve()
    # Never serve anything outside the repo, whatever the request asked for.
    if not str(path).startswith(str(REPO_ROOT)):
        return None
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# ======================================================================================
# Presentation
# ======================================================================================

CSS = """
:root {
  --bg:        #0b0e17;
  --panel:     #131826;
  --panel-2:   #1a2032;
  --line:      #252d42;
  --line-soft: #1c2333;
  --text:      #e8ecf6;
  --muted:     #98a3bd;
  --dim:       #6b7794;
  --accent:    #5b7cfa;
  --accent-2:  #7c9bff;
  --good:      #3fb984;
  --warn:      #e0a33a;
  --bad:       #ef5f5f;
  --radius:    12px;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16.5px/1.65 ui-sans-serif, -apple-system, "Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent-2); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ---- shell ---- */
.shell { display: flex; min-height: 100vh; }
.sidebar {
  width: 268px; flex: 0 0 268px;
  background: var(--panel);
  border-right: 1px solid var(--line);
  padding: 22px 16px 40px;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.main { flex: 1 1 auto; min-width: 0; padding: 38px 44px 80px; max-width: 1180px; }

/* ---- brand ---- */
.brand { display: flex; align-items: center; gap: 12px; padding: 4px 8px 22px; }
.brand-mark {
  width: 42px; height: 42px; flex: 0 0 42px;
  border-radius: 11px;
  background: linear-gradient(145deg, var(--accent), #3d5fe0);
  display: grid; place-items: center;
  font-weight: 800; font-size: 22px; color: #fff;
  box-shadow: 0 3px 14px rgba(91,124,250,.4);
}
.brand-name { font-size: 21px; font-weight: 750; letter-spacing: -.2px; line-height: 1.15; }
.brand-sub {
  font-size: 11.5px; font-weight: 650; letter-spacing: .1em; text-transform: uppercase;
  color: var(--accent-2); margin-top: 3px;
}

/* ---- nav ---- */
.nav-group { margin-bottom: 20px; }
.nav-label {
  font-size: 11px; font-weight: 700; letter-spacing: .11em; text-transform: uppercase;
  color: var(--dim); padding: 0 10px 8px;
}
.nav a {
  display: block; padding: 9px 11px; border-radius: 8px;
  color: var(--muted); font-size: 15px; font-weight: 500;
}
.nav a:hover { background: var(--panel-2); color: var(--text); text-decoration: none; }
.nav a.on { background: rgba(91,124,250,.16); color: var(--accent-2); font-weight: 600; }

/* ---- type ---- */
h1 { font-size: 33px; font-weight: 750; letter-spacing: -.5px; margin: 0 0 10px; }
h2 { font-size: 23px; font-weight: 700; letter-spacing: -.2px; margin: 34px 0 12px;
     padding-bottom: 9px; border-bottom: 1px solid var(--line-soft); }
h3 { font-size: 18.5px; font-weight: 650; margin: 26px 0 8px; }
h4 { font-size: 16.5px; font-weight: 650; margin: 20px 0 6px; color: var(--muted); }
.lede { font-size: 17.5px; color: var(--muted); margin: 0 0 26px; max-width: 76ch; }
p { max-width: 82ch; }

/* ---- cards ---- */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(272px, 1fr)); gap: 16px; }
.card {
  display: block; background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 20px; color: inherit;
}
.card:hover { border-color: var(--accent); text-decoration: none; transform: translateY(-1px); }
.card h3 { margin: 0 0 6px; font-size: 17.5px; }
.card p { margin: 0; color: var(--muted); font-size: 14.5px; line-height: 1.55; }
.card .tag {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--dim); margin-bottom: 9px;
}

/* ---- forms ---- */
form { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius);
       padding: 24px; margin: 20px 0 30px; }
.field { margin-bottom: 17px; }
.field-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 17px; }
label { display: block; font-size: 14.5px; font-weight: 600; margin-bottom: 6px; }
.hint { font-size: 13.5px; color: var(--dim); font-weight: 400; margin-top: 4px; }
input[type=text], input[type=number], select, textarea {
  width: 100%; padding: 10px 12px; font-size: 15.5px;
  background: var(--bg); color: var(--text);
  border: 1px solid var(--line); border-radius: 8px;
  font-family: inherit;
}
textarea { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: 13.5px;
           line-height: 1.55; min-height: 320px; resize: vertical; }
input:focus, select:focus, textarea:focus {
  outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,124,250,.18);
}
.checks { display: flex; flex-wrap: wrap; gap: 18px; }
.check { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 500; }
.check input { width: 17px; height: 17px; accent-color: var(--accent); }
button {
  background: var(--accent); color: #fff; border: 0; border-radius: 8px;
  padding: 11px 22px; font-size: 15.5px; font-weight: 650; cursor: pointer;
  font-family: inherit;
}
button:hover { background: var(--accent-2); }

/* ---- output ---- */
pre {
  background: #070a11; border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px 20px; overflow-x: auto;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  font-size: 13.5px; line-height: 1.6; color: #cfd8ee;
}
code { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: .92em;
       background: var(--panel-2); padding: 2px 6px; border-radius: 5px; color: var(--accent-2); }
pre code { background: none; padding: 0; color: inherit; font-size: inherit; }

table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14.5px; display: block;
        overflow-x: auto; white-space: normal; }
th, td { border: 1px solid var(--line); padding: 9px 13px; text-align: left; vertical-align: top; }
th { background: var(--panel-2); font-weight: 650; font-size: 13.5px;
     letter-spacing: .02em; color: var(--muted); }
tbody tr:nth-child(even) { background: rgba(255,255,255,.014); }

blockquote { border-left: 3px solid var(--accent); background: var(--panel);
             margin: 16px 0; padding: 12px 18px; color: var(--muted); border-radius: 0 8px 8px 0; }
blockquote p { margin: 6px 0; }
ul, ol { max-width: 82ch; }
li { margin: 5px 0; }
hr { border: 0; border-top: 1px solid var(--line-soft); margin: 30px 0; }

/* ---- notices ---- */
.notice { border-radius: var(--radius); padding: 15px 18px; margin: 16px 0;
          font-size: 15px; border: 1px solid; }
.notice-warn { background: rgba(224,163,58,.09); border-color: rgba(224,163,58,.4); }
.notice-bad  { background: rgba(239,95,95,.09);  border-color: rgba(239,95,95,.42); }
.notice-good { background: rgba(63,185,132,.09); border-color: rgba(63,185,132,.4); }
.notice ul { margin: 8px 0 0; padding-left: 20px; }
.notice strong { color: var(--text); }

.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px; margin: 20px 0; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 15px 17px; }
.stat .k { font-size: 12px; font-weight: 650; letter-spacing: .07em; text-transform: uppercase;
           color: var(--dim); }
.stat .v { font-size: 25px; font-weight: 720; margin-top: 4px; letter-spacing: -.4px; }

.muted { color: var(--muted); }
.small { font-size: 14px; }

@media (max-width: 900px) {
  .shell { flex-direction: column; }
  .sidebar { width: auto; flex: none; height: auto; position: static; border-right: 0;
             border-bottom: 1px solid var(--line); }
  .main { padding: 26px 20px 60px; }
  h1 { font-size: 27px; }
}
"""

NAV = [
    (
        "Planners",
        [
            ("/", "Overview"),
            ("/tools/domain-plan", "Domain plan"),
            ("/tools/dns-records", "DNS records"),
            ("/tools/cadence", "Cadence builder"),
            ("/tools/audit", "Audit report"),
            ("/tools/intake", "Intake to spec"),
        ],
    ),
    (
        "Reference",
        [
            ("/docs", "All documents"),
            ("/docs/VARIABLES.md", "Variables"),
            ("/docs/04-cadence/cadence-spec.md", "Cadence spec"),
            ("/docs/05-copy/copy-rules.md", "Copy rules"),
            ("/docs/07-data/enrichment-spec.md", "Enrichment spec"),
        ],
    ),
]


def layout(title: str, body: str, active: str = "") -> HTMLResponse:
    nav_html = []
    for group, links in NAV:
        items = "".join(
            f'<a href="{href}" class="{"on" if href == active else ""}">{html.escape(label)}</a>'
            for href, label in links
        )
        nav_html.append(
            f'<div class="nav-group"><div class="nav-label">{group}</div>'
            f'<div class="nav">{items}</div></div>'
        )

    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · AcquireOS</title>
<style>{CSS}</style>
</head><body>
<div class="shell">
  <aside class="sidebar">
    <a href="/" class="brand" style="text-decoration:none;color:inherit">
      <div class="brand-mark">A</div>
      <div>
        <div class="brand-name">AcquireOS</div>
        <div class="brand-sub">Outbound Pipeline OS</div>
      </div>
    </a>
    {''.join(nav_html)}
  </aside>
  <main class="main">{body}</main>
</div>
</body></html>"""
    )


def error_page(title: str, message: str, detail: str = "", status: int = 404) -> HTMLResponse:
    body = f"<h1>{html.escape(title)}</h1><div class='notice notice-bad'>{html.escape(message)}</div>"
    if detail:
        body += f"<pre>{html.escape(detail)}</pre>"
    response = layout(title, body)
    response.status_code = status
    return response


def esc(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def md_to_html(text: str) -> str:
    """Render markdown to HTML, with raw HTML in the source neutralized.

    Python-Markdown passes embedded HTML straight through, and some of what is rendered here
    comes from user-supplied JSON — an audit findings file, a client intake. A client_name of
    "<script>...</script>" would otherwise execute.

    Only '<' is escaped, not '>'. A tag cannot form without '<', so that is enough to stop
    injection, and leaving '>' alone keeps markdown blockquotes working — the templates use
    them heavily. The trade-off is that angle-bracket autolinks (<https://...>) render as
    literal text; the documents here use bare URLs, so nothing relies on them.
    """
    safe = text.replace("<", "&lt;")
    try:
        import markdown

        return markdown.markdown(
            safe,
            extensions=["tables", "fenced_code", "sane_lists", "toc"],
            output_format="html5",
        )
    except ImportError:
        return f"<pre>{html.escape(text)}</pre>"


# ======================================================================================
# Overview
# ======================================================================================

TOOL_CARDS = [
    (
        "/tools/domain-plan",
        "02 · Infrastructure",
        "Domain plan",
        "Turn a monthly volume target into a domain and mailbox count, with the arithmetic "
        "shown and name suggestions to check.",
    ),
    (
        "/tools/dns-records",
        "02 · Infrastructure",
        "DNS records",
        "Generate the SPF, DKIM, DMARC, MX and tracking record set for one sending domain, "
        "with a client-facing explanation of each.",
    ),
    (
        "/tools/cadence",
        "04 · Cadence",
        "Cadence builder",
        "Build the node map and the CRM build order from your lanes, channels and cadence "
        "length.",
    ),
    (
        "/tools/audit",
        "03 · Audit",
        "Audit report",
        "Render a deliverability audit from a findings file, with the remediation list built "
        "automatically from the findings.",
    ),
    (
        "/tools/intake",
        "06 · Onboarding",
        "Intake to spec",
        "Turn a completed client intake into a build specification, with everything that "
        "blocks the build flagged.",
    ),
]


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    cards = "".join(
        f'<a class="card" href="{href}"><div class="tag">{esc(tag)}</div>'
        f"<h3>{esc(name)}</h3><p>{esc(desc)}</p></a>"
        for href, tag, name, desc in TOOL_CARDS
    )
    body = f"""
<h1>AcquireOS</h1>
<p class="lede">The internal toolkit for building and running cold email infrastructure and
managed outbound pipelines. Client-agnostic: every client-specific value is a placeholder,
and no client data lives here.</p>

<h2>Planners</h2>
<div class="grid">{cards}</div>

<h2>How an engagement runs</h2>
<pre>intake-form.md            client fills this
        |
        v
intake to spec            build spec + blocker list
        |
        +--&gt; domain plan  --&gt; DNS records --&gt; warmup (3-4 weeks)
        |
        +--&gt; cadence builder --&gt; CRM build checklist
        |
        +--&gt; brain file   --&gt; copy variants
        |
        +--&gt; schema.sql   --&gt; list pipeline
                 |
                 v
          live sending, then audit on a recurring basis</pre>

<h2>Compliance</h2>
<p>CAN-SPAM, GDPR + PECR and CASL are build requirements here, not review items. Where the
three regimes differ, the artifacts branch by jurisdiction rather than picking the loosest
rule. The per-artifact rules are in <a href="/docs/05-copy/copy-rules.md">copy rules</a>.</p>
<div class="notice notice-warn"><strong>Canada is the exception that cannot be handled by
building to the strictest reading.</strong> CASL requires a lawful basis before the first
message, so it cannot be satisfied retroactively by good opt-out handling. Either the basis is
recorded per contact, or Canadian contacts are excluded from the list.</div>

<h2>Command line</h2>
<p class="small muted">Every planner here is the same code the CLI runs. Nothing is duplicated.</p>
<pre>python 02-infrastructure/domain_plan.py --primary-domain example.com --monthly-volume 20000
python 02-infrastructure/dns_records.py --domain example-hq.com --esp google-workspace --verify
python 04-cadence/cadence_builder.py --segments enterprise,mid-market --channels email
python 03-audit/audit_report.py --input 03-audit/sample-input.json
python 06-onboarding/intake_to_spec.py --input 06-onboarding/sample-intake.json
python 07-data/list_pipeline.py --csv leads.csv --mapping mapping.json --dry-run</pre>
"""
    return layout("Overview", body, active="/")


# ======================================================================================
# Domain plan
# ======================================================================================


def _domain_plan_form(v: dict) -> str:
    return f"""
<form method="post">
  <div class="field">
    <label for="primary_domain">Primary domain</label>
    <input type="text" id="primary_domain" name="primary_domain" value="{esc(v['primary_domain'])}" required>
    <div class="hint">The client's main brand domain. Never used for cold sending.</div>
  </div>
  <div class="field-row">
    <div class="field">
      <label for="monthly_volume">Target sends per month</label>
      <input type="number" id="monthly_volume" name="monthly_volume" value="{esc(v['monthly_volume'])}" min="1" required>
    </div>
    <div class="field">
      <label for="daily_ceiling">Daily ceiling per mailbox</label>
      <input type="number" id="daily_ceiling" name="daily_ceiling" value="{esc(v['daily_ceiling'])}" min="1" max="100">
    </div>
    <div class="field">
      <label for="mailboxes_per_domain">Mailboxes per domain</label>
      <input type="number" id="mailboxes_per_domain" name="mailboxes_per_domain" value="{esc(v['mailboxes_per_domain'])}" min="1" max="5">
    </div>
  </div>
  <div class="field-row">
    <div class="field">
      <label for="sending_days">Sending days per month</label>
      <input type="number" id="sending_days" name="sending_days" value="{esc(v['sending_days'])}" min="1" max="31">
    </div>
    <div class="field">
      <label for="headroom">Headroom</label>
      <input type="text" id="headroom" name="headroom" value="{esc(v['headroom'])}">
      <div class="hint">Spare capacity, 0 to 1. Lets one domain be pulled without missing target.</div>
    </div>
  </div>
  <button type="submit">Build the plan</button>
</form>"""


@app.get("/tools/domain-plan", response_class=HTMLResponse)
def domain_plan_get() -> HTMLResponse:
    defaults = {
        "primary_domain": "example.com",
        "monthly_volume": 20000,
        "daily_ceiling": 40,
        "mailboxes_per_domain": 3,
        "sending_days": 22,
        "headroom": "0.2",
    }
    body = (
        "<h1>Domain plan</h1>"
        '<p class="lede">How many sending domains and mailboxes a volume target needs, and '
        "what each mailbox may send. No availability lookups — this produces a plan a human "
        "executes.</p>" + _domain_plan_form(defaults)
    )
    return layout("Domain plan", body, active="/tools/domain-plan")


@app.post("/tools/domain-plan", response_class=HTMLResponse)
def domain_plan_post(
    primary_domain: str = Form(...),
    monthly_volume: int = Form(...),
    daily_ceiling: int = Form(40),
    mailboxes_per_domain: int = Form(3),
    sending_days: int = Form(22),
    headroom: str = Form("0.2"),
) -> HTMLResponse:
    values = {
        "primary_domain": primary_domain,
        "monthly_volume": monthly_volume,
        "daily_ceiling": daily_ceiling,
        "mailboxes_per_domain": mailboxes_per_domain,
        "sending_days": sending_days,
        "headroom": headroom,
    }
    form = _domain_plan_form(values)

    try:
        mod = load_tool("domain_plan")
        plan = mod.build_plan(
            primary_domain=primary_domain,
            monthly_volume=monthly_volume,
            daily_ceiling=daily_ceiling,
            mailboxes_per_domain=mailboxes_per_domain,
            sending_days=sending_days,
            headroom=float(headroom),
        )
    except ToolUnavailable as exc:
        return layout(
            "Domain plan",
            f"<h1>Domain plan</h1>{form}"
            f"<div class='notice notice-bad'>{esc(exc)}</div>",
            active="/tools/domain-plan",
        )
    except (ValueError, TypeError) as exc:
        return layout(
            "Domain plan",
            f"<h1>Domain plan</h1>{form}"
            f"<div class='notice notice-bad'><strong>Cannot plan that.</strong><br>{esc(exc)}</div>",
            active="/tools/domain-plan",
        )

    p = plan["plan"]
    stats = f"""
<div class="stat-row">
  <div class="stat"><div class="k">Domains</div><div class="v">{p['secondary_domains']}</div></div>
  <div class="stat"><div class="k">Mailboxes</div><div class="v">{p['total_mailboxes']}</div></div>
  <div class="stat"><div class="k">Per day</div><div class="v">{p['estate_daily_capacity']:,}</div></div>
  <div class="stat"><div class="k">Utilisation</div><div class="v">{p['utilisation_at_target']:.0%}</div></div>
</div>"""

    resilience = (
        '<div class="notice notice-good">Holds target volume with one domain pulled from '
        f"rotation ({p['degraded_daily_capacity']:,}/day degraded).</div>"
        if p["survives_losing_one_domain"]
        else '<div class="notice notice-warn"><strong>Does not hold target volume with one '
        "domain pulled from rotation</strong> — degraded capacity is "
        f"{p['degraded_daily_capacity']:,}/day. Add a domain, or accept that a reputation "
        "incident cuts throughput.</div>"
    )

    rows = "".join(
        f"<tr><td>{n}</td><td><code>{esc(s['domain'])}</code></td><td>{esc(s['rationale'])}</td></tr>"
        for n, s in enumerate(plan["suggested_domains"], start=1)
    )
    notes = "".join(f"<li>{esc(note)}</li>" for note in plan["notes"])

    body = f"""<h1>Domain plan</h1>
<p class="lede">{esc(plan['inputs']['primary_domain'])} &middot;
{plan['inputs']['monthly_volume']:,} sends per month</p>
{form}
{stats}
{resilience}
<h2>Arithmetic</h2>
<pre>{esc(chr(10).join(plan['arithmetic']))}</pre>
<h2>Suggested domain names</h2>
<p class="small muted">Check availability and registration history manually. A previously-owned
domain carries its previous owner's reputation, which you cannot see and cannot fix.</p>
<table><thead><tr><th>#</th><th>Domain</th><th>Rationale</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Notes</h2>
<ul>{notes}</ul>"""
    return layout("Domain plan", body, active="/tools/domain-plan")


# ======================================================================================
# DNS records
# ======================================================================================


def _dns_form(v: dict, esps: list[tuple[str, str]]) -> str:
    options = "".join(
        f'<option value="{esc(k)}"{" selected" if k == v["esp"] else ""}>{esc(label)}</option>'
        for k, label in esps
    )
    return f"""
<form method="post">
  <div class="field-row">
    <div class="field">
      <label for="domain">Sending domain</label>
      <input type="text" id="domain" name="domain" value="{esc(v['domain'])}" required>
    </div>
    <div class="field">
      <label for="esp">Email service provider</label>
      <select id="esp" name="esp">{options}</select>
    </div>
  </div>
  <div class="field-row">
    <div class="field">
      <label for="rua">DMARC report address</label>
      <input type="text" id="rua" name="rua" value="{esc(v['rua'])}">
      <div class="hint">Must be a real mailbox that someone reads.</div>
    </div>
    <div class="field">
      <label for="dkim_selector">DKIM selector</label>
      <input type="text" id="dkim_selector" name="dkim_selector" value="{esc(v['dkim_selector'])}">
      <div class="hint">Leave blank for the provider default.</div>
    </div>
  </div>
  <div class="field checks">
    <label class="check"><input type="checkbox" name="include_tracking" value="1"
      {"checked" if v["include_tracking"] else ""}> Include tracking CNAME</label>
    <label class="check"><input type="checkbox" name="verify" value="1"
      {"checked" if v["verify"] else ""}> Include the plain-English explanation</label>
  </div>
  <button type="submit">Generate records</button>
</form>"""


def _dns_defaults() -> dict:
    return {
        "domain": "example-hq.com",
        "esp": "google-workspace",
        "rua": "{{DMARC_RUA_ADDRESS}}",
        "dkim_selector": "",
        "include_tracking": True,
        "verify": True,
    }


def _esp_choices() -> list[tuple[str, str]]:
    try:
        mod = load_tool("dns_records")
        return [(k, v["label"]) for k, v in sorted(mod.ESP_PROFILES.items())]
    except ToolUnavailable:
        return [("generic", "Generic / other provider")]


@app.get("/tools/dns-records", response_class=HTMLResponse)
def dns_get() -> HTMLResponse:
    body = (
        "<h1>DNS records</h1>"
        '<p class="lede">The full record set for one sending domain. Values in double braces '
        "are placeholders you replace before publishing.</p>"
        + _dns_form(_dns_defaults(), _esp_choices())
    )
    return layout("DNS records", body, active="/tools/dns-records")


@app.post("/tools/dns-records", response_class=HTMLResponse)
def dns_post(
    domain: str = Form(...),
    esp: str = Form("generic"),
    rua: str = Form("{{DMARC_RUA_ADDRESS}}"),
    dkim_selector: str = Form(""),
    include_tracking: str = Form(""),
    verify: str = Form(""),
) -> HTMLResponse:
    values = {
        "domain": domain,
        "esp": esp,
        "rua": rua or "{{DMARC_RUA_ADDRESS}}",
        "dkim_selector": dkim_selector,
        "include_tracking": bool(include_tracking),
        "verify": bool(verify),
    }
    form = _dns_form(values, _esp_choices())

    try:
        mod = load_tool("dns_records")
        rs = mod.build_records(
            domain=domain,
            esp=esp,
            dkim_selector=dkim_selector or None,
            rua=rua or "{{DMARC_RUA_ADDRESS}}",
            include_tracking=bool(include_tracking),
        )
    except ToolUnavailable as exc:
        return layout("DNS records", f"<h1>DNS records</h1>{form}"
                      f"<div class='notice notice-bad'>{esc(exc)}</div>",
                      active="/tools/dns-records")
    except (ValueError, TypeError) as exc:
        return layout("DNS records", f"<h1>DNS records</h1>{form}"
                      f"<div class='notice notice-bad'><strong>Cannot generate records.</strong>"
                      f"<br>{esc(exc)}</div>", active="/tools/dns-records")

    rows = "".join(
        f"<tr><td><code>{esc(r['type'])}</code></td><td><code>{esc(r['host'])}</code></td>"
        f"<td>{r['ttl']}</td><td><code>{esc(r['value'])}</code></td>"
        f"<td class='small muted'>{esc(r['purpose'])}</td></tr>"
        for r in rs["records"]
    )
    checks = "\n".join(f"# {r['purpose']}\n{r['check']}" for r in rs["records"])

    explain = ""
    if values["verify"]:
        blocks = []
        for n, r in enumerate(rs["records"], start=1):
            blocks.append(
                f"<h3>{n}. {esc(r['purpose'])} "
                f"<span class='small muted'>&mdash; {esc(r['type'])} on "
                f"<code>{esc(r['fqdn'])}</code></span></h3>"
                f"<p>{esc(r['explanation'])}</p>"
            )
        explain = (
            "<h2>What these records do</h2>"
            "<p class='small muted'>Suitable to send to a client as-is.</p>"
            + "".join(blocks)
            + "<h3>Why DMARC starts at p=none</h3><p>A DMARC policy of reject tells the world "
            "to throw away any mail from this domain that fails authentication. That is the "
            "destination, not the starting point. Published on day one it will discard "
            "legitimate mail from any system nobody remembered to authorise, silently, with no "
            "bounce. Publish p=none, read the aggregate reports for two to four weeks until "
            "every legitimate source is accounted for, move to quarantine, watch for two more "
            "weeks, then move to reject.</p>"
        )

    body = f"""<h1>DNS records</h1>
<p class="lede">{esc(rs['domain'])} &middot; {esc(rs['esp_label'])}</p>
{form}
<h2>Records</h2>
<table><thead><tr><th>Type</th><th>Host</th><th>TTL</th><th>Value</th><th>Purpose</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="notice notice-warn"><strong>DKIM key.</strong> {esc(rs['dkim_note'])}
Publish every other record first, then generate the key and publish it last. Activating signing
before the record resolves fails DKIM on every message sent in the gap.</div>
<h2>Order of operations</h2>
<ol>
<li>Publish MX, SPF and DMARC.</li>
<li>Wait for propagation and confirm with the checks below.</li>
<li>Generate the DKIM key, publish it, <em>then</em> activate signing.</li>
<li>Publish the tracking CNAME only if tracking will be used.</li>
<li>Send one message to a seed address and read the raw headers. All three of
<code>spf=pass</code>, <code>dkim=pass</code> and <code>dmarc=pass</code> must appear before any
warmup traffic starts.</li>
</ol>
<h2>Verification</h2>
<pre>{esc(checks)}</pre>
{explain}"""
    return layout("DNS records", body, active="/tools/dns-records")


# ======================================================================================
# Cadence builder
# ======================================================================================


def _cadence_form(v: dict) -> str:
    return f"""
<form method="post">
  <div class="field">
    <label for="segments">Segment lanes</label>
    <input type="text" id="segments" name="segments" value="{esc(v['segments'])}" required>
    <div class="hint">Comma-separated. Maximum six — past that the copy volume outruns any
    team's ability to iterate on it.</div>
  </div>
  <div class="field-row">
    <div class="field">
      <label for="segment_field">Segment field</label>
      <input type="text" id="segment_field" name="segment_field" value="{esc(v['segment_field'])}">
      <div class="hint">The contact field the router reads.</div>
    </div>
    <div class="field">
      <label for="default_lane">Default lane</label>
      <input type="text" id="default_lane" name="default_lane" value="{esc(v['default_lane'])}">
      <div class="hint">Catches null and unmapped values. Blank uses the last lane.</div>
    </div>
    <div class="field">
      <label for="length">Length in business days</label>
      <input type="number" id="length" name="length" value="{esc(v['length'])}" min="3" max="30">
    </div>
  </div>
  <div class="field">
    <label>Channels</label>
    <div class="checks">
      <label class="check"><input type="checkbox" name="email" value="1" checked disabled>
        Email <span class="hint" style="margin:0">(always required)</span></label>
      <label class="check"><input type="checkbox" name="sms" value="1"
        {"checked" if v["sms"] else ""}> SMS</label>
      <label class="check"><input type="checkbox" name="sms_consent_confirmed" value="1"
        {"checked" if v["sms_consent_confirmed"] else ""}> SMS consent basis confirmed</label>
    </div>
  </div>
  <button type="submit">Build the node map</button>
</form>"""


@app.get("/tools/cadence", response_class=HTMLResponse)
def cadence_get() -> HTMLResponse:
    defaults = {
        "segments": "enterprise, mid-market, smb",
        "segment_field": "{{SEGMENT_FIELD}}",
        "default_lane": "",
        "length": 8,
        "sms": False,
        "sms_consent_confirmed": False,
    }
    body = (
        "<h1>Cadence builder</h1>"
        '<p class="lede">The concrete node map for one client, plus the order to build it in a '
        "CRM. Architecture is in the "
        '<a href="/docs/04-cadence/cadence-spec.md">cadence spec</a>.</p>'
        + _cadence_form(defaults)
    )
    return layout("Cadence builder", body, active="/tools/cadence")


@app.post("/tools/cadence", response_class=HTMLResponse)
def cadence_post(
    segments: str = Form(...),
    segment_field: str = Form("{{SEGMENT_FIELD}}"),
    default_lane: str = Form(""),
    length: int = Form(8),
    sms: str = Form(""),
    sms_consent_confirmed: str = Form(""),
) -> HTMLResponse:
    values = {
        "segments": segments,
        "segment_field": segment_field,
        "default_lane": default_lane,
        "length": length,
        "sms": bool(sms),
        "sms_consent_confirmed": bool(sms_consent_confirmed),
    }
    form = _cadence_form(values)
    channels = ["email"] + (["sms"] if sms else [])

    try:
        mod = load_tool("cadence_builder")
        c = mod.build_cadence(
            segments=[s.strip() for s in segments.split(",") if s.strip()],
            channels=channels,
            length=length,
            segment_field=segment_field or "{{SEGMENT_FIELD}}",
            default_lane=default_lane.strip() or None,
            sms_consent_confirmed=bool(sms_consent_confirmed),
        )
    except ToolUnavailable as exc:
        return layout("Cadence builder", f"<h1>Cadence builder</h1>{form}"
                      f"<div class='notice notice-bad'>{esc(exc)}</div>", active="/tools/cadence")
    except (ValueError, TypeError) as exc:
        return layout("Cadence builder", f"<h1>Cadence builder</h1>{form}"
                      f"<div class='notice notice-bad'><strong>Cannot build that cadence.</strong>"
                      f"<br>{esc(exc)}</div>", active="/tools/cadence")

    t = c["totals"]
    stats = f"""
<div class="stat-row">
  <div class="stat"><div class="k">Lanes</div><div class="v">{t['lanes']}</div></div>
  <div class="stat"><div class="k">Nodes per lane</div><div class="v">{t['nodes_per_lane']}</div></div>
  <div class="stat"><div class="k">Node instances</div><div class="v">{t['main_sequence_node_instances']}</div></div>
  <div class="stat"><div class="k">Copy pieces</div><div class="v">{t['copy_pieces_required']}</div></div>
</div>"""

    warnings = ""
    if c["warnings"]:
        items = "".join(f"<li>{esc(w)}</li>" for w in c["warnings"])
        warnings = f'<div class="notice notice-warn"><strong>Warnings</strong><ul>{items}</ul></div>'

    nodes = "".join(
        f"<tr><td><code>{esc(n['node'])}</code></td><td>{n['day']}</td>"
        f"<td>{esc(n['channel'])}</td><td>{esc(n['purpose'])}</td>"
        f"<td class='small muted'>{esc(n['exit'])}</td></tr>"
        for n in c["nodes"]
    )
    ft = "".join(
        f"<tr><td><code>{esc(f['node'])}</code></td><td>{f['day']}</td>"
        f"<td>{esc(f['channel'])}</td><td>{esc(f['purpose'])}</td></tr>"
        for f in c["followthrough"]
    )
    lanes = "".join(
        f"<tr><td>{esc(l['lane'])}</td><td><code>{esc(l['slug'])}</code></td>"
        f"<td class='small'>{esc(', '.join(l['node_ids']))}</td>"
        f"<td>{'yes' if l['is_default'] else ''}</td></tr>"
        for l in c["lanes"]
    )
    gates = "".join(
        f"<tr><td><code>{esc(g['id'])}</code></td><td>{esc(g['name'])}</td>"
        f"<td>{esc(g['passes'])}</td><td class='small muted'>{esc(g['on_failure'])}</td></tr>"
        for g in c["entry_gates"]
    )
    terminal = "".join(
        f"<tr><td><code>{esc(s['state'])}</code></td><td>{esc(s['entered'])}</td>"
        f"<td>{esc(s['suppression'])}</td><td class='small muted'>{esc(s['next'])}</td></tr>"
        for s in c["terminal_states"]
    )
    build = "".join(
        f"<li><strong>{esc(s['title'])}</strong><br>"
        f"<span class='small muted'>{esc(s['detail'])}</span></li>"
        for s in c["build_order"]
    )

    body = f"""<h1>Cadence node map</h1>
<p class="lede">{esc(', '.join(c['config']['segments']))} &middot;
{esc(', '.join(c['config']['channels']))} &middot;
{c['config']['length_days']} business days</p>
{form}
{stats}
{warnings}
<h2>Entry gates</h2>
<p class="small muted">Run in order. A contact failing any gate never enters, and the reason is logged.</p>
<table><thead><tr><th>#</th><th>Gate</th><th>Passes when</th><th>On failure</th></tr></thead>
<tbody>{gates}</tbody></table>
<h2>Main sequence</h2>
<p class="small muted">Every lane runs these offsets. Only the message angle differs between lanes.</p>
<table><thead><tr><th>Node</th><th>Day</th><th>Channel</th><th>Purpose</th><th>Exit</th></tr></thead>
<tbody>{nodes}</tbody></table>
<h2>Lanes</h2>
<table><thead><tr><th>Lane</th><th>Slug</th><th>Node IDs</th><th>Default</th></tr></thead>
<tbody>{lanes}</tbody></table>
<h2>Interrupt &rarr; follow-through</h2>
<p class="small muted">Fires on an inbound reply, the required input being supplied, or a
meeting booked. Never on opens. Days count from the interrupt, not from cadence entry.</p>
<table><thead><tr><th>Node</th><th>Day</th><th>Channel</th><th>Purpose</th></tr></thead>
<tbody>{ft}</tbody></table>
<h2>Terminal states</h2>
<table><thead><tr><th>State</th><th>Entered when</th><th>Suppression</th><th>Next action</th></tr></thead>
<tbody>{terminal}</tbody></table>
<h2>Build order</h2>
<p class="small muted">Ordered by dependency, not by importance. Full checklist:
<a href="/docs/04-cadence/crm-build-checklist.md">CRM build checklist</a>.</p>
<ol>{build}</ol>"""
    return layout("Cadence builder", body, active="/tools/cadence")


# ======================================================================================
# JSON-driven tools: audit report and intake to spec
# ======================================================================================


def _json_tool_page(
    title: str,
    lede: str,
    active: str,
    sample_path: str,
    payload: str,
    rendered: str = "",
    problem: str = "",
) -> HTMLResponse:
    form = f"""
<form method="post">
  <div class="field">
    <label for="payload">Input JSON</label>
    <textarea id="payload" name="payload" spellcheck="false">{esc(payload)}</textarea>
    <div class="hint">Prefilled with <code>{esc(sample_path)}</code>. Replace it with your own.</div>
  </div>
  <button type="submit">Render</button>
</form>"""
    body = f"<h1>{esc(title)}</h1><p class='lede'>{lede}</p>{form}{problem}{rendered}"
    return layout(title, body, active=active)


@app.get("/tools/audit", response_class=HTMLResponse)
def audit_get() -> HTMLResponse:
    sample = read_repo_file("03-audit/sample-input.json") or "{}"
    return _json_tool_page(
        "Audit report",
        "Render a deliverability audit from a findings file. Missing sections render as "
        "<em>not assessed</em> rather than being silently dropped, and the remediation list is "
        "built automatically from the findings so the plan cannot drift out of step with them.",
        "/tools/audit",
        "03-audit/sample-input.json",
        sample,
    )


@app.post("/tools/audit", response_class=HTMLResponse)
def audit_post(payload: str = Form(...)) -> HTMLResponse:
    lede = "Render a deliverability audit from a findings file."
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return _json_tool_page(
            "Audit report", lede, "/tools/audit", "03-audit/sample-input.json", payload,
            problem=f"<div class='notice notice-bad'><strong>Not valid JSON.</strong><br>"
                    f"Line {exc.lineno}, column {exc.colno}: {esc(exc.msg)}</div>",
        )
    if not isinstance(data, dict):
        return _json_tool_page(
            "Audit report", lede, "/tools/audit", "03-audit/sample-input.json", payload,
            problem="<div class='notice notice-bad'>The input must be a JSON object.</div>",
        )

    try:
        mod = load_tool("audit_report")
        warnings = mod.check_input(data)
        report = mod.render_report(data)
    except ToolUnavailable as exc:
        return _json_tool_page("Audit report", lede, "/tools/audit",
                               "03-audit/sample-input.json", payload,
                               problem=f"<div class='notice notice-bad'>{esc(exc)}</div>")
    except Exception:
        return _json_tool_page("Audit report", lede, "/tools/audit",
                               "03-audit/sample-input.json", payload,
                               problem="<div class='notice notice-bad'><strong>The renderer "
                                       "failed on this input.</strong><pre>"
                                       + esc(traceback.format_exc()) + "</pre></div>")

    problem = ""
    if warnings:
        items = "".join(f"<li>{esc(w)}</li>" for w in warnings)
        problem = (f"<div class='notice notice-warn'><strong>{len(warnings)} issue(s) in the "
                   f"input</strong><ul>{items}</ul></div>")

    return _json_tool_page(
        "Audit report", lede, "/tools/audit", "03-audit/sample-input.json", payload,
        rendered=f"<hr>{md_to_html(report)}", problem=problem,
    )


@app.get("/tools/intake", response_class=HTMLResponse)
def intake_get() -> HTMLResponse:
    sample = read_repo_file("06-onboarding/sample-intake.json") or "{}"
    return _json_tool_page(
        "Intake to spec",
        "Turn a completed client intake into a build specification: the domain plan, the "
        "cadence node map, the CRM build order, and everything missing or ambiguous that "
        "blocks the build.",
        "/tools/intake",
        "06-onboarding/sample-intake.json",
        sample,
    )


@app.post("/tools/intake", response_class=HTMLResponse)
def intake_post(payload: str = Form(...)) -> HTMLResponse:
    lede = "Turn a completed client intake into a build specification."
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return _json_tool_page(
            "Intake to spec", lede, "/tools/intake", "06-onboarding/sample-intake.json", payload,
            problem=f"<div class='notice notice-bad'><strong>Not valid JSON.</strong><br>"
                    f"Line {exc.lineno}, column {exc.colno}: {esc(exc.msg)}</div>",
        )
    if not isinstance(data, dict):
        return _json_tool_page(
            "Intake to spec", lede, "/tools/intake", "06-onboarding/sample-intake.json", payload,
            problem="<div class='notice notice-bad'>The input must be a JSON object.</div>",
        )

    try:
        mod = load_tool("intake_to_spec")
        spec = mod.build_spec(data)
        markdown_out = mod.render(spec)
    except ToolUnavailable as exc:
        return _json_tool_page("Intake to spec", lede, "/tools/intake",
                               "06-onboarding/sample-intake.json", payload,
                               problem=f"<div class='notice notice-bad'>{esc(exc)}</div>")
    except Exception:
        return _json_tool_page("Intake to spec", lede, "/tools/intake",
                               "06-onboarding/sample-intake.json", payload,
                               problem="<div class='notice notice-bad'><strong>The builder "
                                       "failed on this input.</strong><pre>"
                                       + esc(traceback.format_exc()) + "</pre></div>")

    n_block, n_warn = len(spec["blockers"]), len(spec["warnings"])
    if n_block:
        banner = (f"<div class='notice notice-bad'><strong>{n_block} blocker(s).</strong> "
                  f"The build does not start until these are resolved.</div>")
    else:
        banner = ("<div class='notice notice-good'><strong>No blockers.</strong> Every required "
                  "input is present and no compliance gate is unsatisfied.</div>")
    if n_warn:
        banner += (f"<div class='notice notice-warn'><strong>{n_warn} warning(s).</strong> "
                   f"These do not stop the build, but they change it.</div>")

    return _json_tool_page(
        "Intake to spec", lede, "/tools/intake", "06-onboarding/sample-intake.json", payload,
        rendered=f"<hr>{md_to_html(markdown_out)}", problem=banner,
    )


# ======================================================================================
# Document browser
# ======================================================================================

DOC_GROUPS = [
    ("Root", ["README.md", "VARIABLES.md"]),
    ("01 · Sales", [
        "01-sales/sprint-scope-template.md",
        "01-sales/retainer-scope-template.md",
        "01-sales/pricing-model.md",
    ]),
    ("02 · Infrastructure", [
        "02-infrastructure/infrastructure-runbook.md",
        "02-infrastructure/warmup-checklist.md",
    ]),
    ("03 · Audit", ["03-audit/audit-template.md"]),
    ("04 · Cadence", [
        "04-cadence/cadence-spec.md",
        "04-cadence/crm-build-checklist.md",
    ]),
    ("05 · Copy", [
        "05-copy/brain-file-template.md",
        "05-copy/copy-rules.md",
        "05-copy/variant_prompt.md",
    ]),
    ("06 · Onboarding", ["06-onboarding/intake-form.md"]),
    ("07 · Data", ["07-data/enrichment-spec.md"]),
]

ALLOWED_DOCS = {p for _, paths in DOC_GROUPS for p in paths}


@app.get("/docs", response_class=HTMLResponse)
def docs_index() -> HTMLResponse:
    sections = []
    for group, paths in DOC_GROUPS:
        cards = "".join(
            f'<a class="card" href="/docs/{p}"><h3>{esc(Path(p).stem.replace("-", " ").title())}</h3>'
            f'<p><code>{esc(p)}</code></p></a>'
            for p in paths
        )
        sections.append(f"<h2>{esc(group)}</h2><div class='grid'>{cards}</div>")
    body = ("<h1>Documents</h1><p class='lede'>The fifteen fillable templates and "
            "specifications. Every client-specific value is a placeholder registered in "
            "<a href='/docs/VARIABLES.md'>VARIABLES.md</a>.</p>" + "".join(sections))
    return layout("Documents", body, active="/docs")


@app.get("/docs/{doc_path:path}", response_class=HTMLResponse)
def docs_show(doc_path: str) -> HTMLResponse:
    if doc_path not in ALLOWED_DOCS:
        return error_page(
            "Not found",
            f"There is no document at {doc_path!r}.",
        )
    text = read_repo_file(doc_path)
    if text is None:
        return error_page(
            "Not bundled",
            f"{doc_path} is in the repository but was not bundled with this function. "
            f"Check includeFiles in vercel.json.",
            status=503,
        )
    body = (f"<p class='small muted'><a href='/docs'>&larr; All documents</a> &middot; "
            f"<code>{esc(doc_path)}</code></p>" + md_to_html(text))
    return layout(Path(doc_path).stem, body, active=f"/docs/{doc_path}")


# ======================================================================================
# Health and JSON API
#
# The same planners, as JSON, for anything that wants to call them rather than read them.
# ======================================================================================


@app.get("/healthz")
def healthz() -> JSONResponse:
    status: dict[str, Any] = {"ok": True, "repo_root": str(REPO_ROOT), "tools": {}}
    for name in TOOL_PATHS:
        try:
            load_tool(name)
            status["tools"][name] = "ok"
        except Exception as exc:  # noqa: BLE001 - health check reports, never raises
            status["tools"][name] = f"unavailable: {exc}"
            status["ok"] = False
    missing = [p for p in ALLOWED_DOCS if read_repo_file(p) is None]
    status["missing_documents"] = missing
    if missing:
        status["ok"] = False
    return JSONResponse(status, status_code=200 if status["ok"] else 503)


@app.get("/api/domain-plan")
def api_domain_plan(
    primary_domain: str,
    monthly_volume: int,
    daily_ceiling: int = 40,
    mailboxes_per_domain: int = 3,
    sending_days: int = 22,
    headroom: float = 0.2,
) -> JSONResponse:
    try:
        mod = load_tool("domain_plan")
        return JSONResponse(
            mod.build_plan(
                primary_domain=primary_domain,
                monthly_volume=monthly_volume,
                daily_ceiling=daily_ceiling,
                mailboxes_per_domain=mailboxes_per_domain,
                sending_days=sending_days,
                headroom=headroom,
            )
        )
    except (ValueError, TypeError, ToolUnavailable) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/api/dns-records")
def api_dns_records(
    domain: str,
    esp: str = "generic",
    rua: str = "{{DMARC_RUA_ADDRESS}}",
    include_tracking: bool = True,
) -> JSONResponse:
    try:
        mod = load_tool("dns_records")
        return JSONResponse(
            mod.build_records(domain=domain, esp=esp, rua=rua, include_tracking=include_tracking)
        )
    except (ValueError, TypeError, ToolUnavailable) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/api/cadence")
def api_cadence(
    segments: str,
    channels: str = "email",
    length: int = 8,
    segment_field: str = "{{SEGMENT_FIELD}}",
) -> JSONResponse:
    try:
        mod = load_tool("cadence_builder")
        return JSONResponse(
            mod.build_cadence(
                segments=[s.strip() for s in segments.split(",") if s.strip()],
                channels=[c.strip() for c in channels.split(",") if c.strip()],
                length=length,
                segment_field=segment_field,
            )
        )
    except (ValueError, TypeError, ToolUnavailable) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots() -> str:
    # Internal tooling. Nothing here should be indexed.
    return "User-agent: *\nDisallow: /\n"


@app.get("/favicon.ico")
def favicon() -> Response:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="14" fill="#5b7cfa"/>'
        '<text x="32" y="45" font-family="system-ui,sans-serif" font-size="38" '
        'font-weight="700" fill="#fff" text-anchor="middle">A</text></svg>'
    )
    return Response(content=svg, media_type="image/svg+xml")


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> HTMLResponse:
    return error_page("Not found", f"Nothing at {request.url.path}")
