"""Decide the test-run scope a change needs (org rule: "full run or exact testcase, based on the change").

Compares the working tree with a reference commit (the last commit that passed a full regression):
  - TARGETED  only new cases were added to existing YAML (no existing case changed, no template, Java,
              pom, Suite.xml or properties change). Run the new cases plus their `$ID:` producers.
  - FULL      anything else: an existing case or expected result changed, a template/script/wiring/
              dependency changed, or a case was removed.

  SCOPE-001  required scope = FULL (reason listed)        INFO
  SCOPE-002  required scope = TARGETED (cases listed)     INFO
The result's `inputs.required_scope` and `inputs.run_cases` drive the SYSTEM_TEST_EXECUTION/QUALITY_GATE run; the gate evidence
must show a run of at least that scope.
"""
from __future__ import annotations

from .apitestrig import Module
from .result import INFO, Result
from .testcase import ID_TOKEN, sid_keys

TEST_DATA_SUFFIXES = (".yml",)


def run(module: Module, ref: str) -> Result:
    res = Result("test-scope", inputs={"module_root": str(module.root), "ref": ref})
    try:
        before = {(c.yml, c.name): c for c in module.base_cases(ref)}
        changed = module.changed_paths(ref)
        top_changed = module.git("diff", "--name-only", ref, "--").splitlines()
    except Exception as e:
        return Result.not_run("test-scope", f"cannot read ref '{ref}': {e}")
    after = {(c.yml, c.name): c for c in module.cases()}

    reasons = []
    outside = [p for p in top_changed if not p.startswith(module.resources_git_prefix() + "/")
               or p.endswith("config/prereg.properties")]
    if outside:
        reasons.append(f"non-resource files changed: {', '.join(outside[:5])}")
    non_yaml = [p for p in changed if not p.endswith(TEST_DATA_SUFFIXES) and not p.startswith("coverage/")]
    if non_yaml:
        reasons.append(f"templates/resources changed: {', '.join(non_yaml[:5])}")
    modified = [f"{k[0]}::{k[1]}" for k, c in after.items() if k in before and before[k].fields != c.fields]
    removed = [f"{k[0]}::{k[1]}" for k in before if k not in after]
    if modified:
        reasons.append(f"existing cases modified: {', '.join(modified[:5])}")
    if removed:
        reasons.append(f"cases removed: {', '.join(removed[:5])}")

    added = [c for k, c in after.items() if k not in before]
    if reasons or not added:
        res.inputs["required_scope"] = "FULL"
        res.add("SCOPE-001", INFO, "required scope FULL: " + ("; ".join(reasons) or "no added cases detected"))
    else:
        producers = sid_keys(module)
        by_name = {c.name: c for c in after.values()}
        run_cases = {c.uid for c in added if c.uid}
        for c in added:
            text = f"{c.fields.get('input', '')}{c.fields.get('output', '')}"
            for key in ID_TOKEN.findall(text):
                prod = producers.get(key, "").split("::")[-1]
                if prod in by_name and by_name[prod].uid:
                    run_cases.add(by_name[prod].uid)
            for dep in str(c.fields.get("additionalDependencies") or "").split(","):
                if dep.strip():
                    run_cases.add(dep.strip())
        res.inputs["required_scope"] = "TARGETED"
        res.inputs["run_cases"] = sorted(run_cases)
        res.add("SCOPE-002", INFO, f"required scope TARGETED: {len(added)} new case(s) + producers -> "
                                   f"{', '.join(sorted(run_cases))}")
    return res.finish()
