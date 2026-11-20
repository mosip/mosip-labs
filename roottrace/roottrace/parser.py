"""Normalise raw Loki lines into structured events; mask PII / payloads; stitch stack traces."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .loki import LogEntry

# Level word anywhere near the start of a line. Spring uses ERROR, log4j also uses SEVERE.
LEVEL_RE = re.compile(r"\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|SEVERE)\b")
# Fully-qualified Java type ending in Exception, Error, or Fault. The package dots keep "Error connecting" out.
EXC_RE = re.compile(r"\b((?:[a-zA-Z_$][\w$]*\.)+[A-Z][\w$]*(?:Exception|Error|Fault))\b")
CAUSED_RE = re.compile(r"Caused by:\s*([\w$.]+)(?::\s*(.*))?")
# MOSIP-style error codes, e.g. IDA-MLC-019, KER-ATH-401, RES-SER-410, PRG_PAM_APP_005
ERRCODE_RE = re.compile(r"\b([A-Z]{2,6}[-_][A-Z]{2,5}[-_](?:[A-Z]{2,5}[-_])?\d{3,4})\b")
# transactionId=TXN1003, trace-id: abc, X-B3-TraceId=... — the id itself is 6 to 64 url-safe chars.
TRACE_RE = re.compile(r"(?i)\b(?:trace[-_]?id|transaction[-_]?id|txn[-_]?id|requestid|X-B3-TraceId)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9-]{6,64})")
# A continuation of the previous line: a stack frame, "Caused by", "... 12 more", or a suppressed exception.
CONT_RE = re.compile(r"^(\s+at\s|\s*\.\.\. \d+ (more|common frames)|Caused by:|\s+Suppressed:|\t)")
# MOSIP logback pattern: 2026-11-19 08:55:42,518 [thread] ERROR [io.mosip.Foo].execute.259 : msg
# method and line are optional; some appenders stop after the logger name.
MOSIP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ][\d:.,]+\s+\[(?P<thread>[^\]]*)\]\s+(?P<level>[A-Z]+)\s+"
    r"\[(?P<logger>[^\]]*)\](?:\.(?P<method>[\w$<>]+)\.(?P<line>\d+))?\s*:\s?(?P<msg>.*)$")
# "at io.mosip.foo.Bar.baz(Bar.java:210)" — group 1 is the class (trailing dot stripped later).
FRAME_RE = re.compile(r"at\s+((?:[\w$]+\.)+)([\w$<>]+)\(([^():]+\.java):(\d+)\)")
LEAD_TS_RE = re.compile(r"^\[?\d{4}-\d{2}-\d{2}[T ][\d:.,]+(?:Z|[+-]\d{2}:?\d{2})?\]?\s*")
# A line that is only "com.foo.BarException" or "com.foo.BarException: message", logged on its own.
EXC_HEADER_RE = re.compile(r"^(?:[a-zA-Z_$][\w$]*\.)+[A-Z][\w$]*(?:Exception|Error)(?::|\s*$)")
# Spring Boot default: "2026-11-19 10:00:00.000 ERROR 1 --- [thread] logger : message"
SPRING_RE = re.compile(
    r"^\S+\s+\S+\s+(?P<level>[A-Z]+)\s+\d*\s*---\s+\[(?P<thread>[^\]]*)\]\s+(?P<logger>\S+)\s*:\s*(?P<msg>.*)$")

# Applied in order. The long base64/JWT-body rule runs before the dedicated JWT rule so a blob
# does not leave a shorter token behind. IDs of 10-16 digits are masked, but not timestamps or IPs
# (those contain ':' or '.' or '-').
MASKS = [
    (re.compile(r"[A-Za-z0-9+/_-]{120,}={0,2}"), "<BLOB>"),                 # base64 biometrics, JWTs
    (re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+"), "<JWT>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<EMAIL>"),
    (re.compile(r"(?<![\d.:-])\d{10,16}(?![\d.:-])"), "<ID>"),                # UIN / VID / phone
]


def mask(text: str) -> str:
    """Replace biometrics, tokens, emails and long numeric ids before anything is stored or shown."""
    for rx, repl in MASKS:
        text = rx.sub(repl, text)
    return text


@dataclass
class Event:
    ts_ns: int
    namespace: str
    service: str
    pod: str
    level: str
    message: str           # masked first line / message
    exception: str | None = None
    root_cause: str | None = None       # deepest "Caused by" type, if the stack names one
    error_codes: list[str] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)
    log_logger: str | None = None       # logger class from the MOSIP/Spring header, when present
    log_method: str | None = None
    log_line: int | None = None
    raw: str = ""          # masked full text incl. stack, truncated


# Mesh sidecars share the pod's app label. Keep them out of the service's own name.
SIDECARS = {"istio-proxy", "istio-init", "vault-agent", "linkerd-proxy"}


def _service(labels: dict, service_label: str) -> str:
    """Pick a stable service name from Loki labels.

    Prefer the configured label, then common fallbacks. If none exist, strip the ReplicaSet
    hash and the pod ordinal off the pod name (my-app-5bf8cbf9df-rbdqh -> my-app).
    A sidecar container is reported as "app/istio-proxy" so its errors are not blamed on the app.
    """
    container = (labels.get("container") or "").split("/")[-1]
    name = ""
    for k in (service_label, "app", "app_kubernetes_io_name", "container", "job"):
        if labels.get(k):
            name = labels[k].split("/")[-1]        # some pipelines prefix the label with a path
            break
    if not name:
        pod = labels.get("pod", "unknown")
        name = re.sub(r"-[a-z0-9]{8,10}-[a-z0-9]{5}$|-\d+$", "", pod)
    if container in SIDECARS and name != container:
        return f"{name}/{container}"
    return name


def _from_json(line: str):
    """Structured JSON logs (some services log one object per line). Returns None for plain text."""
    if not line.startswith("{"):
        return None
    try:
        d = json.loads(line)
    except ValueError:
        return None                        # a line that merely starts with '{' is still plain text
    msg = d.get("message") or d.get("msg") or ""
    stack = d.get("stack_trace") or d.get("exception") or d.get("stacktrace") or ""
    level = str(d.get("level") or d.get("severity") or d.get("log.level") or "").upper()
    trace = d.get("traceId") or d.get("trace_id") or d.get("transactionId")
    return level, f"{msg}\n{stack}".strip(), trace


def frames_in(text: str) -> list[dict]:
    """Every 'at class.method(File.java:line)' frame, in the order they appear."""
    return [{"class": m.group(1).rstrip("."), "method": m.group(2), "file": m.group(3), "line": int(m.group(4))}
            for m in FRAME_RE.finditer(text or "")]


def app_frame(text: str) -> dict | None:
    """Application throw site: the first io.mosip frame in the deepest Caused-by section.

    The deepest cause is the one that actually failed (SQLException, not the RestTemplate wrapper).
    Spring and Hikari frames are skipped so the link points at MOSIP source.
    """
    sections = re.split(r"(?m)^[ \t]*Caused by:", text or "")
    for section in reversed(sections):                  # deepest cause first
        app = [f for f in frames_in(section) if f["class"].startswith("io.mosip.")]
        if app:
            return app[0]                               # top io.mosip frame in that section
    return None


def code_location(ev: Event) -> dict | None:
    """Where in MOSIP source this event was thrown. Stack frame wins over the logger class.line header."""
    frame = app_frame(ev.raw)
    if frame:
        return frame
    # No stack, but the MOSIP logback pattern recorded logger.method.line.
    if ev.log_line and ev.log_logger and ev.log_logger.startswith("io.mosip."):
        return {"class": ev.log_logger, "method": ev.log_method, "file": None, "line": ev.log_line}
    return None


def parse(entries: list[LogEntry], service_label: str = "app") -> list[Event]:
    """Turn Loki lines into events. Stack frames that follow an error are stitched onto that event.

    Loki delivers one line per record, so a Java stack is many records. We keep the last event per
    stream (same labels) and append continuation lines to it instead of mining each frame as its own error.
    """
    events: list[Event] = []
    last_by_stream: dict[tuple, Event] = {}
    for e in entries:
        key = tuple(sorted(e.labels.items()))          # identity of this log stream
        line = e.line.rstrip("\n")
        prev = last_by_stream.get(key)
        # An exception header logged as its own line right after an ERROR/WARN line is the same event.
        # The 2s gap rejects a later, unrelated exception that happens to share the stream.
        if (prev is not None and EXC_HEADER_RE.match(line) and prev.level in ("ERROR", "WARN", "FATAL")
                and e.ts_ns - prev.ts_ns < 2_000_000_000 and not prev.exception):
            prev.raw += "\n" + mask(line)[:2000]
            prev.exception = EXC_HEADER_RE.match(line).group(0).rstrip(": ").strip()
            continue
        if prev is not None and CONT_RE.match(line):
            if len(prev.raw) < 6000:                    # stop appending once the stack is long enough to read
                prev.raw += "\n" + mask(line)
            m = CAUSED_RE.search(line)
            if m:
                prev.root_cause = m.group(1)            # overwritten by each deeper "Caused by"
            continue

        trace_from_json = None
        js = _from_json(line)
        sm = None
        if js:
            level, text, trace_from_json = js
        else:
            text = line
            sm = MOSIP_RE.match(line) or SPRING_RE.match(line)
            if sm:
                gd = sm.groupdict()
                # Keep the logger in the message so Drain clusters "AuthService: sign failed" apart from other sign failures.
                level, text = gd["level"], f"{gd['logger']}: {gd['msg']}"
            else:
                lm = LEVEL_RE.search(line[:200])        # only the head, so a level word in the message body is ignored
                level = lm.group(1) if lm else ""
                text = LEAD_TS_RE.sub("", line)         # drop a leading timestamp the regexes did not consume
        level = {"WARNING": "WARN", "SEVERE": "ERROR"}.get(level, level) or "ERROR"

        first, *rest = text.split("\n")
        ev = Event(
            ts_ns=e.ts_ns,
            namespace=e.labels.get("namespace", "-"),
            service=_service(e.labels, service_label),
            pod=e.labels.get("pod", "-"),
            level=level,
            message=mask(first)[:1000],                 # the line Drain clusters on
            raw=mask(text)[:6000],                      # full text, already masked, for samples and code location
        )
        exc = EXC_RE.search(text)
        ev.exception = exc.group(1) if exc else None
        causes = CAUSED_RE.findall(text)
        if causes:
            ev.root_cause = causes[-1][0]               # the innermost cause, not the wrapper
        ev.error_codes = sorted(set(ERRCODE_RE.findall(text)))
        tids = set(TRACE_RE.findall(text))
        if trace_from_json:
            tids.add(str(trace_from_json))
        ev.trace_ids = sorted(tids)
        if not js and sm:
            gd = sm.groupdict()
            ev.log_logger = gd.get("logger")
            ev.log_method = gd.get("method")
            ev.log_line = int(gd["line"]) if gd.get("line") else None
        events.append(ev)
        last_by_stream[key] = ev
    return events
