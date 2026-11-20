"""Git commit and Java package prefix of a running MOSIP service.

The pod spec only has an image tag. The commit and the package prefix are inside
the service jar, in one of:

  BOOT-INF/classes/service-git.properties
  BOOT-INF/classes/git.properties

and in META-INF/build-info.properties (build.group, build.artifact, build.version).

This module only parses those files and maps a Java package onto a source repo.
It does not open a cluster or a jar; callers hand it the file text.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

# Spring Boot fat-jar paths, preferred order. service-git.properties is the MOSIP convention.
GIT_ENTRIES = (
    "BOOT-INF/classes/service-git.properties",
    "BOOT-INF/classes/git.properties",
)
BUILD_ENTRY = "META-INF/build-info.properties"


def unescape(value: str) -> str:
    """Java .properties escapes with a backslash. Keep the character after the slash and drop the slash."""
    out = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            out.append(value[i + 1])           # \: \= \\ and unicode-ish single chars
            i += 2
        else:
            out.append(value[i])
            i += 1
    return "".join(out)


def parse_properties(text: str) -> dict[str, str]:
    """Read a .properties file, or a JSON object some build plugins emit instead of properties."""
    raw_text = (text or "").strip()
    if raw_text.startswith("{"):
        data = json.loads(raw_text)
        return {str(k): str(v) for k, v in data.items()}
    found: dict[str, str] = {}
    for raw in raw_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue                                    # blank line or comment
        sep = "=" if "=" in line else ":" if ":" in line else ""
        if not sep:
            continue                                    # a line with no separator is not a property
        key, value = line.split(sep, 1)                 # split once; values may contain '=' or ':'
        found[unescape(key.strip())] = unescape(value.strip())
    return found


def pick_git_entry(names: list[str]) -> str | None:
    """Which jar entry to read for the commit. service-git.properties wins over git.properties."""
    have = set(names)
    for entry in GIT_ENTRIES:
        if entry in have:
            return entry
    return None


@dataclass
class Revision:
    commit: str | None = None
    commit_abbrev: str | None = None
    version: str | None = None
    group: str | None = None            # Maven groupId, from build-info
    artifact: str | None = None         # Maven artifactId

    def to_dict(self) -> dict:
        return {
            "commit": self.commit, "commit_abbrev": self.commit_abbrev,
            "version": self.version, "group": self.group, "artifact": self.artifact,
        }


def load_sources() -> list[dict]:
    """The packaged sources.yaml: Java package prefix -> git repo. Used to label a throw site."""
    import yaml
    from importlib import resources
    text = resources.files("roottrace").joinpath("sources.yaml").read_text(encoding="utf-8")
    return list((yaml.safe_load(text) or {}).get("sources") or [])


def repo_for(package: str, sources: list[dict]) -> dict | None:
    """Longest package-prefix match. A broader prefix must not hide a more specific one.

    io.mosip.kernel matches kernel, but io.mosip.kernel.auth must match the auth row when both exist.
    """
    best = None
    best_len = -1
    for row in sources:
        prefix = row.get("prefix") or ""
        if prefix and (package == prefix or package.startswith(prefix + ".")) and len(prefix) > best_len:
            best = row
            best_len = len(prefix)
    return best


def revision_from(git_text: str, build_text: str) -> Revision:
    """Combine git.properties and build-info.properties into one revision. Missing keys stay None."""
    git = parse_properties(git_text)
    build = parse_properties(build_text)
    return Revision(
        commit=git.get("git.commit.id.full"),
        commit_abbrev=git.get("git.commit.id.abbrev"),
        version=build.get("build.version") or git.get("git.build.version"),
        group=build.get("build.group"),
        artifact=build.get("build.artifact"),
    )
