"""Configuration loading. Values in YAML can be overridden by ROOTTRACE_* env vars."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LokiConfig:
    url: str = "http://localhost:3100"          # laptop tunnel, or in-cluster service DNS
    username: str | None = None                 # basic auth; leave null and use ROOTTRACE_LOKI_USER
    password: str | None = None
    bearer_token: str | None = None             # alternative to basic auth
    org_id: str | None = None                   # X-Scope-OrgID for multi-tenant Loki
    verify_tls: bool = True
    page_size: int = 5000                       # lines per query_range page
    max_lines: int = 200_000                    # safety cap per query window
    timeout_s: int = 60                         # one HTTP call; a full scan issues several
    retries: int = 3                            # extra attempts on connection errors, 429, and 5xx


@dataclass
class K8sConfig:
    enabled: bool = True
    kubeconfig: str | None = None               # Rancher-downloaded kubeconfig; None = default / in-cluster
    context: str | None = None                  # which context inside that kubeconfig
    evidence: bool = True                       # tail of the previous container log for crashing pods
    revisions: bool = False                     # exec into a few pods and read git.properties from the jar


@dataclass
class Config:
    loki: LokiConfig = field(default_factory=LokiConfig)
    k8s: K8sConfig = field(default_factory=K8sConfig)
    namespaces: list[str] = field(default_factory=list)   # empty = every namespace except the exclude list
    exclude_namespaces: list[str] = field(default_factory=lambda: [
        # Platform namespaces. Their errors are real, but they drown MOSIP service signals.
        "kube-system", "cattle-system", "cattle-monitoring-system", "cattle-logging-system",
        "cattle-fleet-system", "fleet-system", "longhorn-system", "istio-system",
    ])
    service_label: str = "app"         # Loki label used as the service name; falls back to container/pod
    # Pre-filter pushed into Loki so we do not pull every info line. Matched case-insensitively.
    error_filter: str = r"(?i)(error|exception|fatal|severe|caused by|failed|refused|timed? ?out)"
    include_warn: bool = True          # WARN lines are kept; the miner still scores them below ERROR
    baseline_offset: str = "24h"       # compare to the same-length window this far in the past
    spike_factor: float = 3.0          # current/baseline ratio that counts as a spike
    critical_score: float = 50.0       # any issue at or above this forces scan exit code 2
    catalog_paths: list[str] = field(default_factory=list)             # extra known-issue YAML files
    dependency_map_paths: list[str] = field(default_factory=list)      # extra/override dependency maps
    slack_webhook: str | None = None
    environment_name: str = "env"      # printed in the report header and the Slack digest
    public_url: str | None = None      # e.g. https://roottrace.dev.mosip.net (used for Slack links)
    grafana_url: str | None = None     # Grafana base URL; each pattern gets an Explore link
    api_token: str | None = None       # if set, /scan and /trace require Authorization: Bearer
    ignore_issue_ids: list[str] = field(default_factory=list)  # catalog ids to treat as false positives
    report_history: int = 48           # timestamped copies kept beside the latest report


def _merge(dc, data: dict):
    """Copy YAML keys onto a dataclass. Nested dicts recurse so loki: {url: ...} fills LokiConfig."""
    for k, v in (data or {}).items():
        if hasattr(dc, k):                          # unknown keys are ignored, not errors
            cur = getattr(dc, k)
            if hasattr(cur, "__dataclass_fields__") and isinstance(v, dict):
                _merge(cur, v)                      # loki / k8s blocks
            else:
                setattr(dc, k, v)                   # YAML wins over the dataclass default


def load_config(path: str | None) -> Config:
    """Defaults, then the YAML file, then ROOTTRACE_* env vars. Env always wins so secrets stay out of the file."""
    cfg = Config()
    if path:
        _merge(cfg, yaml.safe_load(Path(path).read_text()) or {})
    env = os.environ
    # Each lookup falls back to whatever YAML (or the default) already set.
    cfg.loki.url = env.get("ROOTTRACE_LOKI_URL", cfg.loki.url)
    cfg.loki.username = env.get("ROOTTRACE_LOKI_USER", cfg.loki.username)
    cfg.loki.password = env.get("ROOTTRACE_LOKI_PASSWORD", cfg.loki.password)
    cfg.loki.bearer_token = env.get("ROOTTRACE_LOKI_TOKEN", cfg.loki.bearer_token)
    cfg.loki.org_id = env.get("ROOTTRACE_LOKI_ORG", cfg.loki.org_id)
    cfg.slack_webhook = env.get("ROOTTRACE_SLACK_WEBHOOK", cfg.slack_webhook)
    cfg.environment_name = env.get("ROOTTRACE_ENV_NAME", cfg.environment_name)
    cfg.public_url = env.get("ROOTTRACE_PUBLIC_URL", cfg.public_url)
    cfg.grafana_url = env.get("ROOTTRACE_GRAFANA_URL", cfg.grafana_url)
    cfg.api_token = env.get("ROOTTRACE_API_TOKEN", cfg.api_token)
    return cfg
