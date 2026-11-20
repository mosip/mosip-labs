"""Dependency-aware root-cause analysis.

Combines a static dependency map with dependencies *observed* in error text, works out which
unhealthy components are roots and which are symptoms, and produces failure chains with
troubleshooting details.

A component is a root when it is unhealthy and nothing it depends on explains that. A map edge
is trusted only when the dependency is actually down (crashing, not ready, or silent). A dependency
that is merely degraded is blamed only when this service's own errors mention it.
"""
from __future__ import annotations

import re
from collections import defaultdict
from importlib import resources
from pathlib import Path

import yaml

# http://keycloak.keycloak/... or http://keycloak/ — first label, and the second label when it is "namespace.svc".
URL_HOST_RE = re.compile(r"https?://([a-z0-9][a-z0-9-]*)(?:\.([a-z0-9-]+))?", re.I)
# Reasons that mean the workload is not serving. A warning event that is not in this set is only "degraded".
HARD_K8S = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError",
            "CreateContainerError", "OOMKilled", "Evicted", "Failed", "NotReady", "RunContainerError"}


class Node:
    """One component in the dependency map: how to recognise it, what it calls, and extra kubectl hints."""

    def __init__(self, d: dict):
        self.name = d["name"]
        self.kind = d.get("kind", "service")           # service | infra | test
        m = d.get("match", {})
        # `$` anchors the end, so the YAML pattern "idrepo" matches "idrepo" and not "idrepo-extra".
        self.ns_rx = re.compile(f"(?:{m['namespace']})$", re.I) if m.get("namespace") else None
        self.app_rx = re.compile(m["app"], re.I) if m.get("app") else None
        self.mention_rx = re.compile(d["mentions"], re.I) if d.get("mentions") else None
        self.depends_on = list(d.get("depends_on", []))
        self.checks = list(d.get("checks", []))         # extra lines appended to the generated kubectl commands

    def matches(self, namespace: str, name: str) -> bool:
        """True when this node's namespace (and optional app) regex fits the pod/service being classified."""
        if self.ns_rx and not self.ns_rx.match(namespace or ""):
            return False
        if self.app_rx and not self.app_rx.search(name or ""):
            return False
        return bool(self.ns_rx or self.app_rx)         # a node with no matchers never claims a workload


class DepMap:
    """Built-in dependencies.yaml plus optional team files. A repeated name is overridden, not duplicated."""

    def __init__(self, extra_paths: list[str] | None = None):
        texts = [resources.files("roottrace").joinpath("dependencies.yaml").read_text()]
        texts += [Path(p).read_text() for p in (extra_paths or [])]
        by_name: dict[str, dict] = {}
        order: list[str] = []
        for t in texts:
            for d in (yaml.safe_load(t) or {}).get("nodes", []):
                if d["name"] in by_name:               # later files override / extend the same node
                    by_name[d["name"]].update(d)
                else:
                    by_name[d["name"]] = d
                    if t is texts[0]:
                        order.append(d["name"])        # built-in order is the file order
                    else:
                        # Team-added nodes are matched first so a more specific local name wins over a built-in one.
                        order.insert(0, d["name"])
        self.nodes = [Node(by_name[n]) for n in order]
        self.by_name = {n.name: n for n in self.nodes}

    def resolve(self, namespace: str, name: str) -> str:
        """Map a namespace + service/pod name onto a component. Unknown workloads keep their own name."""
        for n in self.nodes:
            if n.matches(namespace, name):
                return n.name
        return name or namespace

    def host_to_node(self, host: str, second: str | None) -> str | None:
        """http://keycloak.keycloak -> the keycloak node, using the host label or the next DNS label."""
        for cand in (host, second):
            if not cand:
                continue
            for n in self.nodes:
                if n.name == cand or (n.app_rx and n.app_rx.search(cand)) or (n.ns_rx and n.ns_rx.match(cand)):
                    return n.name
        return None


def _status_rank(s: str) -> int:
    """down outranks a suspected or logs-missing upstream, which outranks degraded."""
    return {"down": 3, "logs-missing": 2, "suspected": 2, "degraded": 1}.get(s, 0)


def _namespace_logged(node, logged: set) -> bool:
    """True when this component has no namespace matcher, or any logged namespace fits that matcher.

    A suspect whose namespace produced no lines at all is logs-missing: the callers failed,
    and we cannot see the callee. That is a different claim from 'the callee looks healthy'.
    """
    if node is None or node.ns_rx is None:
        return True
    return any(node.ns_rx.match(ns or "") for ns in logged)


