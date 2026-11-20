"""Correlated errors render as a stack: this error, then the earlier ones under Caused by."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from roottrace.report import attach_stacks  # noqa: E402


def test_transaction_stack():
    later = {
        "service": "ida-auth", "namespace": "ida", "level": "ERROR", "template": "sign failed",
        "count": 2, "first_ns": 200, "score": 10, "trace_ids": ["TXN10042"],
        "code": {"class": "io.mosip.authentication.service.AuthService", "method": "authenticate",
                 "file": "AuthService.java", "line": 210},
    }
    earlier = {
        "service": "keymanager", "namespace": "keymanager", "level": "ERROR", "template": "KER-KMS-012 failed",
        "count": 2, "first_ns": 100, "score": 20, "trace_ids": ["TXN10042"],
        "code": {"class": "io.mosip.kernel.keymanager.Key", "method": "create", "file": "Key.java", "line": 40},
    }
    attach_stacks([later, earlier], [])
    assert [f["service"] for f in later["stack"]] == ["ida-auth", "keymanager"]
    assert later["via"] == "same transaction"
    assert later["stack"][0]["at"] == "io.mosip.authentication.service.AuthService.authenticate(AuthService.java:210)"
    assert later["stack"][1]["at"].endswith("Key.create(Key.java:40)")
    assert [f["service"] for f in earlier["stack"]] == ["keymanager"]
    assert earlier["via"] == ""


def test_failure_stack():
    iss = {
        "service": "resident", "namespace": "resident", "level": "ERROR",
        "template": "connection timed out", "count": 4, "first_ns": 5, "score": 3, "trace_ids": [],
    }
    chains = [{
        "root": "postgres", "status": "down", "status_label": "Down",
        "why": "postgres is crash-looping", "code": None,
        "impacted": [{"component": "resident", "children": []}],
    }]
    attach_stacks([iss], chains)
    assert [f["service"] for f in iss["stack"]] == ["resident", "postgres"]
    assert iss["via"] == "same failure"
    assert "crash-looping" in iss["stack"][1]["message"]
    assert [f["service"] for f in chains[0]["stack"]] == ["resident", "postgres"]


def test_time_stack():
    """A callee that failed within a few seconds is the cause. The same second with no call is not."""
    resident = {
        "service": "resident", "component": "resident", "namespace": "resident", "level": "ERROR",
        "template": "connection refused", "count": 4, "first_ns": 10_000_000_000, "score": 3,
        "trace_ids": [], "marks": [10_000_000_000],
    }
    keymanager = {
        "service": "keymanager", "component": "keymanager", "namespace": "keymanager", "level": "ERROR",
        "template": "KER-KMS-012 failed", "count": 2, "first_ns": 9_600_000_000, "score": 8,
        "trace_ids": [], "marks": [9_600_000_000],
    }
    activemq = {
        "service": "activemq", "component": "activemq", "namespace": "activemq", "level": "ERROR",
        "template": "broker down", "count": 1, "first_ns": 9_400_000_000, "score": 9,
        "trace_ids": [], "marks": [9_400_000_000],
    }
    printsvc = {
        "service": "print", "component": "print", "namespace": "print", "level": "ERROR",
        "template": "printer jammed", "count": 1, "first_ns": 9_800_000_000, "score": 1,
        "trace_ids": [], "marks": [9_800_000_000],
    }
    calls = {"resident": {"keymanager"}, "keymanager": {"activemq"}}
    attach_stacks([resident, keymanager, activemq, printsvc], [], calls)
    assert [f["service"] for f in resident["stack"]] == ["resident", "keymanager", "activemq"]
    assert resident["stack"][1]["gap"] == "400ms earlier"
    assert resident["stack"][2]["gap"] == "200ms earlier"
    assert resident["via"] == "400ms earlier"
    assert "print" not in [f["service"] for f in resident["stack"]]
    assert [f["service"] for f in keymanager["stack"]] == ["keymanager", "activemq"]
    assert [f["service"] for f in activemq["stack"]] == ["activemq"]


def test_time_too_far_falls_back_to_root():
    resident = {
        "service": "resident", "component": "resident", "namespace": "resident", "level": "ERROR",
        "template": "connection timed out", "count": 4, "first_ns": 200_000_000_000, "score": 3,
        "trace_ids": [], "marks": [200_000_000_000],
    }
    keymanager = {
        "service": "keymanager", "component": "keymanager", "namespace": "keymanager", "level": "ERROR",
        "template": "KER-KMS-012 failed", "count": 2, "first_ns": 1_000_000_000, "score": 8,
        "trace_ids": [], "marks": [1_000_000_000],
    }
    chains = [{
        "root": "postgres", "status": "down", "status_label": "Down",
        "why": "postgres is crash-looping", "code": None,
        "impacted": [{"component": "resident", "children": []}],
    }]
    attach_stacks([resident, keymanager], chains, {"resident": {"keymanager"}})
    assert [f["service"] for f in resident["stack"]] == ["resident", "postgres"]
    assert resident["via"] == "same failure"


def main():
    test_transaction_stack()
    test_failure_stack()
    test_time_stack()
    test_time_too_far_falls_back_to_root()
    print("STACK CHECKS PASSED")


if __name__ == "__main__":
    main()
