# Workflow templates

One file per `task_type` (core/workflow.yaml `task_types`). Each template is a projection of the single state
machine, never a second orchestrator:

- `path`: the states this task type walks, in graph order. Edges into a state that is not on the path collapse
  forward to the next state that is; loop-backs into a skipped state are dropped (`crewline manifest`).
- `entry_guards`: extra guards, added to core/workflow.yaml's for the same state.
- `required_gates`: gates that must be PASS (or carry an attributed exception) before QUALITY_GATE passes and
  before the outcome can be SUCCESS (MAN-012). Gates of skipped states are NOT_APPLICABLE with the template as rationale.
- `risk_tier`: the default autonomy level (core/permissions.yaml `tiers`); the orchestrator may raise it, never lower it (MAN-013).
