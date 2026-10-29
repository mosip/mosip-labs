# ADR-0004: One orchestrator, one state machine, a template per task type

- Status: Accepted (proposed by the assistant, 2026-10-28; to be confirmed by the team)
- Supersedes nothing; extends ADR-0001..0003 from the SDET Architect Assistant.

## Context
The full-SDLC plan (Option A) requires one orchestrator that owns state, permissions, evidence, retries and final status, with
specialists that never run their own workflow. Task types differ (an incident must never edit code; a release has no
implementation; a refactor must not change tests) but a separate state machine per type would be a second orchestrator.

## Decision
`core/workflow.yaml` is the single graph, its states declared in main-line order. `core/workflows/<task_type>.yaml` projects it:
`path` lists the states the type walks; an edge into a skipped state collapses forward along the main line; loop-backs into a
skipped state are dropped; template `entry_guards` add to the core ones; `required_gates` must pass before COMMIT_PR and SUCCESS.
Gates owned by a skipped state are not applicable automatically. `crewline manifest` enforces all of it.

## Consequences
- The SDET path proven in PILOT-001 is the `test-automation` template; its tests run unchanged against the new graph.
- Adding a task type is a YAML file plus tests, not code.
- Mixed requests take the stricter template or are split into linked tasks.
