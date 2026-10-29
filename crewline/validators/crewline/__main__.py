"""crewline - deterministic validators for the Crewline.

Workflow
  python -m crewline discover      --repo <module repo> --module <name> [--out <dir>] [--force]   # module onboarding
  python -m crewline manifest     <task-manifest.json> [--to <STATE> [--apply --note <text>]]
  python -m crewline tools         [--only <capability>]
Development (any repository)
  python -m crewline run           --repo <dir> --out <record.json> [--report <path>] [--cwd <dir>] -- <command...>
  python -m crewline evidence      --record <record.json> --repo <dir>
  python -m crewline change-scope  --repo <dir> --base <ref> --manifest <task-manifest.json>
  python -m crewline test-integrity --repo <dir> --base <ref> [--approvals <yaml>] [--strict]
  python -m crewline migration     --repo <dir> --base <ref>
  python -m crewline trace         <task-manifest.json>
  python -m crewline diff-coverage --repo <dir> --base <ref> --jacoco <jacoco.xml|dir> [--threshold 80]
  python -m crewline usage         --manifest <m> (--mark "<step>" | --transcript <session.jsonl> [--out <json>])
  python -m crewline regression    --baseline <report|surefire dir> --candidate <report|surefire dir> [--allow-fail <id>]
Git / PR
  python -m crewline secrets       <path>... [--base-dir <dir>] [--no-gitleaks]
  python -m crewline dco           --repo <dir> --range <base>..<head>
  python -m crewline branch        --repo <dir> --upstream upstream/<branch> --base <sha> --story <KEY> [--allow <sha>] [--upstream-repo o/r --pr-repo o/r --pr-base <b>]
SDET (API TestRig)
  python -m crewline testcase      --module-root <api-test> [--profile <yaml>] [--base <ref>] [--scope all|changed]
                                    (profile default: <module repo>/.crewline/qa/profile.yaml)
  python -m crewline expected-diff --module-root <api-test> --profile <yaml> --base <ref> [--approvals <yaml>]
  python -m crewline scope         --module-root <api-test> --profile <yaml> --ref <last fully-regressed commit>
  python -m crewline coverage      --commons-dir <dir> --module-root <api-test> --module-code <CODE> [--offline]

Exit code 0 PASS, 1 FAIL, 2 NOT_RUN. Add --json for machine-readable output.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import (branch, change_scope, coverage, dco, diff_coverage, discover, evidence, expected_diff, manifest, migration, regression, scope,
               secrets_scan, test_integrity, testcase, tools, traceability, usage)
from .apitestrig import Module, load_profile
from .result import EXIT, Result


def module_profile(module_root: str, profile: str | None) -> str:
    """The module's own profile unless one is given: <repo top>/.crewline/qa/profile.yaml."""
    if profile:
        return profile
    import subprocess
    top = subprocess.run(["git", "-C", module_root, "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         encoding="utf-8").stdout.strip()
    path = Path(top or module_root) / ".crewline" / "qa" / "profile.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found: onboard the module (module-onboarding) or pass --profile")
    return str(path)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command: list[str] = []
    if "--" in argv:                          # `run ... -- <command>`: everything after -- is the command
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(prog="crewline", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def module_args(p):
        p.add_argument("--module-root", required=True)
        p.add_argument("--profile", help="default: <module repo>/.crewline/qa/profile.yaml")

    def repo_base(p):
        p.add_argument("--repo", required=True)
        p.add_argument("--base", required=True)

    p = sub.add_parser("testcase"); module_args(p)
    p.add_argument("--base"); p.add_argument("--scope", choices=["all", "changed"])
    p = sub.add_parser("expected-diff"); module_args(p)
    p.add_argument("--base", required=True); p.add_argument("--approvals")
    p = sub.add_parser("secrets")
    p.add_argument("paths", nargs="+"); p.add_argument("--base-dir", default="."); p.add_argument("--no-gitleaks", action="store_true")
    p = sub.add_parser("dco")
    p.add_argument("--repo", required=True); p.add_argument("--range", required=True)
    p = sub.add_parser("coverage")
    p.add_argument("--commons-dir", required=True); p.add_argument("--module-root", required=True)
    p.add_argument("--module-code", required=True); p.add_argument("--offline", action="store_true")
    p = sub.add_parser("branch")
    p.add_argument("--repo", required=True); p.add_argument("--upstream", required=True, help="e.g. upstream/develop")
    p.add_argument("--base", required=True, help="upstream base commit recorded at REPO_READY")
    p.add_argument("--story", required=True); p.add_argument("--allow", action="append", default=[])
    p.add_argument("--upstream-repo"); p.add_argument("--pr-repo"); p.add_argument("--pr-base")
    p = sub.add_parser("tools"); p.add_argument("--only", action="append", default=[])
    p = sub.add_parser("scope"); module_args(p)
    p.add_argument("--ref", required=True, help="last commit that passed a full regression")
    p = sub.add_parser("regression")
    p.add_argument("--baseline", required=True, help="TestRig full-report / surefire dir of the base run")
    p.add_argument("--candidate", required=True, help="same, for the branch run")
    p.add_argument("--allow-fail", action="append", default=[], help="test id with an attributed gate exception")
    p = sub.add_parser("run")
    p.add_argument("--repo", required=True); p.add_argument("--out", required=True)
    p.add_argument("--report"); p.add_argument("--cwd")
    p = sub.add_parser("evidence")
    p.add_argument("--record", required=True); p.add_argument("--repo", required=True)
    p = sub.add_parser("change-scope"); repo_base(p); p.add_argument("--manifest", required=True)
    p = sub.add_parser("test-integrity"); repo_base(p)
    p.add_argument("--approvals"); p.add_argument("--strict", action="store_true")
    p = sub.add_parser("migration"); repo_base(p)
    p = sub.add_parser("trace"); p.add_argument("manifest")
    p = sub.add_parser("discover")
    p.add_argument("--repo", required=True); p.add_argument("--module", required=True)
    p.add_argument("--out"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("diff-coverage"); repo_base(p)
    p.add_argument("--jacoco", required=True, help="jacoco.xml or a directory searched for jacoco.xml")
    p.add_argument("--threshold", type=float, default=80.0); p.add_argument("--include", default="*src/main/java/*.java")
    p = sub.add_parser("usage")
    p.add_argument("--manifest", required=True); p.add_argument("--mark", help="start a named step now")
    p.add_argument("--transcript", action="append", default=[]); p.add_argument("--out")
    p = sub.add_parser("manifest")
    p.add_argument("manifest"); p.add_argument("--to")
    p.add_argument("--apply", action="store_true", help="record the transition if every guard passes")
    p.add_argument("--note", default="")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "testcase":
            case_scope = a.scope or ("changed" if a.base else "all")
            res = testcase.run(Module(a.module_root, load_profile(module_profile(a.module_root, a.profile))), case_scope, a.base)
        elif a.cmd == "expected-diff":
            res = expected_diff.run(Module(a.module_root, load_profile(module_profile(a.module_root, a.profile))), a.base, a.approvals)
        elif a.cmd == "secrets":
            res = secrets_scan.run(a.paths, a.base_dir, not a.no_gitleaks)
        elif a.cmd == "dco":
            res = dco.run(a.repo, a.range)
        elif a.cmd == "branch":
            res = branch.run(a.repo, a.upstream, a.base, a.story, a.allow, a.pr_repo, a.pr_base, a.upstream_repo)
        elif a.cmd == "tools":
            res = tools.run(a.only)
        elif a.cmd == "scope":
            res = scope.run(Module(a.module_root, load_profile(module_profile(a.module_root, a.profile))), a.ref)
        elif a.cmd == "regression":
            res = regression.run(a.baseline, a.candidate, a.allow_fail)
        elif a.cmd == "coverage":
            res = coverage.run(a.commons_dir, a.module_root, a.module_code, a.offline)
        elif a.cmd == "run":
            res = evidence.capture(a.repo, a.out, command, a.report, a.cwd)
        elif a.cmd == "evidence":
            res = evidence.run(a.record, a.repo)
        elif a.cmd == "change-scope":
            res = change_scope.run(a.repo, a.base, a.manifest)
        elif a.cmd == "test-integrity":
            res = test_integrity.run(a.repo, a.base, a.approvals, a.strict)
        elif a.cmd == "migration":
            res = migration.run(a.repo, a.base)
        elif a.cmd == "trace":
            res = traceability.run(a.manifest)
        elif a.cmd == "discover":
            res = discover.run(a.repo, a.module, a.out, a.force)
        elif a.cmd == "diff-coverage":
            res = diff_coverage.run(a.repo, a.base, a.jacoco, a.threshold, a.include)
        elif a.cmd == "usage":
            res = usage.mark(a.manifest, a.mark) if a.mark else usage.report(a.manifest, a.transcript, a.out)
        else:
            if a.to and a.apply:
                res = manifest.apply(a.manifest, a.to, a.note)
            else:
                res = manifest.transition(a.manifest, a.to) if a.to else manifest.check(a.manifest)
    except Exception as e:  # a validator that crashes must never read as PASS
        res = Result.not_run(a.cmd, f"{type(e).__name__}: {e}")

    out = res.to_json() if a.json else res.to_text()
    sys.stdout.buffer.write((out + "\n").encode("utf-8"))
    return EXIT[res.status]


if __name__ == "__main__":
    sys.exit(main())
