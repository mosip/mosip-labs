"""Known-issue catalog: YAML signatures -> probable cause + fix. Team-maintained tribal knowledge."""
from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import yaml

from .miner import Issue


_KNOWN_KEYS = ("id", "title", "severity", "cause", "fix", "owner", "review")


class Catalog:
    def __init__(self, paths: list[str], ignore: list[str] | None = None):
        """Load the built-in catalog, then any team files. Later files add entries; they do not replace earlier ones.

        `ignore` is a list of catalog ids the team has marked as false positives. Those entries never attach.
        An entry with `suppress: true` is the same thing, recorded in the catalog file itself.
        """
        self.ignore = set(ignore or [])
        self.entries = []
        texts = [resources.files("roottrace").joinpath("known_issues.yaml").read_text()]
        texts += [Path(p).read_text() for p in paths]
        for t in texts:
            for e in (yaml.safe_load(t) or {}).get("issues", []):
                m = e.get("match", {})
                # Compile once. A missing regex means the entry never matches (it is kept, not rejected).
                e["_rx"] = re.compile(m["regex"], re.I) if m.get("regex") else None
                e["_svc"] = re.compile(m["service"], re.I) if m.get("service") else None
                self.entries.append(e)

    def apply(self, issues: list[Issue]):
        """Attach every catalog hit onto the issue. Scoring reads iss.known, so call this before the final score."""
        for iss in issues:
            # Template plus the concrete samples. The template has <*> where numbers were, so samples still matter.
            hay = "\n".join([iss.template, *iss.exceptions, *iss.root_causes, *iss.error_codes,
                             *(s["text"][:1500] for s in iss.samples)])
            for e in self.entries:
                if e.get("suppress") or e.get("id") in self.ignore:
                    continue
                if e["_svc"] and not e["_svc"].search(iss.service):
                    continue                                    # optional service regex, e.g. "print|credential"
                if e["_rx"] and e["_rx"].search(hay):
                    iss.known.append({k: e.get(k) for k in _KNOWN_KEYS})

    def apply_k8s(self, findings: list[dict]):
        """Same catalog, but only entries marked scope: k8s, matched against pod reason + event message."""
        for f in findings:
            hay = f"{f.get('reason','')} {f.get('message','')}"
            for e in self.entries:
                if e.get("suppress") or e.get("id") in self.ignore:
                    continue
                if e.get("scope") == "k8s" and e["_rx"] and e["_rx"].search(hay):
                    f.setdefault("known", []).append({k: e.get(k) for k in _KNOWN_KEYS})
