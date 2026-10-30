# Crewline changelog

Every change that ships to users raises the version in `.claude-plugin/plugin.json` and `VERSION` (CI: `crewline version`),
because Claude Code updates an installed plugin only when that version changes. A task records the version it started on
(`crewline_version`); when a session runs a newer Crewline, the agents read the entries in between.

- **PATCH**: a fix; no rule or gate becomes stricter.
- **MINOR**: a new or stricter rule, gate, validator or agent. Tasks in progress continue; the agent tells the user what
  changed for them.
- **MAJOR**: a change that can break a task in progress (state machine, manifest schema). Finish or restart open tasks.

## 0.2.0
First plugin release.
- Claude Code plugin with per-module opt-in (`.claude/settings.json`), active only in repositories with `.crewline/`.
- Guard rails in the plugin hooks (ADR-0007): commit / push / PR only after the gates pass; Bash and PowerShell.
- Task records in `<clone>/.crewline-work/tasks/`; each task records `crewline_version` (MAN-016 warns on drift).
- `discover`: long Windows paths, no local paths in drafts, `testcase_rules.id_key_from_input`.
