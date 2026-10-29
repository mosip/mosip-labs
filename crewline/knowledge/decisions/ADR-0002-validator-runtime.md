# ADR-0002: Validators are a small Python package (`validators/sdetval`)

- Status: Proposed (2026-10-27).
- Context: validators must run locally (Windows/Git Bash), in CI and from any AI adapter, and return machine-readable results.
  The team's tooling is Java (CoverageCli). Python 3 + PyYAML is already on the dev machines (Anaconda).
- Decision: keep the assistant's own validators in Python (stdlib + PyYAML, optional `jsonschema`, optional `gitleaks`),
  with the CLI contract `python -m sdetval <validator> … [--json]` and exit codes 0 PASS / 1 FAIL / 2 NOT_RUN.
- Alternatives: port into apitest-commons as Java (best long-term fit for the testrig repos; a candidate once the rules settle);
  shell scripts (not portable on Windows).
- Consequences: CI for consuming repos would need Python. Until that is approved, validators run in the assistant's S11 state and on demand.
- Deviation from Blueprint §2 layout: validator code lives in `validators/sdetval/` with per-module rules in
  per-module profiles (now `<module repo>/.crewline/qa/profile.yaml`, see README section 14), instead of one folder per validator. Same responsibilities, fewer moving parts.
