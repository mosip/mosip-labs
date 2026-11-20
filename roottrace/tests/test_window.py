"""A window longer than six hours is queried in slices, and a slice that stops early is reported."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fake_loki import FakeLoki  # noqa: E402

from roottrace import engine  # noqa: E402
from roottrace.config import Config  # noqa: E402


def test_slices():
    assert len(engine._slices(0, engine._SLICE_NS)) == 1
    parts = engine._slices(0, engine._SLICE_NS + 1)
    assert len(parts) == 2 and parts[0][1] == engine._SLICE_NS and parts[1][1] == engine._SLICE_NS + 1


def test_long_window_is_split():
    now = time.time_ns()
    row = (now - 1_000_000_000, {"namespace": "ida", "app": "ida-auth", "container": "ida-auth", "pod": "p"},
           "2026-11-19 10:00:00 ERROR something failed")
    fake = FakeLoki([row])
    url = fake.start()
    try:
        cfg = Config()
        cfg.loki.url = url
        cfg.k8s.enabled = False
        result = engine.scan(cfg, now - 7 * 3600 * 10**9, now)
    finally:
        fake.stop()
    assert len(fake.ranges) == 4, fake.ranges          # current and baseline, two slices each
    assert result["coverage"] == []
    assert result["issues"]


def test_cap_is_partial():
    now = time.time_ns()
    labels = {"namespace": "ida", "app": "ida-auth", "container": "ida-auth", "pod": "p"}
    rows = [(now - (i + 1) * 1_000_000_000, labels, f"2026-11-19 10:00:0{i} ERROR failed {i}") for i in range(3)]
    fake = FakeLoki(rows)
    url = fake.start()
    try:
        cfg = Config()
        cfg.loki.url = url
        cfg.loki.max_lines = 1
        cfg.k8s.enabled = False
        result = engine.scan(cfg, now - 3600 * 10**9, now)
    finally:
        fake.stop()
    assert any(g["which"] == "current" and g["reason"] == "stopped at max_lines" for g in result["coverage"])


def test_timeout_is_split_and_reported():
    class Boom:
        truncated = False

        def __init__(self):
            self.calls = []

        def query_range(self, query, start, end):
            self.calls.append(end - start)
            raise RuntimeError("timeout")

    boom = Boom()
    events, partial = engine._pull(boom, "q", 0, 2 * engine._MIN_NS + 10, Config(), "current")
    assert events == []
    assert partial and all(p["reason"] == "Loki did not answer" for p in partial)
    assert boom.calls and min(boom.calls) <= engine._MIN_NS


def test_stack_crosses_a_slice():
    from roottrace.loki import LogEntry
    labels = {"namespace": "ida", "app": "ida-auth", "pod": "p"}

    class Split:
        truncated = False

        def query_range(self, query, start, end):
            if end <= engine._SLICE_NS:
                return [LogEntry(100, labels, "2026-11-19 10:00:00 ERROR sign failed")]
            return [LogEntry(200, labels, "Caused by: java.lang.NullPointerException: boom")]

    events, partial = engine._pull(Split(), "q", 0, engine._SLICE_NS + 1, Config(), "current")
    assert partial == []
    assert len(events) == 1, events
    assert events[0].root_cause and "NullPointerException" in events[0].root_cause


def test_unread_window_is_incomplete():
    class Dead:
        truncated = False

        def __init__(self, cfg):
            pass

        def query_range(self, *a, **k):
            raise RuntimeError("timeout")

        def instant_vector(self, *a, **k):
            raise RuntimeError("timeout")

    orig = engine.LokiClient
    engine.LokiClient = Dead
    try:
        cfg = Config()
        cfg.k8s.enabled = False
        now = time.time_ns()
        result = engine.scan(cfg, now - 3600 * 10**9, now)
    finally:
        engine.LokiClient = orig
    assert result["verdict"].startswith("Incomplete")
    assert result["critical"]
    assert result["coverage"]


def main():
    test_slices()
    test_long_window_is_split()
    test_cap_is_partial()
    test_timeout_is_split_and_reported()
    test_stack_crosses_a_slice()
    test_unread_window_is_incomplete()
    print("WINDOW CHECKS PASSED")


if __name__ == "__main__":
    main()
