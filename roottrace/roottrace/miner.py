"""Cluster events into templates (Drain3), diff against a baseline, score issues."""
from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

from .parser import Event, code_location, frames_in

# Multiplier inside the score. FATAL outranks ERROR, which outranks WARN. Unknown levels score as 1.
LEVEL_WEIGHT = {"FATAL": 3.0, "ERROR": 2.0, "WARN": 1.0}


@dataclass
class Issue:
    """One Drain template for one service: how often it fired now, how often yesterday, and why it ranks."""
    key: str                                # "namespace/service#clusterId"
    namespace: str
    service: str
    template: str                           # Drain template, with <*> where tokens varied
    level: str
    count: int = 0                          # lines in the current window
    baseline_count: int = 0                 # lines in the comparison window
    first_ns: int = 0
    last_ns: int = 0
    pods: set = field(default_factory=set)
    exceptions: Counter = field(default_factory=Counter)
    root_causes: Counter = field(default_factory=Counter)
    error_codes: Counter = field(default_factory=Counter)
    trace_ids: list = field(default_factory=list)
    samples: list = field(default_factory=list)     # up to 3 masked raw lines
    marks: list = field(default_factory=list)       # when this pattern fired, for cross-service time joins
    known: list = field(default_factory=list)       # catalog matches
    code: dict | None = None                        # application throw site
    code_note: str | None = None                    # why code is empty: no stack, or no io.mosip frame
    path: list = field(default_factory=list)        # services that logged a shared trace id, in order
    since_deploy: bool | None = None                # True when a rollout is in the window and this pattern started after it
    score: float = 0.0

    @property
    def is_new(self) -> bool:
        return self.baseline_count == 0             # never seen in the comparison window

    @property
    def ratio(self) -> float:
        return self.count / max(self.baseline_count, 1)    # avoid divide-by-zero for brand-new patterns

    def to_dict(self) -> dict:
        # Counters become plain dicts of the most common values so JSON and the HTML stay small.
        return {
            "key": self.key, "namespace": self.namespace, "service": self.service,
            "template": self.template, "level": self.level, "count": self.count,
            "baseline_count": self.baseline_count, "is_new": self.is_new,
            "first_ns": self.first_ns, "last_ns": self.last_ns, "pods": sorted(self.pods),
            "exceptions": dict(self.exceptions.most_common(5)),
            "root_causes": dict(self.root_causes.most_common(5)),
            "error_codes": dict(self.error_codes.most_common(10)),
            "trace_ids": self.trace_ids[:10], "samples": self.samples, "marks": self.marks,
            "known": self.known, "code": self.code, "code_note": self.code_note, "path": self.path,
            "since_deploy": self.since_deploy, "score": round(self.score, 1),
        }


def keep(ev: Event, include_warn: bool) -> bool:
    """Drop lines that are not worth clustering. INFO is kept only when it carries an exception."""
    if ev.level in ("ERROR", "FATAL"):
        return True
    if ev.level == "WARN":
        return include_warn or bool(ev.exception)   # a WARN that wraps an exception is still a failure
    return bool(ev.exception)                       # INFO/DEBUG lines that still carry an exception