def analyze(raw: dict, dm: DepMap) -> dict:
    """Turn issues, pod findings and silent services into failure chains.

    Returns chains (one per root), a status per component, and the edges that were considered.
    """
    issues, k8s, silent = raw["issues"], raw["k8s"], raw["silent"]
    # Every component we have evidence for. Missing keys start healthy with empty evidence.
    comp: dict[str, dict] = defaultdict(lambda: {"issues": [], "k8s": [], "silent": False, "namespaces": set(),
                                                 "first_ns": 0, "status": "healthy", "evidence": []})

    def first(c, ts):
        # Earliest timestamp this component showed trouble. 0 means "unknown" and must not win.
        if ts and (not c["first_ns"] or ts < c["first_ns"]):
            c["first_ns"] = ts

    # Fold logs, pods and silence onto components. The component name is written back onto each row
    # so the report can show "pms" instead of the raw deployment name.
    for i in issues:
        n = dm.resolve(i["namespace"], i["service"])
        i["component"] = n
        c = comp[n]; c["issues"].append(i); c["namespaces"].add(i["namespace"]); first(c, i["first_ns"])
    for f in k8s:
        n = dm.resolve(f["namespace"], f["pod"])
        f["component"] = n
        c = comp[n]; c["k8s"].append(f); c["namespaces"].add(f["namespace"]); first(c, f.get("ts_ns", 0))
    for s in silent:
        n = dm.resolve(s["namespace"], s["service"])
        c = comp[n]; c["silent"] = True; c["namespaces"].add(s["namespace"])

    # ---- health status per component
    for name, c in comp.items():
        # job-failed is a test rig, not the service being down. CrashLoop / NotReady / hard reasons are "down".
        hard = [f for f in c["k8s"] if f["kind"] != "job-failed"
                and (f["reason"] in HARD_K8S or f["kind"] in ("pod-state", "not-ready"))]
        if hard or c["silent"]:
            c["status"] = "down"
        elif c["issues"] or c["k8s"]:
            c["status"] = "degraded"                    # errors or soft events, process still up
        for f in c["k8s"]:
            c["evidence"].append(f"{f['kind']}: {f['pod']} — {f['reason']} {f.get('message','')[:140]}".strip())
        if c["silent"]:
            c["evidence"].append("no log lines at all in the window (was logging in the baseline)")
        for i in sorted(c["issues"], key=lambda x: -x["score"])[:4]:
            tag = "NEW " if i["is_new"] else ""
            cause = (list(i["root_causes"]) or list(i["exceptions"]) or [""])[0]
            c["evidence"].append(f"{tag}{i['level']} ×{i['count']} in {i['service']}: {i['template'][:160]}"
                                 + (f"  [{cause}]" if cause else ""))
    # Test-rig components are excluded from the root search so a failed Job is not called the cause of MOSIP.
    unhealthy = {n for n, c in comp.items() if c["status"] != "healthy" and dm.by_name.get(n, Node({"name": n})).kind != "test"}

    # ---- edges: static map, then whatever the error text itself names
    edges: dict[str, dict[str, dict]] = defaultdict(dict)   # from -> to -> {source, evidence}
    for n in dm.nodes:
        for d in n.depends_on:
            edges[n.name][d] = {"source": "map", "evidence": None}
    for name in unhealthy:
        for i in comp[name]["issues"]:
            text = " ".join([i["template"], *(s["text"][:1500] for s in i["samples"])])
            for node in dm.nodes:
                if node.name == name or not node.mention_rx:
                    continue
                # Prefer the template (stable) and fall back to a sample (has the original host name).
                m = node.mention_rx.search(i["template"]) or node.mention_rx.search(text)
                if m:
                    edges[name][node.name] = {"source": "logs", "evidence": f"{i['service']}: …{_around(text, m)}…"}
            for host, second in URL_HOST_RE.findall(text):
                tgt = dm.host_to_node(host, second)
                if tgt and tgt != name:
                    edges[name][tgt] = {"source": "logs", "evidence": f"{i['service']} calls http://{host}"}

    # ---- suspects: a healthy-looking component that at least two unhealthy components name in their logs.
    # One complainer is not enough; that is just a client bug. Two means the shared upstream is the story.
    complainers: dict[str, set] = defaultdict(set)
    for a, outs in edges.items():
        if a in unhealthy:
            for b, e in outs.items():
                if e["source"] == "logs" and b not in unhealthy:
                    complainers[b].add(a)
    suspects = {b for b, who in complainers.items() if len(who) >= 2}
    for b in suspects:
        c = comp[b]; c["status"] = "suspected"
        c["evidence"].insert(0, f"no errors or pod problems of its own, but {len(complainers[b])} components fail "
                                f"talking to it ({', '.join(sorted(complainers[b]))}) — check network, credentials, "
                                f"config, or whether its logs reach Loki")
    # Callers can pass every namespace that logged anything (not only errors). A suspect whose
    # own namespace is absent from that set is logs-missing, not a confirmed healthy upstream.
    if raw.get("logged_namespaces") is not None:
        logged = set(raw["logged_namespaces"])
        for b in suspects:
            if _namespace_logged(dm.by_name.get(b), logged):
                continue
            who = ", ".join(sorted(complainers[b]))
            comp[b]["status"] = "logs-missing"
            comp[b]["evidence"][0] = (
                f"no log lines from this component in the window, and {len(complainers[b])} components fail "
                f"talking to it ({who}). Its logs are not in Loki, so this is not a confirmed outage."
            )
    bad = unhealthy | suspects

    def blamed(n):
        """Dependencies that explain n's trouble.

        A log mention always counts. A map edge counts only when the dependency is hard-down, or when
        both sides are already 'suspected' (they are the same kind of opaque upstream failure).
        A map edge to a merely degraded neighbour is ignored, so two unrelated errors are not merged.
        """
        out = []
        for d, e in edges.get(n, {}).items():
            if d == n or d not in bad:
                continue
            ds, ns_ = comp[d]["status"], comp[n]["status"]
            if e["source"] == "logs" or ds == "down" or (ds == "suspected" and ns_ == "suspected"):
                out.append(d)
        return out

    # ---- roots: bad nodes with no blamed dependency. Cycles have no such node, so the strongest
    # (then earliest) uncovered node is promoted until every bad node sits in some root's upstream set.
    roots = {n for n in bad if not blamed(n)}
    covered = set()
    for r in roots:
        covered |= _upstream_of(r, bad, blamed)
    for n in sorted(bad - covered - roots, key=lambda n: (-_status_rank(comp[n]["status"]), comp[n]["first_ns"] or 1 << 62)):
        if n not in covered:                    # inside a cycle with no clean root
            roots.add(n)
            covered |= _upstream_of(n, bad, blamed)

    # ---- build chains. rev is "who depends on me among the bad set", i.e. the impact tree.
    rev: dict[str, list] = defaultdict(list)
    for a in bad:
        for d in blamed(a):
            rev[d].append(a)
    chains = []
    for r in roots:
        c = comp[r]
        node = dm.by_name.get(r)
        # Catalog hits from this component's own logs and from its pod findings, keyed so duplicates collapse.
        known = {k["id"]: k for i in c["issues"] for k in i["known"]}
        known.update({k["id"]: k for f in c["k8s"] for k in f.get("known", [])})
        tree = _tree(r, rev, comp, edges, c["first_ns"], set([r]))
        if c["status"] in ("suspected", "logs-missing"):
            # A suspect has no errors of its own. The useful catalog text lives on the services that call it.
            for up in _flatten(tree):
                for i in comp[up]["issues"]:
                    for k in i["known"]:
                        known.setdefault(k["id"], k)
        # Infra (postgres, keycloak, activemq) does not get a Java throw site. Services do.
        code = None
        if not node or node.kind != "infra":
            ranked = sorted(c["issues"], key=lambda i: -i.get("score", 0))
            code = next((i.get("code") for i in ranked if i.get("code")), None)
        # Union of per-issue request paths, in the order the issues started.
        request_path = []
        for i in sorted(c["issues"], key=lambda i: i.get("first_ns") or 0):
            for svc in i.get("path") or []:
                if svc not in request_path:
                    request_path.append(svc)
        impacted = _count(tree)
        dependents = [n.name for n in dm.nodes if r in n.depends_on]
        at_risk = [d for d in dependents if d not in bad]      # still healthy, but they call this root
        pods = {p for i in c["issues"] for p in i.get("pods") or []} | {f.get("pod") for f in c["k8s"]}
        revision = image = previous_logs = None
        for row in raw.get("revisions") or []:
            if row.get("pod") in pods and (row.get("revision") or {}).get("commit"):
                revision, image = row["revision"], row.get("image")
                break
        for f in c["k8s"]:
            if not revision and (f.get("revision") or {}).get("commit"):
                revision = f["revision"]
            image = image or f.get("image")
            previous_logs = previous_logs or f.get("previous_logs")
        chains.append({
            "root": r, "kind": node.kind if node else "service", "status": c["status"],
            "namespaces": sorted(c["namespaces"]) or [r], "first_ns": c["first_ns"],
            "evidence": c["evidence"][:8], "known": list(known.values()),
            "revision": revision, "image": image, "previous_logs": previous_logs,
            "checks": _checks(r, node, c), "impacted": tree, "impacted_count": impacted,
            "code": code, "request_path": request_path,
            "at_risk": at_risk[:10],
            # down/suspected/degraded dominates, then how many components are dragged along, then the worst score.
            "rank": (_status_rank(c["status"]) * 1000 + impacted * 50
                     + max([i["score"] for i in c["issues"]] or [0])),
        })
    chains.sort(key=lambda ch: -ch["rank"])
    # Keep edges that touch the bad set so the JSON graph is the failure, not the whole MOSIP map.
    graph_edges = sorted({(a, b, e["source"]) for a, outs in edges.items() for b, e in outs.items()
                          if a in bad or b in bad})
    return {"chains": chains, "components": {n: comp[n]["status"] for n in comp},
            "graph": [{"from": a, "to": b, "source": s, "blamed": b in bad and a in bad} for a, b, s in graph_edges]}


