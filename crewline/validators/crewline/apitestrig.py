"""Read-only model of an API TestRig module, built from the real files (no parallel schema).

Facts this relies on are recorded with evidence in knowledge/frameworks/apitestrig.md:
- a <test> in the Suite.xml points one script class at one YAML via the `ymlFile` parameter;
- a YAML file is `<RootKey>: {<caseName>: {fields...}}`;
- `uniqueIdentifier` is the stable case identity (unique module-wide, case-insensitive);
- a case whose name contains `_sid` stores `<caseName minus first "_" segment>_<idKeyName field>`,
  which later cases reference as `$ID:<key>$`.
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Case:
    name: str
    root: str
    yml: str          # path relative to resources root, forward slashes
    line: int
    fields: dict

    @property
    def uid(self) -> str | None:
        return self.fields.get("uniqueIdentifier")


@dataclass
class SuiteTest:
    name: str
    yml: str
    script_class: str
    params: dict = field(default_factory=dict)

    @property
    def id_key_names(self) -> list[str]:
        raw = self.params.get("idKeyName", "")
        return [k.strip() for k in raw.split(",") if k.strip()]


def parse_cases(text: str, yml: str) -> list[Case]:
    """Parse YAML text into cases, keeping the 1-based line of each case key."""
    if not text.strip():
        return []
    node = yaml.compose(text)
    data = yaml.safe_load(text) or {}
    cases = []
    if node is None or not hasattr(node, "value"):
        return cases
    for root_key, root_val in node.value:
        root = root_key.value
        if not hasattr(root_val, "value") or not isinstance(root_val.value, list):
            continue
        for case_key, _ in root_val.value:
            name = case_key.value
            fields = (data.get(root) or {}).get(name) or {}
            if not isinstance(fields, dict):     # e.g. a mis-indented field parsed as a case
                raise yaml.YAMLError(f"{yml}: '{root}.{name}' is not a testcase mapping (line {case_key.start_mark.line + 1})")
            cases.append(Case(name, root, yml, case_key.start_mark.line + 1, fields))
    return cases


class Module:
    def __init__(self, module_root: str | Path, profile: dict):
        self.root = Path(module_root).resolve()
        self.profile = profile
        self.resources = self.root / profile.get("resources_root", "src/main/resources")
        self.yaml_glob = profile.get("yaml_glob", "**/*.yml")
        self.exclude_dirs = set(profile.get("exclude_dirs", ["coverage", "config"]))

    # --- working tree ----------------------------------------------------
    def yaml_files(self) -> list[str]:
        out = []
        for p in sorted(self.resources.glob(self.yaml_glob)):
            rel = p.relative_to(self.resources).as_posix()
            if rel.split("/")[0] in self.exclude_dirs:
                continue
            out.append(rel)
        return out

    def read(self, rel: str) -> str:
        return (self.resources / rel).read_text(encoding="utf-8")

    @property
    def ignored(self) -> set[str]:
        return set(self.profile.get("ignore_yaml", []))

    def cases(self) -> list[Case]:
        """Parse every in-scope YAML. A file that doesn't parse is recorded in `parse_errors`
        (rel path -> message) instead of aborting, so callers decide BLOCK vs WARN."""
        self.parse_errors: dict[str, str] = {}
        out = []
        for rel in self.yaml_files():
            if rel in self.ignored:
                continue
            try:
                out.extend(parse_cases(self.read(rel), rel))
            except yaml.YAMLError as e:
                self.parse_errors[rel] = str(e).splitlines()[0]
        return out

    def suite_tests(self) -> list[SuiteTest]:
        tests = []
        for suite in self.profile.get("suite_files", []):
            tree = ET.parse(self.root / suite)
            for t in tree.getroot().iter("test"):
                params = {p.get("name"): p.get("value", "") for p in t.findall("parameter")}
                cls = t.find("./classes/class")
                tests.append(SuiteTest(t.get("name", ""), params.get("ymlFile", ""),
                                       cls.get("name", "") if cls is not None else "", params))
        return tests

    # --- git (base ref) --------------------------------------------------
    # Every git call runs from the repository top level, so pathspecs and output paths are both
    # top-level relative (ls-tree/diff resolve pathspecs against the working directory).
    def top(self) -> Path:
        if not hasattr(self, "_top"):
            out = subprocess.run(["git", "-C", str(self.root), "rev-parse", "--show-toplevel"], check=True,
                                 capture_output=True, text=True, encoding="utf-8").stdout
            self._top = Path(out.strip()).resolve()
        return self._top

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.top()), *args], check=True,
                              capture_output=True, text=True, encoding="utf-8").stdout

    def resources_git_prefix(self) -> str:
        return self.resources.relative_to(self.top()).as_posix()

    def base_yaml_files(self, base: str) -> list[str]:
        prefix = self.resources_git_prefix()
        names = self.git("ls-tree", "-r", "--name-only", base, "--", prefix).splitlines()
        out = []
        for n in names:
            rel = n[len(prefix) + 1:]
            if rel.endswith(".yml") and rel.split("/")[0] not in self.exclude_dirs:
                out.append(rel)
        return sorted(out)

    def read_base(self, base: str, rel: str) -> str:
        return self.git("show", f"{base}:{self.resources_git_prefix()}/{rel}")

    def base_cases(self, base: str) -> list[Case]:
        self.base_parse_errors: dict[str, str] = {}
        out = []
        for rel in self.base_yaml_files(base):
            if rel in self.ignored:
                continue
            try:
                out.extend(parse_cases(self.read_base(base, rel), rel))
            except yaml.YAMLError as e:
                self.base_parse_errors[rel] = str(e).splitlines()[0]
        return out

    def changed_paths(self, base: str) -> list[str]:
        """Paths (relative to resources root) that differ from base, incl. untracked files."""
        prefix = self.resources_git_prefix()
        changed = self.git("diff", "--name-only", base, "--", prefix).splitlines()
        changed += self.git("ls-files", "--others", "--exclude-standard", "--", prefix).splitlines()
        out = set()
        for c in changed:
            p = (self.top() / c).resolve()
            try:
                out.add(p.relative_to(self.resources).as_posix())
            except ValueError:
                continue
        return sorted(out)


def load_profile(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
