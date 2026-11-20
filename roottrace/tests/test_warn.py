"""A scan keeps WARN lines beside ERROR lines, and can opt out."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fake_loki import FakeLoki  # noqa: E402

from roottrace import engine  # noqa: E402
from roottrace.config import Config  # noqa: E402


def spring(level, msg):
    return f"2026-11-19 10:00:00.000 {level} 1 --- [nio-8090-exec-3] i.m.a.AuthService : {msg}"


def scan(include_warn):
    now = time.time_ns()
    labels = {"namespace": "ida", "app": "ida-auth", "pod": "ida-auth-0", "container": "ida-auth"}
    rows = [
        (now - 2_000_000_000, labels, spring("WARN", "OTP retry scheduled transactionId=TXN42")),
        (now - 1_000_000_000, labels, spring("ERROR", "IDA-MLC-019 sign failed")),
        (now - 500_000_000, labels, spring("INFO", "request processed ok")),
    ]
    fake = FakeLoki(rows)
    url = fake.start()
    try:
        cfg = Config()
        cfg.loki.url = url
        cfg.k8s.enabled = False
        cfg.include_warn = include_warn
        return engine.scan(cfg, now - 3600 * 10**9, now)
    finally:
        fake.stop()


def main():
    cfg = Config()
    assert cfg.include_warn is True
    filt = engine.line_filter(cfg)
    assert "warn" in filt and "error" in filt, filt
    assert "warn" not in engine.line_filter(Config(include_warn=False))

    with_warn = scan(True)
    levels = {i["level"] for i in with_warn["issues"]}
    assert "WARN" in levels and "ERROR" in levels, with_warn["issues"]
    assert all("request processed" not in i["template"] for i in with_warn["issues"])

    errors_only = scan(False)
    assert all(i["level"] != "WARN" for i in errors_only["issues"]), errors_only["issues"]
    assert any(i["level"] == "ERROR" for i in errors_only["issues"])

    print("WARN CHECKS PASSED")


if __name__ == "__main__":
    main()