def _around(text: str, m: re.Match, w: int = 60) -> str:
    """A short slice of the log line around a regex hit, for the impact-tree 'why this link' text."""
    return text[max(0, m.start() - w): m.end() + w].replace("\n", " ")


def _upstream_of(root, bad, blamed):
    """Every bad node that reaches `root` by following blamed() edges. Includes the root itself."""
    seen, stack = {root}, [root]
    while stack:
        cur = stack.pop()
        for n in bad:
            if n not in seen and cur in blamed(n):     # n blames cur, so n is downstream of this root
                seen.add(n); stack.append(n)
    return seen


def _tree(n, rev, comp, edges, root_first, seen):
    """Impact tree: components whose trouble is blamed on n, then the components blamed on those.

    before_root is set when a child started failing more than 60s before the root. The report
    warns that the two may be unrelated rather than hiding the child.
    """
    out = []
    for up in sorted(rev.get(n, [])):
        if up in seen:
            continue                                    # a cycle would otherwise recurse forever
        seen.add(up)
        c = comp[up]
        e = edges[up][n]
        out.append({
            "component": up, "status": c["status"], "via": e["source"], "via_evidence": e["evidence"],
            "symptoms": c["evidence"][:3],
            "before_root": bool(root_first and c["first_ns"] and c["first_ns"] < root_first - 60 * 10**9),
            "children": _tree(up, rev, comp, edges, root_first, seen),
        })
    return out


