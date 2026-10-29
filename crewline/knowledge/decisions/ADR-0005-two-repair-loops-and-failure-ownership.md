# ADR-0005: Separate repair loops for test code and production code; route failures by ownership

- Status: Accepted (proposed by the assistant, 2026-10-28)

## Context
The SDET assistant escalated every APPLICATION failure, because it never owned production code. In the full SDLC the most
common failing test is one the task's own code broke. Treating it as a bug would file the agent's own defect; sharing one
counter would let three test-code attempts block a legitimate code fix (Blueprint v2.0 §9 asks for a separate policy).

## Decision
- New class `CODE_UNDER_CHANGE`: fails on the branch, passes (or is absent) on the base, failing path runs through the task's diff.
  It goes to the software-developer with its own counter `repair.dev_attempt_count` (max 3, `track: dev`).
- `AUTOMATION` keeps the SDET counter `repair.attempt_count` (max 3).
- `APPLICATION` now means a defect the task did not introduce: escalate with a bug draft (unchanged rule, narrower meaning).
- `SPECIFICATION` joins the forced-escalation list: an ambiguous expectation is the product owner's call.
- Evidence decides the class: run the failing test on the base commit.

## Consequences
Guards use `any_of`/`all_of`; MAN-003 checks both counters against the history.