class Miner:
    """One Drain miner per service. Templates are learned from baseline and current lines together,
    so the same wording gets the same cluster id in both windows and the diff is meaningful.
    """

    def __init__(self):
        c = TemplateMinerConfig()
        c.drain_sim_th = 0.45                  # how similar two lines must be to share a cluster
        c.drain_depth = 5                      # tokens kept in the prefix tree
        c.parametrize_numeric_tokens = True    # numbers become <*> so counts do not split clusters
        c.masking_instructions = []            # masking already happened in the parser
        self._miners: dict[str, TemplateMiner] = {}
        self._cfg = c
        self.issues: dict[str, Issue] = {}

    def _miner(self, service: str) -> TemplateMiner:
        # A fresh miner per service. Otherwise "connection refused" in ida and in keymanager collapse into one row.
        if service not in self._miners:
            self._miners[service] = TemplateMiner(config=self._cfg)
        return self._miners[service]

    def _cluster(self, ev: Event) -> str:
        """Feed one line to Drain and return the issue key. The cause is appended so two templates
        that share a message but wrap different exceptions stay separate.
        """
        text = ev.message
        if ev.root_cause and ev.root_cause not in text:
            text += f" [cause {ev.root_cause}]"
        r = self._miner(f"{ev.namespace}/{ev.service}").add_log_message(text)
        return f"{ev.namespace}/{ev.service}#{r['cluster_id']}"

    def add_baseline(self, events: list[Event]):
        """Count only. Baseline lines teach Drain the template but do not become samples or scores."""
        for ev in events:
            key = self._cluster(ev)
            iss = self._get(key, ev)
            iss.baseline_count += 1

    def add_current(self, events: list[Event]):
        """Count the live window and keep the evidence the report shows: pods, samples, codes, throw site."""
        for ev in events:
            key = self._cluster(ev)
            iss = self._get(key, ev)
            iss.count += 1
            # Keep when it fired, spread across the window. The first 4000 are kept whole;
            # after that each new line has an even chance to replace one, so a chatty pattern
            # does not only remember the start of the day.
            if len(iss.marks) < 4000:
                iss.marks.append(ev.ts_ns)
            else:
                j = random.randrange(iss.count)
                if j < 4000:
                    iss.marks[j] = ev.ts_ns
            iss.first_ns = ev.ts_ns if not iss.first_ns else min(iss.first_ns, ev.ts_ns)
            iss.last_ns = max(iss.last_ns, ev.ts_ns)
            iss.pods.add(ev.pod)
            if LEVEL_WEIGHT.get(ev.level, 0) > LEVEL_WEIGHT.get(iss.level, 0):
                iss.level = ev.level                # a cluster that is mostly WARN but once FATAL is FATAL
            if ev.exception:
                iss.exceptions[ev.exception] += 1
            if ev.root_cause:
                iss.root_causes[ev.root_cause] += 1
            iss.error_codes.update(ev.error_codes)
            for t in ev.trace_ids:
                if len(iss.trace_ids) < 20 and t not in iss.trace_ids:
                    iss.trace_ids.append(t)         # enough ids to jump into `roottrace trace`, not all of them
            if len(iss.samples) < 3:
                iss.samples.append({"ts_ns": ev.ts_ns, "pod": ev.pod, "text": ev.raw[:3000]})
            if iss.code is None:
                loc = code_location(ev)            # first event that can name a MOSIP frame wins
                if loc:
                    iss.code = {**loc, "pod": ev.pod}
                    iss.code_note = None
                elif not iss.code_note:
                    # A one-line message has nothing to open. A stack of library frames is a different gap.
                    iss.code_note = "stack has no io.mosip frame" if frames_in(ev.raw) else "no stack in this window"

    def _get(self, key: str, ev: Event) -> Issue:
        if key not in self.issues:
            # Template text is filled in finalize(); Drain rewrites it as more lines merge.
            self.issues[key] = Issue(key=key, namespace=ev.namespace, service=ev.service,
                                     template="", level=ev.level)
        return self.issues[key]

    def finalize(self, spike_factor: float) -> list[Issue]:
        """Copy the latest Drain template onto each issue and score the ones that fired in this window.

        Called twice by the engine: once so the catalog can match templates, then again so the
        catalog severity is part of the score.
        """
        for key, iss in self.issues.items():
            svc, cid = key.rsplit("#", 1)
            for c in self._miner(svc).drain.clusters:
                if str(c.cluster_id) == cid:
                    iss.template = c.get_template()
        out = [i for i in self.issues.values() if i.count > 0]     # baseline-only rows are "resolved", not issues
        for i in out:
            # Volume is log10 so 10_000 lines do not bury a new FATAL that fired twice.
            s = LEVEL_WEIGHT.get(i.level, 1.0) * 5 * math.log10(1 + i.count)
            if i.is_new:
                s += 25                                 # did not exist in the baseline window
            elif i.ratio >= spike_factor:
                s += 10 * min(math.log2(i.ratio), 4)    # a spike, capped so a 1000x blip cannot dominate
            s += 3 * min(len(i.pods), 5)                # same error on many pods is more serious than one pod
            for k in i.known:
                s += {"critical": 30, "high": 20, "medium": 10}.get(k.get("severity"), 5)
            i.score = s
        return sorted(out, key=lambda i: i.score, reverse=True)

    def resolved(self) -> list[Issue]:
        """Templates present in the baseline but gone now. That can be a fix, or a service that stopped logging."""
        return sorted([i for i in self.issues.values() if i.count == 0 and i.baseline_count >= 5],
                      key=lambda i: i.baseline_count, reverse=True)
