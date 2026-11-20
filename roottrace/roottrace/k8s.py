"""Kubernetes health signals: restarts, bad pod states, warning events, recent rollouts.

Read-only. A failure here is recorded on the result and the log report still runs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .buildinfo import revision_from
from .config import K8sConfig
from .parser import mask

log = logging.getLogger(__name__)
# Waiting reasons that mean the container is not serving, as opposed to ContainerCreating on a fresh start.
BAD_WAITING = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "CreateContainerConfigError",
               "CreateContainerError", "InvalidImageName", "RunContainerError"}


def _ns_of(t) -> int:
    """Kubernetes client datetimes -> nanoseconds. Missing timestamps become 0 so they fail the window test."""
    if t is None:
        return 0
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)          # the client sometimes returns naive UTC
    return int(t.timestamp() * 1e9)


def collect(cfg: K8sConfig, namespaces: list[str], exclude: list[str], start_ns: int, end_ns: int) -> dict:
    """Returns {"findings": [...], "rollouts": [...], "error": str|None}. Never raises.

    Pod *states* (CrashLoop, NotReady) are reported even if they started before the window, because
    the pod is still broken now. Restarts, warning events and rollouts are limited to the window.
    """
    result = {"findings": [], "rollouts": [], "error": None}
    if not cfg.enabled:
        return result
    try:
        from kubernetes import client, config as kcfg
        try:
            # Outside the cluster, always use the kubeconfig (Rancher download). Inside, use the service account
            # unless a kubeconfig path was set explicitly.
            if cfg.kubeconfig or not _in_cluster():
                kcfg.load_kube_config(config_file=cfg.kubeconfig, context=cfg.context)
            else:
                kcfg.load_incluster_config()
        except Exception:
            kcfg.load_incluster_config()            # kubeconfig load failed; try the in-cluster fallback once
        core, apps = client.CoreV1Api(), client.AppsV1Api()
        log_budget = {"n": 0}

        def stamp(pod, cs, finding):
            """Record the image, and for a few crashing pods the previous container log (masked)."""
            image = next((c.image for c in (pod.spec.containers or []) if c.name == cs.name), None)
            finding["image"] = image
            finding["image_id"] = getattr(cs, "image_id", None)
            if cfg.evidence and finding["kind"] in ("pod-state", "restart") and log_budget["n"] < 8:
                log_budget["n"] += 1
                try:
                    text = core.read_namespaced_pod_log(
                        pod.metadata.name, finding["namespace"], container=cs.name,
                        previous=True, tail_lines=40, _request_timeout=20)
                    finding["previous_logs"] = mask(text or "")[:2000]
                except Exception as ex:
                    log.info("previous logs skipped for %s/%s: %s", finding["namespace"], finding["pod"], ex)
            return finding

        ns_list = namespaces or [n.metadata.name for n in core.list_namespace().items]
        ns_list = [n for n in ns_list if n not in exclude]
        for ns in ns_list:
            for pod in core.list_namespaced_pod(ns).items:
                for cs in (pod.status.container_statuses or []):
                    w = cs.state.waiting if cs.state else None
                    if w and w.reason in BAD_WAITING:
                        result["findings"].append(stamp(pod, cs, dict(
                            kind="pod-state", namespace=ns, pod=pod.metadata.name,
                            container=cs.name, reason=w.reason,
                            message=(w.message or "")[:400], restarts=cs.restart_count)))
                    term = cs.last_state.terminated if cs.last_state else None
                    # A restart counts only when the previous container died inside this window.
                    if cs.restart_count and term and start_ns <= _ns_of(term.finished_at) <= end_ns:
                        result["findings"].append(stamp(pod, cs, dict(
                            kind="restart", namespace=ns, pod=pod.metadata.name,
                            container=cs.name, reason=term.reason or "Restarted",
                            message=f"exit code {term.exit_code}", restarts=cs.restart_count,
                            ts_ns=_ns_of(term.finished_at))))
                    # Running but not ready, and not already reported as CrashLoop / ImagePull.
                    if pod.status.phase == "Running" and not cs.ready and not (w and w.reason in BAD_WAITING):
                        result["findings"].append(dict(kind="not-ready", namespace=ns, pod=pod.metadata.name,
                                                       container=cs.name, reason="NotReady", message="",
                                                       restarts=cs.restart_count))
                if pod.status.phase == "Failed" or pod.status.reason == "Evicted":
                    ends = [_ns_of(cs.state.terminated.finished_at) for cs in (pod.status.container_statuses or [])
                            if cs.state and cs.state.terminated]
                    fin = max(ends) if ends else _ns_of(pod.status.start_time)
                    if start_ns <= fin <= end_ns:
                        # A failed Job pod (test rig) is a different kind from a workload that crashed.
                        is_job = any(o.kind == "Job" for o in (pod.metadata.owner_references or []))
                        result["findings"].append(dict(kind="job-failed" if is_job else "pod-state", namespace=ns,
                                                       pod=pod.metadata.name, container="-",
                                                       reason=pod.status.reason or ("JobFailed" if is_job else "Failed"),
                                                       message=(pod.status.message or "")[:400], restarts=0, ts_ns=fin))
            for ev in core.list_namespaced_event(ns).items:
                ts = _ns_of(ev.last_timestamp or ev.event_time or ev.first_timestamp)
                if ev.type == "Warning" and start_ns <= ts <= end_ns:
                    # involved_object.kind is stored in `container` so the report can say Pod vs HPA vs Node.
                    result["findings"].append(dict(kind="event", namespace=ns, pod=ev.involved_object.name,
                                                   container=ev.involved_object.kind, reason=ev.reason,
                                                   message=(ev.message or "")[:400], restarts=ev.count or 1, ts_ns=ts))
            for rs in apps.list_namespaced_replica_set(ns).items:
                ts = _ns_of(rs.metadata.creation_timestamp)
                # A new ReplicaSet with replicas > 0 is a rollout. Zero-replica history is ignored.
                if start_ns <= ts <= end_ns and (rs.spec.replicas or 0) > 0:
                    owner = (rs.metadata.owner_references or [None])[0]
                    img = ", ".join(c.image.split("/")[-1] for c in rs.spec.template.spec.containers)
                    result["rollouts"].append(dict(namespace=ns, name=owner.name if owner else rs.metadata.name,
                                                   ts_ns=ts, images=img))
    except Exception as e:  # k8s is optional — the report still works on logs alone
        log.warning("Kubernetes collection skipped: %s", e)
        result["error"] = str(e)
    return result


_REV_SH = r"""
cmd=$(tr '\0' '\n' < /proc/1/cmdline)
jar=$(printf '%s\n' "$cmd" | grep -E '\.jar$' | head -n 1)
if [ -z "$jar" ] || [ ! -f "$jar" ]; then echo NOJAR; exit 0; fi
git=$(unzip -p "$jar" BOOT-INF/classes/service-git.properties 2>/dev/null)
if [ -z "$git" ]; then git=$(unzip -p "$jar" BOOT-INF/classes/git.properties 2>/dev/null); fi
build=$(unzip -p "$jar" META-INF/build-info.properties 2>/dev/null)
printf '%s\n----\n%s\n' "$git" "$build"
"""


def _parse_rev(text: str) -> dict:
    """Split the exec output into a revision dict. Missing commit is an error string, not an exception."""
    if "----" not in (text or ""):
        return {"error": ((text or "no output").strip()[:200])}
    git, build = text.split("----", 1)
    rev = revision_from(git, build).to_dict()
    if not rev.get("commit"):
        return {"error": "jar has no git.commit.id.full"}
    return rev


def read_revisions(cfg: K8sConfig, targets: list[tuple[str, str, str | None]]) -> list[dict]:
    """Exec into up to 8 pods and read git.properties from the jar named on pid 1's command line.

    Off unless k8s.revisions is true. Needs pods/exec. A container that is not running returns an error
    on its row; the rest of the scan still finishes.
    """
    if not cfg.enabled or not cfg.revisions:
        return []
    uniq: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    for ns, pod, container in targets:
        if (ns, pod) in seen:
            continue
        seen.add((ns, pod))
        uniq.append((ns, pod, container))
        if len(uniq) >= 8:
            break
    out: list[dict] = []
    try:
        from kubernetes import client, config as kcfg
        from kubernetes.stream import stream
        try:
            if cfg.kubeconfig or not _in_cluster():
                kcfg.load_kube_config(config_file=cfg.kubeconfig, context=cfg.context)
            else:
                kcfg.load_incluster_config()
        except Exception:
            kcfg.load_incluster_config()
        core = client.CoreV1Api()
        for ns, pod, container in uniq:
            row: dict = {"namespace": ns, "pod": pod, "container": container}
            try:
                live = core.read_namespaced_pod(pod, ns)
                name = container or (live.spec.containers[0].name if live.spec.containers else None)
                row["container"] = name
                row["image"] = next((c.image for c in (live.spec.containers or []) if c.name == name), None)
                text = stream(core.connect_get_namespaced_pod_exec, pod, ns, container=name,
                              command=["sh", "-c", _REV_SH], stderr=True, stdin=False,
                              stdout=True, tty=False, _request_timeout=20)
                row["revision"] = _parse_rev(text)
            except Exception as e:
                row["revision"] = {"error": str(e)[:200]}
            out.append(row)
    except Exception as e:
        log.warning("revision lookup skipped: %s", e)
    return out


def _in_cluster() -> bool:
    """True when this process is a pod. Kubernetes injects KUBERNETES_SERVICE_HOST."""
    import os
    return bool(os.environ.get("KUBERNETES_SERVICE_HOST"))
