"""Self-contained HTML + JSON report, failure-first."""
from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment


def fmt_ts(ns: int) -> str:
    """Nanoseconds -> 'YYYY-MM-DD HH:MM:SS UTC'. 0 and missing timestamps render as '-'."""
    if not ns:
        return "-"
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# One self-contained HTML page. Jinja renders it with autoescape on, so log text cannot inject markup.
# The page is ordered failure-first: verdict, chains, tiles, catalog, shared errors, ranked patterns, pods.
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RootTrace · {{ r.environment }}</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--mut:#6b6b66;--line:#e4e3de;--crit:#c0392b;--high:#d9822b;--med:#b8a10d;--ok:#2e8b57;--new:#6c4bd8;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--card:#1f1f1d;--ink:#ecebe6;--mut:#9a9992;--line:#33332f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:22px;margin:0}h2{font-size:15px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin:34px 0 10px}
.sub{color:var(--mut);margin-top:4px}
.verdict{margin:18px 0;padding:14px 16px;border-radius:10px;background:var(--card);border-left:5px solid var(--ok);font-weight:600}
.verdict.bad{border-color:var(--crit)}.verdict.warn{border-color:var(--high)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.tile b{display:block;font-size:26px}.tile span{color:var(--mut);font-size:12px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;color:var(--mut);font-weight:600;background:var(--bg)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code,.mono{font-family:var(--mono);font-size:12.5px}
.tpl{font-family:var(--mono);font-size:12.5px;word-break:break-word}
.pill{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;font-weight:600;color:#fff;margin-right:4px}
.pill.FATAL,.pill.critical,.pill.down{background:var(--crit)}.pill.ERROR,.pill.high,.pill.degraded{background:var(--high)}
.pill.WARN,.pill.medium{background:var(--med)}.pill.low{background:var(--mut)}.pill.new,.pill.suspected,.pill.logs-missing{background:var(--new)}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:10px;padding:16px 18px;margin:0 0 14px}
.card.down{border-left-color:var(--crit)}.card.degraded{border-left-color:var(--high)}.card.suspected,.card.logs-missing{border-left-color:var(--new)}
.card h3{margin:0;font-size:18px}.numstep{color:var(--mut);font-weight:600;margin-right:6px}
.why{margin:8px 0 0}.k{font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--mut);margin-top:12px}
.hit{display:block;background:rgba(217,130,43,.18)}
.jumps{margin:8px 0 0}.jumps a{margin-right:12px}
section.more{margin-top:28px}section.more>summary{cursor:pointer;font-size:15px;font-weight:600}
details summary{cursor:pointer;color:var(--mut);font-size:12px;margin-top:6px}
pre{white-space:pre-wrap;word-break:break-word;background:var(--bg);padding:10px;border-radius:6px;max-height:320px;overflow:auto;font-size:12px}
pre.trace{font-family:var(--mono);font-size:12.5px;line-height:1.55;margin:10px 0;border:1px solid var(--line)}
.fix{margin-top:6px;padding:8px 10px;border-radius:6px;background:var(--bg);font-size:13px}
.muted{color:var(--mut)}input#q{width:100%;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);margin-bottom:10px}
.chain{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:14px}
.chain h3{margin:0 0 6px;font-size:16px}
.chain ul.ev{margin:6px 0 0 18px;padding:0}.chain ul.ev li{margin:2px 0}
.tree,.tree ul{list-style:none;margin:0;padding-left:18px;border-left:2px solid var(--line)}
.tree li{margin:6px 0;padding-left:8px}.tree .sym{color:var(--mut);font-size:12.5px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px}@media(max-width:800px){.cols{grid-template-columns:1fr}}
.box{background:var(--bg);border-radius:8px;padding:10px 12px}.box b{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.box code{display:block;margin:4px 0;white-space:pre-wrap}.warnnote{color:var(--high);font-size:12px}
.empty{padding:14px;color:var(--mut);background:var(--card);border:1px dashed var(--line);border-radius:10px}
</style></head><body><div class="wrap">
<h1>RootTrace — {{ r.environment }}</h1>
<div class="sub">{{ r.window_from }} → {{ r.window_to }} · compared with {{ r.baseline_offset }} earlier · {{ r.namespaces or "all namespaces" }}{% if r.traces_from %} · from saved traces{% endif %}</div>

<div class="verdict {{ r.verdict_class }}">{{ r.verdict }}</div>
{% if r.chains %}<div class="jumps">{% for ch in r.chains %}<a href="#r{{ loop.index }}">{{ loop.index }}. {{ ch.root }}</a>{% endfor %}</div>{% endif %}
{% if r.coverage %}<div class="warnnote">Part of this window is missing.{% for g in r.coverage %} {{ g.which }} {{ g.from }} – {{ g.to }}: {{ g.reason }}.{% endfor %}</div>{% endif %}

{% macro stack(frames) %}<pre class="trace">{% for f in frames %}{% if not loop.first %}Caused by: {% endif %}{{ f.level }} {{ f.service }}: {{ f.message }}{% if f.count %} ×{{ f.count }}{% endif %}{% if f.gap %} · {{ f.gap }}{% endif %}
{% if f.at %}    at {{ f.at }}
{% endif %}{% endfor %}</pre>{% endmacro %}

{% macro branch(t) %}<li><span class="pill {{ t.status }}">{{ t.status }}</span> <b>{{ t.component }}</b>
 <span class="muted">{% if t.via == "logs" %}named in a log{% else %}on the dependency map{% endif %}</span>
 {% if t.before_root %}<div class="warnnote">This one started earlier, so it may be a separate problem.</div>{% endif %}
 {% if t.symptoms %}<div class="sym">{{ t.symptoms[0][:180] }}</div>{% endif %}
 {% if t.children %}<ul>{% for c in t.children %}{{ branch(c) }}{% endfor %}</ul>{% endif %}</li>{% endmacro %}

{% if r.chains %}<h2>Start here</h2>
{% for ch in r.chains %}<article class="card {{ ch.status }}" id="r{{ loop.index }}">
<h3><span class="numstep">{{ loop.index }}</span><span class="pill {{ ch.status }}">{{ ch.status_label or ch.status }}</span> {{ ch.root }}</h3>
<div class="muted">{{ ch.kind }}{% if ch.namespaces %} · {{ ch.namespaces|join(", ") }}{% endif %}{% if ch.first != "-" %} · first seen {{ ch.first }}{% endif %}{% if ch.stack and ch.stack|length > 1 %} · {{ ch.via }}{% endif %}</div>
{% if ch.stack %}{{ stack(ch.stack) }}{% elif ch.why %}<p class="why">{{ ch.why }}</p>{% endif %}
{% if ch.direct %}<div class="k">Affected</div><div>{{ ch.direct|join(", ") }}{% if ch.impacted_count and ch.impacted_count > ch.direct|length %} · {{ ch.impacted_count }} in the trail{% endif %}</div>{% endif %}
{% if ch.code %}
<div class="k">In the code</div>
<div class="mono">{% if ch.code.file %}{{ ch.code.file }}{% if ch.code.line %}:{{ ch.code.line }}{% endif %}{% else %}{{ ch.code.class }}{% if ch.code.line %}:{{ ch.code.line }}{% endif %}{% endif %}</div>
<div class="muted">{{ ch.code.class }}{% if ch.code.method %}.{{ ch.code.method }}{% endif %}{% if ch.code.repo %} · <a href="{{ ch.code.repo }}">{{ ch.code.repo }}</a>{% endif %}{% if ch.code.commit %} · {{ ch.code.commit[:12] }}{% endif %}</div>
{% if ch.code.snippet %}<pre>{% for ln in ch.code.snippet.lines %}<span class="{% if ln.hit %}hit{% endif %}">{{ ln.n }}  {{ ln.text }}</span>
{% endfor %}</pre>{% elif ch.code.snippet_note %}<div class="muted">{{ ch.code.snippet_note }}</div>{% endif %}
{% elif ch.kind == "infra" %}<div class="k">In the code</div><div>No application line. This is infrastructure.</div>
{% elif ch.code_note %}<div class="k">In the code</div><div>{{ ch.code_note }}</div>{% endif %}
{% if ch.revision %}<div class="muted">Running {{ ch.revision.commit_abbrev or ch.revision.commit }}{% if ch.revision.version %} · {{ ch.revision.version }}{% endif %}{% if ch.image %} · {{ ch.image }}{% endif %}</div>{% elif ch.image %}<div class="muted">{{ ch.image }}</div>{% endif %}
{% if ch.request_path %}<div class="k">Request path</div><div>{{ ch.request_path|join(" → ") }}</div>{% endif %}
{% if ch.known %}
<div class="k">What to try</div>
<div class="fix">{% if ch.known[0].certainty == "confirmed" %}Matches the logged method. {% elif ch.known[0].certainty == "lead" %}Possible cause, from the message only. {% endif %}{{ ch.known[0].fix }}</div>
{% endif %}
<details><summary>How this was traced{% if ch.checks %}, and the kubectl commands{% endif %}</summary>
{% if ch.evidence|length > 1 %}<ul class="ev">{% for e in ch.evidence[1:] %}<li>{{ e }}</li>{% endfor %}</ul>{% endif %}
{% if ch.impacted %}<ul class="tree">{% for t in ch.impacted %}{{ branch(t) }}{% endfor %}</ul>{% endif %}
{% if ch.at_risk %}<div class="muted">Still healthy, but they call {{ ch.root }}: {{ ch.at_risk|join(", ") }}</div>{% endif %}
{% if ch.known|length > 1 %}{% for k in ch.known[1:] %}<div class="fix">{{ k.title }}: {{ k.fix }}</div>{% endfor %}{% endif %}
{% for c in ch.checks %}<code>{{ c }}</code>{% endfor %}
{% if ch.previous_logs %}<pre>{{ ch.previous_logs }}</pre>{% endif %}
</details>
</article>{% endfor %}{% endif %}

<div class="tiles">
 <div class="tile"><b>{{ r.stats.issues }}</b><span>log patterns</span></div>
 <div class="tile"><b>{{ r.stats.new }}</b><span>new since yesterday</span></div>
 <div class="tile"><b>{{ r.stats.events }}</b><span>matching lines</span></div>
 <div class="tile"><b>{{ r.stats.services }}</b><span>services</span></div>
 <div class="tile"><b>{{ r.stats.k8s }}</b><span>pod problems</span></div>
 <div class="tile"><b>{{ r.silent|length }}</b><span>gone silent</span></div>
</div>

<h2>Every log pattern</h2>
<p class="muted">The lines behind the cards above, most serious first. The number on the right is how many times it fired, and underneath is the same window yesterday.</p>
<input id="q" placeholder="Filter by service, exception, error code, text…" oninput="f(this.value)">
{% if r.issues %}<table id="issues"><tr><th>Service</th><th>What was logged</th><th class="num">Count<br><span class="muted">yesterday</span></th></tr>
{% for i in r.issues %}<tr>
<td><b>{{ i.service }}</b><div class="muted mono">{{ i.namespace }}</div></td>
<td><span class="pill {{ i.level }}">{{ i.level }}</span>{% if i.since_deploy is true %}<span class="pill new">since deploy</span>{% elif i.new_streak %}<span class="pill new">new all week</span>{% elif i.is_new %}<span class="pill new">new</span>{% elif i.since_deploy is false %}<span class="pill medium">before deploy</span>{% endif %}
{% if i.via %}<div class="muted">{{ i.via }}</div>{% endif %}
{% if i.stack %}{{ stack(i.stack) }}{% else %}<div class="tpl">{{ i.template }}</div>{% endif %}
{% if i.code and i.code.file %}<div class="mono">{{ i.code.file }}{% if i.code.line %}:{{ i.code.line }}{% endif %}</div>{% elif i.code_note %}<div class="muted">{{ i.code_note }}</div>{% endif %}
<details><summary>sample and detail · {{ i.first }}</summary>
{% if i.code %}<div class="mono">{{ i.code.class }}{% if i.code.method %}.{{ i.code.method }}{% endif %}{% if i.code.repo %} · <a href="{{ i.code.repo }}">repository</a>{% endif %}</div>{% endif %}
{% if i.code and i.code.snippet %}<pre>{% for ln in i.code.snippet.lines %}<span class="{% if ln.hit %}hit{% endif %}">{{ ln.n }}  {{ ln.text }}</span>
{% endfor %}</pre>{% elif i.code and i.code.snippet_note %}<div class="muted">{{ i.code.snippet_note }}</div>{% endif %}
{% if i.path %}<div class="muted">Same id in {{ i.path|join(" → ") }}</div>{% endif %}
{% if i.root_causes %}<div class="muted">Exception: {{ i.root_causes|join(", ") }}</div>{% endif %}
{% if i.error_codes %}<div class="muted">Codes: {{ i.error_codes|join(", ") }}</div>{% endif %}
{% for k in i.known %}<div class="fix"><b>{{ k.title }}</b> {% if k.certainty == "confirmed" %}matches the logged method{% elif k.certainty == "lead" %}possible cause{% endif %}: {{ k.fix }}</div>{% endfor %}
{% if i.grafana %}<div><a href="{{ i.grafana }}">open in Grafana</a></div>{% endif %}
{% if i.traces %}<div class="mono">{% for t in i.traces %}<a href="{{ t.url }}">{{ t.id }}</a> {% endfor %}</div>{% endif %}
{% for s in i.samples %}<pre>{{ s.pod }}  {{ s.ts }}
{{ s.text }}</pre>{% endfor %}</details></td>
<td class="num">{{ i.count }}<br><span class="muted">{{ i.baseline_count }}</span></td></tr>{% endfor %}</table>
{% else %}<div class="empty">No error patterns in this window. 🎉</div>{% endif %}

{% if r.known_summary %}<section class="more"><details><summary>Catalog notes — message matches, not a second list of roots</summary>
<table><tr><th>Note</th><th>Where</th><th>What it suggests</th></tr>
{% for k in r.known_summary %}<tr><td><span class="pill {{ k.severity }}">{{ k.severity }}</span><b>{{ k.title }}</b><div class="muted mono">{{ k.id }}{% if k.owner %} · {{ k.owner }}{% endif %}</div></td>
<td class="mono">{{ k.where|join(", ") }}</td><td>{{ k.cause }}<div class="fix">{{ k.fix }}</div></td></tr>{% endfor %}</table>
</details></section>{% endif %}

{% if r.cross %}<section class="more"><details><summary>The same message in more than one service</summary>
<table><tr><th>Message</th><th>Services</th><th class="num">Lines</th></tr>
{% for g in r.cross %}<tr><td>{% if g.new %}<span class="pill new">new</span>{% endif %}<div class="tpl">{{ g.template }}</div></td>
<td class="mono">{{ g.services|join(", ") }}</td><td class="num">{{ g.count }}</td></tr>{% endfor %}</table>
</details></section>{% endif %}

<h2>Pods</h2>
{% if r.k8s_error %}<div class="empty">Kubernetes data not collected: {{ r.k8s_error }}</div>
{% elif r.k8s %}<table><tr><th>Kind</th><th>Pod / object</th><th>Reason</th><th>Detail</th><th class="num">Restarts / count</th></tr>
{% for f in r.k8s %}<tr><td>{{ f.kind }}</td><td class="mono">{{ f.namespace }}/{{ f.pod }}<div class="muted">{{ f.container }}</div></td>
<td>{% for k in f.known or [] %}<span class="pill critical">{{ k.id }}</span>{% endfor %}<b>{{ f.reason }}</b></td>
<td>{{ f.message }}{% for k in f.known or [] %}<div class="fix">→ {{ k.fix }}</div>{% endfor %}</td><td class="num">{{ f.restarts }}</td></tr>{% endfor %}</table>
{% else %}<div class="empty">No pod restarts, bad states or warning events in the window.</div>{% endif %}

{% if r.rollouts %}<h2>Rollouts in window</h2><table><tr><th>When</th><th>Workload</th><th>Images</th></tr>
{% for d in r.rollouts %}<tr><td class="mono">{{ d.ts }}</td><td class="mono">{{ d.namespace }}/{{ d.name }}</td><td class="mono">{{ d.images }}</td></tr>{% endfor %}</table>{% endif %}

{% if r.silent %}<h2>Services gone silent</h2><div class="muted" style="margin-bottom:8px">Logged in the baseline window but no log lines at all now — possibly down or scaled to zero.</div>
<table><tr><th>Service</th><th class="num">Baseline lines</th></tr>{% for s in r.silent %}<tr><td class="mono">{{ s.namespace }}/{{ s.service }}</td><td class="num">{{ s.baseline }}</td></tr>{% endfor %}</table>{% endif %}

{% if r.resolved %}<h2>Gone since baseline</h2><table><tr><th>Service</th><th>Pattern</th><th class="num">Baseline</th></tr>
{% for i in r.resolved %}<tr><td class="mono">{{ i.service }}</td><td class="tpl">{{ i.template }}</td><td class="num">{{ i.baseline_count }}</td></tr>{% endfor %}</table>{% endif %}

<p class="muted" style="margin-top:40px">Tokens, e-mails and long numbers are masked. A card is a place to start. The tables under it are the lines and pods that led there.</p>
</div>
<script>function f(q){q=q.toLowerCase();document.querySelectorAll('#issues tr').forEach((r,i)=>{if(i)r.style.display=r.innerText.toLowerCase().includes(q)?'':'none'})}</script>
</body></html>"""


_LABEL = {
    "down": "Down",
    "degraded": "Errors",
    "suspected": "Suspected",
    "logs-missing": "No logs",
}


def _one_line(text: str, limit: int = 220) -> str:
    """One readable sentence from a log or evidence line."""
    return " ".join((text or "").split())[:limit]


def _why(text: str) -> str:
    """Drop the miner prefix so the card shows the log message, not 'ERROR ×25 in service:'."""
    line = _one_line(text, 400)
    if "×" in line and " in " in line and ": " in line:
        line = line.split(" in ", 1)[1].split(": ", 1)[-1]
    if " [cause " in line:
        line = line.split(" [cause ", 1)[0]
    return _one_line(line)


def _look(chains: list) -> str:
    """The roots a person should open first, in rank order, with a plain status."""
    if not chains:
        return ""
    shown = ", ".join(
        f"{c['root']} ({_LABEL.get(c['status'], c['status']).lower()})" for c in chains[:4])
    if len(chains) > 4:
        shown += f", and {len(chains) - 4} more"
    return shown


def _at(code: dict | None) -> str | None:
    """Class.method(File.java:line) copied from a parsed frame. No frame means no at-line."""
    if not code or not code.get("class"):
        return None
    file = code.get("file") or (code["class"].rsplit(".", 1)[-1] + ".java")
    loc = f"{file}:{code['line']}" if code.get("line") else file
    if code.get("method"):
        return f"{code['class']}.{code['method']}({loc})"
    return f"{code['class']}({loc})"


def _frame(iss: dict) -> dict:
    """One line of a correlated stack. The message is the log pattern, not a rewritten cause."""
    return {
        "service": iss.get("service") or iss.get("namespace") or "",
        "level": iss.get("level") or "",
        "message": _one_line(iss.get("template") or "", 180),
        "count": iss.get("count"),
        "at": _at(iss.get("code")),
        "first_ns": iss.get("first_ns") or 0,
    }


def _chain_names(chain: dict) -> set[str]:
    names = {chain.get("root") or ""}
    def walk(nodes):
        for t in nodes or []:
            if t.get("component"):
                names.add(t["component"])
            walk(t.get("children"))
    walk(chain.get("impacted"))
    return {n.lower() for n in names if n}


def _owns(iss: dict, root: str) -> bool:
    """True when this issue is the chain root. The dependency-map name wins over the pod name."""
    comp = (iss.get("component") or "").lower()
    if comp:
        return comp == root
    ns = (iss.get("namespace") or "").lower()
    svc = (iss.get("service") or "").lower()
    return ns == root or svc == root or svc.startswith(root + "-")


def _on_chain(chain: dict, iss: dict, names: set[str]) -> bool:
    comp = (iss.get("component") or "").lower()
    if comp:
        return comp in names
    ns = (iss.get("namespace") or "").lower()
    svc = (iss.get("service") or "").lower()
    if ns in names or svc in names:
        return True
    return any(svc == n or svc.startswith(n + "-") or svc.startswith(n + "/") for n in names)


def _root_issue(chain: dict, issues: list[dict], names: set[str]) -> dict | None:
    root = (chain.get("root") or "").lower()
    own = [i for i in issues if _on_chain(chain, i, names) and _owns(i, root)]
    if not own:
        return None
    return max(own, key=lambda i: i.get("score") or 0)


# A callee's error counts as this error's cause when it was logged up to 10s earlier,
# or up to 2s later (the caller often writes its line first).
_BEFORE_NS = 10 * 1_000_000_000
_AFTER_NS = 2 * 1_000_000_000


def _comp(iss: dict) -> str:
    return (iss.get("component") or iss.get("service") or "").lower()


def _moments(iss: dict) -> list[int]:
    """Times this pattern fired. Samples and the first line stand in when the scan kept no marks."""
    raw = [t for t in (iss.get("marks") or []) if t]
    if not raw:
        raw = [s.get("ts_ns") or 0 for s in (iss.get("samples") or [])]
        raw = [t for t in raw if t]
    if not raw and iss.get("first_ns"):
        raw = [iss["first_ns"]]
    return sorted(raw)


def _closest(cause: list[int], symptom: list[int]) -> tuple[int, int] | None:
    """(gap, cause time) for the closest pair inside the window. None when they never line up.

    The cause time is the one that matched, so the next hop is measured from that moment
    and not from some other firing of the same pattern.
    """
    if not cause or not symptom:
        return None
    best = None
    for st in symptom:
        lo = bisect_left(cause, st - _BEFORE_NS)
        hi = bisect_right(cause, st + _AFTER_NS)
        for ct in cause[lo:hi]:
            delta = st - ct
            if best is None or abs(delta) < abs(best[0]):
                best = (delta, ct)
    return best


def _gap(delta: int) -> str:
    if abs(delta) < 50_000_000:
        return "same time"
    ms = abs(delta) / 1_000_000
    text = f"{ms:.0f}ms" if ms < 1000 else f"{abs(delta) / 1_000_000_000:.1f}s"
    return f"{text} earlier" if delta >= 0 else f"{text} later"


def _time_frames(iss: dict, by_comp: dict[str, list[dict]], calls: dict[str, set[str]],
                 moments: dict[int, list[int]]) -> list[dict]:
    """Errors on services this one calls, then the services those call, when the times line up.

    Each hop has to fall inside the window of the frame above it. A service that only failed
    at the same second, with no call between them, is left out.
    """
    frames: list[dict] = []
    seen_ids = {id(iss)}
    seen_comp = {_comp(iss)}
    layer = [(iss, moments[id(iss)])]
    while layer and len(frames) < 4:
        found = []
        for cur, anchors in layer:
            for dep in calls.get(_comp(cur), ()):
                if dep in seen_comp:
                    continue
                for other in by_comp.get(dep, []):
                    if id(other) in seen_ids:
                        continue
                    pair = _closest(moments[id(other)], anchors)
                    if pair is None:
                        continue
                    delta, cause_ts = pair
                    found.append((abs(delta), delta, cause_ts, other, dep))
        found.sort(key=lambda row: row[0])
        nxt = []
        taken: set[str] = set()
        for _, delta, cause_ts, other, dep in found:
            if dep in seen_comp or dep in taken or id(other) in seen_ids:
                continue
            taken.add(dep)
            seen_comp.add(dep)
            seen_ids.add(id(other))
            frame = _frame(other)
            frame["gap"] = _gap(delta)
            frames.append(frame)
            nxt.append((other, [cause_ts]))
            if len(frames) >= 4:
                break
        layer = nxt
    return frames


def attach_stacks(issues: list[dict], chains: list[dict], calls: dict[str, set[str]] | None = None) -> None:
    """Give every error a stack. The top frame is that error. Under it, in order:

    an earlier error that shares its transaction id; otherwise an error on a service it calls
    that was logged within a few seconds; otherwise the root of its failure chain.
    """
    by_tid: dict[str, list[dict]] = {}
    for iss in issues:
        for tid in iss.get("trace_ids") or []:
            by_tid.setdefault(tid, []).append(iss)

    peers: dict[int, list[dict]] = {}
    for iss in issues:
        mine = set(iss.get("trace_ids") or [])
        if not mine:
            continue
        found = []
        seen = set()
        for tid in mine:
            for other in by_tid.get(tid, []):
                if other is iss or id(other) in seen:
                    continue
                if mine.intersection(other.get("trace_ids") or []):
                    seen.add(id(other))
                    found.append(other)
        if found:
            peers[id(iss)] = found

    named = [(ch, _chain_names(ch)) for ch in chains]

    def root_frame(iss: dict) -> dict | None:
        for ch, names in named:
            if not _on_chain(ch, iss, names):
                continue
            root = (ch.get("root") or "").lower()
            if _owns(iss, root):
                return None                            # this error is the root, nothing under it
            top = _root_issue(ch, issues, names)
            if top is not None and top is not iss:
                return _frame(top)
            if ch.get("why"):
                return {"service": ch["root"], "level": ch.get("status_label") or ch.get("status") or "",
                        "message": ch["why"], "count": None, "at": _at(ch.get("code")), "first_ns": 0}
        return None

    by_comp: dict[str, list[dict]] = {}
    moments: dict[int, list[int]] = {}
    for iss in issues:
        by_comp.setdefault(_comp(iss), []).append(iss)
        moments[id(iss)] = _moments(iss)

    for iss in issues:
        frames = [_frame(iss)]
        def earlier(other: dict) -> bool:
            ot, it = other.get("first_ns") or 0, iss.get("first_ns") or 0
            if ot != it:
                return ot < it
            return (other.get("service") or "") < (iss.get("service") or "")
        others = [p for p in peers.get(id(iss), []) if p is not iss and earlier(p)]
        for p in sorted(others, key=lambda p: p.get("first_ns") or 0, reverse=True)[:5]:
            frames.append(_frame(p))
        if others:
            via = "same transaction"
        else:
            timed = _time_frames(iss, by_comp, calls or {}, moments)
            frames.extend(timed)
            have = {f.get("service") for f in frames}
            deeper = root_frame(iss)
            if deeper and deeper.get("service") not in have:
                frames.append(deeper)
            if timed:
                via = timed[0].get("gap") or "same moment"
            elif len(frames) > 1:
                via = "same failure"
            else:
                via = ""
        iss["stack"] = frames
        iss["via"] = via

    for ch, names in named:
        root = (ch.get("root") or "").lower()
        members = [i for i in issues if _on_chain(ch, i, names)]
        by_svc: dict[str, dict] = {}
        for iss in members:
            prev = by_svc.get(iss.get("service") or "")
            if prev is None or (iss.get("score") or 0) > (prev.get("score") or 0):
                by_svc[iss.get("service") or ""] = iss
        own = [i for i in by_svc.values() if _owns(i, root)]
        kids = [i for i in by_svc.values() if i not in own]
        kids.sort(key=lambda i: -(i.get("score") or 0))
        frames = [_frame(i) for i in kids[:6]]
        if own:
            frames.append(_frame(max(own, key=lambda i: i.get("score") or 0)))
        elif ch.get("why"):
            frames.append({"service": ch["root"], "level": ch.get("status_label") or "",
                           "message": ch["why"], "count": None, "at": _at(ch.get("code")), "first_ns": 0})
        shared = set()
        same_txn = False
        for iss in members:
            for tid in iss.get("trace_ids") or []:
                if tid in shared:
                    same_txn = True
                shared.add(tid)
        ch["stack"] = frames
        ch["via"] = "same transaction" if same_txn and len(frames) > 1 else ("same failure" if len(frames) > 1 else "")


def _grafana(base: str, namespace: str, label: str, service: str, text: str) -> str:
    """Grafana Explore URL for one pattern. The snippet is a literal line filter, not the Drain template."""
    snippet = (text or "")[:90].replace("`", "'").replace("\\", "")
    expr = '{namespace="%s", %s="%s"} |= `%s`' % (namespace, label or "app", service, snippet)
    panes = {"q": {"datasource": "loki", "queries": [{"refId": "A", "expr": expr}]}}
    return base.rstrip("/") + "/explore?schemaVersion=1&orgId=1&panes=" + quote(json.dumps(panes))


def _trace_url(public: str | None, tid: str) -> str:
    path = "/trace/" + quote(tid) + "?since=6h"
    return (public.rstrip("/") + path) if public else path


def build(result: dict) -> dict:
    """Shape the scan result into a template-friendly dict. The same dict is written as JSON.

    Mutates issue rows in place: timestamps become strings, counters become lists. Callers that
    still need the raw counters must read them before build().
    """
    issues = result["issues"]
    # Collapse catalog hits that fired in several services into one row, remembering where.
    known: dict[str, dict] = {}
    for i in issues:
        for k in i["known"]:
            e = known.setdefault(k["id"], {**k, "where": set()})
            e["where"].add(i["service"])
    for f in result["k8s"]:
        for k in f.get("known", []):
            # A pod-level catalog hit (CrashLoop, failing probe) is always shown as critical.
            e = known.setdefault(k["id"], {**k, "severity": "critical", "where": set()})
            e["where"].add(f["pod"])
    sev = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    known_summary = sorted(({**v, "where": sorted(v["where"])[:8]} for v in known.values()),
                           key=lambda k: sev.get(k.get("severity"), 9))
    crit = sum(1 for k in known_summary if k.get("severity") == "critical")
    new = sum(1 for i in issues if i["is_new"])
    # Distinct pods, so one CrashLooping container plus its restart event counts as one pod.
    bad_pods = len({f["pod"] for f in result["k8s"] if f["kind"] in ("pod-state", "restart")})
    chains = result.get("deps", {}).get("chains", [])
    # Unhealthy beats degraded. Critical catalog hits, failing pods, or a silent service are enough.
    look = _look(chains)
    if crit or bad_pods or result["silent"]:
        verdict = f"Unhealthy. Start with {look}." if look else "Unhealthy. Pods are failing or a service went silent."
        vcls = "bad"
    elif new or issues:
        verdict = f"Degraded. Start with {look}." if look else f"Degraded. {len(issues)} error patterns, {new} of them new."
        vcls = "warn"
    elif result.get("coverage"):
        # An empty window that Loki did not finish is not a clean result.
        verdict = "Incomplete. Part of this window was not read, so a clean result is not known."
        vcls = "bad"
    else:
        verdict, vcls = "Healthy. No errors in this window.", ""
    # The same Drain template in two services is one shared upstream, not two incidents.
    groups: dict[str, dict] = {}
    for i in issues:
        g = groups.setdefault(i["template"].strip().lower(), {"template": i["template"], "services": [],
                                                              "count": 0, "new": False, "known": []})
        g["services"].append(i["service"]); g["count"] += i["count"]; g["new"] |= i["is_new"]
        g["known"] += [k["id"] for k in i["known"] if k["id"] not in g["known"]]
    cross = sorted((g for g in groups.values() if len(set(g["services"])) >= 2), key=lambda g: -len(g["services"]))
    label = result.get("service_label") or "app"
    for i in issues:
        i["first"], i["last"] = fmt_ts(i["first_ns"]), fmt_ts(i["last_ns"])
        for s in i["samples"]:
            s["ts"] = fmt_ts(s["ts_ns"])
        sample = (i["samples"][0]["text"].split("\n", 1)[0] if i["samples"] else i["template"])
        if result.get("grafana_url"):
            i["grafana"] = _grafana(result["grafana_url"], i["namespace"], label, i["service"], sample)
        i["traces"] = [{"id": t, "url": _trace_url(result.get("public_url"), t)} for t in i.get("trace_ids") or []]
        # Counters arrived as dicts from Issue.to_dict(); the template joins the keys.
        i["exceptions"] = list(i["exceptions"])
        i["root_causes"] = list(i["root_causes"])
        i["error_codes"] = list(i["error_codes"])
    for g in result.get("coverage") or []:
        g["from"], g["to"] = fmt_ts(g["from_ns"]), fmt_ts(g["to_ns"])
    for ch in chains:
        ch["first"] = fmt_ts(ch["first_ns"])
        ch["status_label"] = _LABEL.get(ch["status"], ch["status"])
        ch["why"] = _why((ch.get("evidence") or [""])[0])
        ch["direct"] = [t.get("component") for t in ch.get("impacted") or []]
    calls: dict[str, set[str]] = {}
    for edge in result.get("deps", {}).get("graph") or []:
        src, dst = (edge.get("from") or "").lower(), (edge.get("to") or "").lower()
        if src and dst:
            calls.setdefault(src, set()).add(dst)
    attach_stacks(issues, chains, calls)
    for i in issues:
        i.pop("marks", None)
    for d in result["rollouts"]:
        d["ts"] = fmt_ts(d["ts_ns"])
    return {
        **result,
        "verdict": verdict, "verdict_class": vcls, "known_summary": known_summary, "cross": cross,
        "chains": chains,
        "stats": {"issues": len(issues), "new": new, "events": sum(i["count"] for i in issues),
                  "services": len({(i["namespace"], i["service"]) for i in issues}),
                  "k8s": len(result["k8s"])},
        "unhealthy": vcls == "bad",            # what the HTTP API's only_if=unhealthy checks
    }


def _annotate_streaks(r: dict, out: Path) -> None:
    """A pattern that was already new on three earlier days is 'new all week', not a fresh surprise."""
    hist = out / "history"
    if not hist.is_dir():
        return
    days: dict[str, set[str]] = {}
    for path in hist.glob("roottrace-report-*.json"):
        day = path.name[len("roottrace-report-"):len("roottrace-report-") + 8]
        if len(day) != 8 or not day.isdigit():
            continue
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        if day >= today:
            continue
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for iss in prior.get("issues") or []:
            if iss.get("is_new") and iss.get("key"):
                days.setdefault(iss["key"], set()).add(day)
    for iss in r.get("issues") or []:
        if iss.get("is_new") and len(days.get(iss.get("key") or "", ())) >= 3:
            iss["new_streak"] = len(days[iss["key"]])


def write(r: dict, out_dir: str) -> tuple[Path, Path]:
    """Write the latest report and a timestamped copy under history/. Returns the latest paths.

    JSON uses default=list so the sets collected while building the known-issue summary survive dumps.
    history/ keeps report_history copies (default 48) and deletes older ones.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    _annotate_streaks(r, out)
    html = Environment(autoescape=True).from_string(TEMPLATE).render(r=r)
    body = json.dumps(r, indent=2, default=list)
    hp, jp = out / "roottrace-report.html", out / "roottrace-report.json"
    hp.write_text(html, encoding="utf-8")
    jp.write_text(body, encoding="utf-8")
    hist = out / "history"
    hist.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (hist / f"roottrace-report-{stamp}.html").write_text(html, encoding="utf-8")
    (hist / f"roottrace-report-{stamp}.json").write_text(body, encoding="utf-8")
    keep = int(r.get("report_history") or 48)
    old = sorted(hist.glob("roottrace-report-*.html"))[:-keep]
    for p in old:
        p.unlink(missing_ok=True)
        p.with_suffix(".json").unlink(missing_ok=True)
    return hp, jp
