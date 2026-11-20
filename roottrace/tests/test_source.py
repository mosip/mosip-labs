"""Snippets are copied from a file at a commit. Catalog rows name a class only when the frame matches."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from roottrace.catalog import Catalog  # noqa: E402
from roottrace.miner import Issue  # noqa: E402
from roottrace.source import attach_snippets, java_relpath, lines_around, path_for  # noqa: E402


def test_lines():
    text = "\n".join(f"line {n}" for n in range(1, 11))
    snip = lines_around(text, 8, radius=1)
    assert [row["text"] for row in snip["lines"]] == ["line 7", "line 8", "line 9"]
    assert [row["hit"] for row in snip["lines"]] == [False, True, False]
    assert lines_around(text, 11) is None
    assert lines_around(text, 0) is None


def test_path():
    assert java_relpath("io.mosip.foo.Bar$Inner", "Bar.java") == "io/mosip/foo/Bar.java"
    paths = [
        "other/src/main/java/io/mosip/kernel/core/util/DateUtils.java",
        "kernel-core/src/main/java/io/mosip/kernel/core/util/DateUtils.java",
    ]
    found = path_for(paths, "io.mosip.kernel.core.util.DateUtils", "DateUtils.java")
    assert found.endswith("kernel-core/src/main/java/io/mosip/kernel/core/util/DateUtils.java") or found.endswith(
        "other/src/main/java/io/mosip/kernel/core/util/DateUtils.java")
    assert path_for(paths, "io.mosip.missing.Nope", "Nope.java") is None


def test_attach_uses_pod_commit():
    calls = []

    def fetch(repo, commit, class_name, line, file_name):
        calls.append(commit)
        return {"snippet": {"line": line, "lines": [{"n": line, "text": "return id;", "hit": True}]}, "commit": commit}

    hit = {"score": 9, "pods": ["auth-0"], "code": {
        "class": "io.mosip.authentication.service.AuthService", "file": "AuthService.java",
        "line": 210, "repo": "https://github.com/mosip/id-authentication"}}
    attach_snippets([hit], [{"pod": "auth-0", "revision": {"commit": "fa3d713f2de9"}}], fetch=fetch)
    assert calls == ["fa3d713f2de9"]
    assert hit["code"]["snippet"]["lines"][0]["text"] == "return id;"

    missed = {"score": 1, "pods": ["other-0"], "code": {"class": "io.mosip.a.A", "line": 1,
                                                        "repo": "https://github.com/mosip/x"}}
    attach_snippets([missed], [], fetch=fetch)
    assert calls == ["fa3d713f2de9"]
    assert missed["code"]["snippet_note"] == "running commit was not read from the pod"


def test_catalog_certainty(tmp_path=None):
    path = Path(__file__).parent / "_catalog_certainty.yaml"
    path.write_text("""
issues:
  - id: LEAD-1
    title: message only
    severity: high
    match: {regex: "connection refused"}
    cause: the message matched
    fix: check the dependency
  - id: CONF-1
    title: this method
    severity: high
    match: {regex: "connection refused", class: io.mosip.foo.Bar, method: run}
    cause: Bar.run is on the frame
    fix: the change is in Bar.run
""", encoding="utf-8")
    try:
        cat = Catalog([str(path)])
        matched = Issue(key="n/s#1", namespace="n", service="svc", template="connection refused", level="ERROR")
        matched.code = {"class": "io.mosip.foo.Bar", "method": "run", "file": "Bar.java", "line": 4}
        other = Issue(key="n/s#2", namespace="n", service="svc", template="connection refused", level="ERROR")
        other.code = {"class": "io.mosip.other.Thing", "method": "run", "file": "Thing.java", "line": 4}
        cat.apply([matched, other])
    finally:
        path.unlink(missing_ok=True)
    by_id = {k["id"]: k for k in matched.known}
    assert by_id["LEAD-1"]["certainty"] == "lead"
    assert by_id["CONF-1"]["certainty"] == "confirmed"
    assert by_id["CONF-1"]["fix"] == "the change is in Bar.run"
    assert all(k["id"] != "CONF-1" for k in other.known)


def main():
    test_lines()
    test_path()
    test_attach_uses_pod_commit()
    test_catalog_certainty()
    print("SOURCE CHECKS PASSED")


if __name__ == "__main__":
    main()
