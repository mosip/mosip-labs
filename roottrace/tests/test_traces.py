"""Saved scans can be analyzed again without calling Loki."""
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from roottrace import engine  # noqa: E402
from roottrace.cli import main  # noqa: E402
from roottrace.config import Config  # noqa: E402
from roottrace.parser import Event  # noqa: E402
from roottrace.traces import load, save  # noqa: E402


def _ev(ts, ns, svc, msg, tid=None):
    return Event(ts_ns=ts, namespace=ns, service=svc, pod=svc + "-0", level="ERROR",
                 message=msg, raw=msg, trace_ids=[tid] if tid else [])


def test_roundtrip_and_rescan():
    cur = [_ev(1_000_000_000_000, "ida", "ida-auth", "IDA-MLC-019 sign failed TXN10042", "TXN10042"),
           _ev(1_000_000_000_100, "keymanager", "keymanager", "KER-KMS-012 failed TXN10042", "TXN10042")]
    base = [_ev(500_000_000_000, "ida", "ida-auth", "old warning")]
    gap = [{"which": "current", "from_ns": 1, "to_ns": 2, "reason": "stopped at max_lines"}]
    with tempfile.TemporaryDirectory() as tmp:
        dest = save(tmp, 10, 20, "24h", "{app=~\".+\"}", gap, cur, base)
        loaded = load(tmp)
        assert loaded.directory == dest
        assert loaded.current[0].trace_ids == ["TXN10042"]
        assert loaded.baseline[0].message == "old warning"
        assert loaded.coverage[0]["reason"] == "stopped at max_lines"

        cfg = Config()
        cfg.k8s.enabled = False
        cfg.loki.url = "http://127.0.0.1:1"          # must not be contacted
        r = engine.scan(cfg, loaded.start_ns, loaded.end_ns, loaded=loaded)
        assert r["stats"]["events"] == 2
        assert r["traces_from"]
        assert r["coverage"][0]["reason"] == "stopped at max_lines"
        services = {i["service"] for i in r["issues"]}
        assert services == {"ida-auth", "keymanager"}

        narrowed = engine.scan(cfg, loaded.start_ns, loaded.end_ns, ["keymanager"], loaded=loaded)
        assert {i["service"] for i in narrowed["issues"]} == {"keymanager"}

        cfg.namespaces = ["ida"]
        configured = engine.scan(cfg, loaded.start_ns, loaded.end_ns, loaded=loaded)
        assert {i["service"] for i in configured["issues"]} == {"ida-auth"}

        found = engine.trace(cfg, "TXN10042", loaded.start_ns, loaded.end_ns, events=loaded.current)
        assert found["count"] == 2
        assert found["services"] == ["ida-auth", "keymanager"]
        missed = engine.trace(cfg, "TXN-NOT-HERE", loaded.start_ns, loaded.end_ns, events=loaded.current)
        assert missed["count"] == 0


def test_cli_uses_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        assert main(["scan", "--no-download-traces", "--out", tmp]) == 1
        save(tmp, 10, 20, "24h", "q", [], [_ev(1_000_000_000_000, "resident", "resident", "connection refused")], [])
        cfg = Path(tmp) / "cfg.yaml"
        cfg.write_text("k8s:\n  enabled: false\nloki:\n  url: http://127.0.0.1:1\n", encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(["scan", "-c", str(cfg), "--no-download-traces", "--out", tmp, "--json"])
        assert code in (0, 2)
        json.loads(buf.getvalue())
        text = (Path(tmp) / "roottrace-report.html").read_text(encoding="utf-8")
        assert "from saved traces" in text
        assert "connection refused" in text


def test_publish_is_one_generation():
    cur = [_ev(1_000_000_000_000, "ida", "ida-auth", "sign failed")]
    with tempfile.TemporaryDirectory() as tmp:
        save(tmp, 10, 20, "24h", "q", [], cur, [])
        dest = Path(tmp) / "traces"
        stamp = json.loads((dest / "LATEST").read_text(encoding="utf-8"))["generation"]
        published = dest / "generations" / stamp
        assert (published / "current.jsonl").is_file()
        assert (published / "baseline.jsonl").is_file()
        half = dest / "generations" / "99990101T000000000000Z"
        half.mkdir()
        (half / "current.jsonl").write_text('{"ts_ns": 1}\n', encoding="utf-8")
        assert load(tmp).current[0].message == "sign failed"
        (published / "baseline.jsonl").unlink()
        try:
            load(tmp)
        except FileNotFoundError:
            return
        raise AssertionError("a missing baseline was treated as an empty window")


def test_flat_layout_still_loads():
    cur = [_ev(1_000_000_000_000, "ida", "ida-auth", "sign failed")]
    with tempfile.TemporaryDirectory() as tmp:
        save(tmp, 10, 20, "24h", "q", [], cur, [])
        dest = Path(tmp) / "traces"
        stamp = json.loads((dest / "LATEST").read_text(encoding="utf-8"))["generation"]
        gen = dest / "generations" / stamp
        for name in ("meta.json", "current.jsonl", "baseline.jsonl"):
            (gen / name).replace(dest / name)
        (dest / "LATEST").unlink()
        assert load(tmp).current[0].message == "sign failed"


def main_tests():
    test_roundtrip_and_rescan()
    test_cli_uses_the_file()
    test_publish_is_one_generation()
    test_flat_layout_still_loads()
    print("TRACE FILE CHECKS PASSED")


if __name__ == "__main__":
    main_tests()