def _flatten(tree):
    """Component names in an impact tree, depth-first. Used to borrow catalog text for a suspect root."""
    for t in tree:
        yield t["component"]
        yield from _flatten(t["children"])


def _count(tree):
    """How many components sit under a root, not counting the root itself."""
    return sum(1 + _count(t["children"]) for t in tree)


def _checks(name, node, c):
    """kubectl lines aimed at the pod that is actually failing, plus any hints from the dependency map.

    Crashing pods are preferred over pods that only logged an error, so `describe` hits the broken one.
    """
    ns = sorted(c["namespaces"])[0] if c["namespaces"] else name
    crashing = sorted({f["pod"] for f in c["k8s"] if f["kind"] in ("pod-state", "restart", "not-ready")})
    pods = crashing + sorted({p for i in c["issues"] for p in i["pods"]} - set(crashing))
    pod = pods[0] if pods else "<pod>"
    out = [f"kubectl -n {ns} get pods -o wide",
           f"kubectl -n {ns} describe pod {pod}",
           f"kubectl -n {ns} logs {pod} --since=1h | findstr /i \"error exception\"",
           f"kubectl -n {ns} get events --sort-by=.lastTimestamp"]
    if any(f["kind"] == "restart" or f["reason"] == "CrashLoopBackOff" for f in c["k8s"]):
        out.insert(2, f"kubectl -n {ns} logs {pod} --previous   (logs of the crashed container)")
    if c["status"] == "suspected":
        # The pod looks healthy here, so the useful check is reachability from a caller, not another describe.
        out.append(f"From an affected pod, test reachability: kubectl -n <ns> exec <pod> -- curl -sv http://{name}.{ns}")
    return out + (node.checks if node else [])
