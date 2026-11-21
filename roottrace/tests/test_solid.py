"""History, logs-missing, false positives, deploy timing, Loki retry, packaged sources."""
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from roottrace.catalog import Catalog  # noqa: E402
from roottrace.deps import DepMap, analyze  # noqa: E402
from roottrace.loki import LokiClient  # noqa: E402
from roottrace.config import LokiConfig  # noqa: E402
from roottrace.miner import Issue  # noqa: E402
from roottrace.report import build, write  # noqa: E402
import requests  # noqa: E402


def test_logs_missing():
    raw = {
        "issues": [
            {"namespace": "pms", "service": "pms-partner", "template": "Error connecting to OIDC service",
             "level": "ERROR", "count": 5, "is_new": True, "first_ns": 10**18, "score": 30,
             "root_causes": {}, "exceptions": {}, "error_codes": {}, "pods": ["pms-partner-abc"],
             "samples": [{"text": "Error connecting to OIDC service"}], "known": [], "path": []},
            {"namespace": "resident", "service": "resident", "template": "Error connecting to OIDC service",
             "level": "ERROR", "count": 5, "is_new": True, "first_ns": 10**18, "score": 30,
             "root_causes": {}, "exceptions": {}, "error_codes": {}, "pods": ["resident-abc"],
             "samples": [{"text": "Error connecting to OIDC service"}], "known": [], "path": []},
        ],
        "k8s": [], "silent": [],
        "logged_namespaces": ["pms", "resident"],
    }
    chains = {c["root"]: c for c in analyze(raw, DepMap())["chains"]}
    assert chains["keycloak"]["status"] == "logs-missing", chains["keycloak"]["status"]


def test_false_positive():
    def one():
        iss = Issue(key="k", namespace="pms", service="pms-partner", template="", level="ERROR")
        iss.template = "Error connecting to OIDC service"
        iss.samples = [{"text": "Error connecting to OIDC service"}]
        return iss
    hit = one()
    Catalog([]).apply([hit])
    assert any(k["id"] == "AUTH-002" for k in hit.known), hit.known
    missed = one()
    Catalog([], ignore=["AUTH-002"]).apply([missed])
    assert all(k["id"] != "AUTH-002" for k in missed.known), missed.known


def test_since_deploy_and_history(tmp=None):
    result = {
        "environment": "t", "window_from": "-", "window_to": "-", "baseline_offset": "24h",
        "namespaces": "", "generated": "-", "query": "{}",
        "issues": [{
            "namespace": "idrepo", "service": "credentialrequest", "template": "credentialReProcessJob ClassCastException",
            "level": "ERROR", "count": 1, "baseline_count": 0, "is_new": True, "score": 10,
            "first_ns": 10**18, "last_ns": 10**18, "pods": ["credentialrequest-a"],
            "exceptions": {}, "root_causes": {}, "error_codes": {}, "trace_ids": ["TXN1"],
            "samples": [{"ts_ns": 10**18, "pod": "credentialrequest-a", "text": "ClassCastException"}],
            "known": [], "code": None, "path": [], "since_deploy": True,
        }],
        "resolved": [], "silent": [], "k8s": [], "rollouts": [{"ts_ns": 10**18 - 1, "namespace": "idrepo", "name": "credentialrequest", "images": "x"}],
        "k8s_error": None, "deps": {"chains": [], "components": {}, "graph": []},
        "grafana_url": "http://grafana.example", "public_url": "http://roottrace.example",
        "service_label": "app", "report_history": 1,
    }
    shaped = build(result)
    assert shaped["issues"][0]["grafana"].startswith("http://grafana.example/explore")
    assert shaped["issues"][0]["traces"][0]["url"].endswith("/trace/TXN1?since=6h")
    out = Path(tempfile.mkdtemp())
    write(shaped, str(out))
    old = out / "history" / "roottrace-report-20000101T000000Z.html"
    old.write_text("old", encoding="utf-8")
    old.with_suffix(".json").write_text("{}", encoding="utf-8")
    write(shaped, str(out))
    htmls = list((out / "history").glob("roottrace-report-*.html"))
    assert len(htmls) == 1 and not old.exists(), [p.name for p in htmls]
    assert "since deploy" in (out / "roottrace-report.html").read_text(encoding="utf-8")
    streak = dict(shaped)
    streak["issues"] = [dict(shaped["issues"][0], key="idrepo/credentialrequest#1", since_deploy=None)]
    streak["report_history"] = 48
    hist = out / "history"
    for day in ("20261117", "20261118", "20261119"):
        (hist / f"roottrace-report-{day}T000000Z.json").write_text(
            '{"issues":[{"key":"idrepo/credentialrequest#1","is_new":true}]}', encoding="utf-8")
    write(streak, str(out))
    assert "new all week" in (out / "roottrace-report.html").read_text(encoding="utf-8")
    streak["issues"][0].pop("new_streak", None)
    for path in hist.glob("roottrace-report-2026*.json"):
        path.unlink()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for day in ("20261117", "20261118", today):
        (hist / f"roottrace-report-{day}T000000Z.json").write_text(
            '{"issues":[{"key":"idrepo/credentialrequest#1","is_new":true}]}', encoding="utf-8")
    write(streak, str(out))
    assert "new all week" not in (out / "roottrace-report.html").read_text(encoding="utf-8")


def test_loki_retries():
    cfg = LokiConfig(url="http://loki.invalid", retries=2, timeout_s=1)
    client = LokiClient(cfg)
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.ConnectionError("reset")
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "success", "data": {"result": []}}
        return resp

    client.s.get = boom
    data = client._get("/loki/api/v1/query", {"query": "{}"})
    assert data == {"result": []}
    assert calls["n"] == 2


def test_sources_packaged():
    from importlib.resources import files
    text = files("roottrace").joinpath("sources.yaml").read_text(encoding="utf-8")
    assert "io.mosip.authentication" in text


def main():
    test_logs_missing()
    test_false_positive()
    test_since_deploy_and_history()
    test_loki_retries()
    test_sources_packaged()
    print("SOLID CHECKS PASSED")


if __name__ == "__main__":
    main()
