# ADR-0001: The coverage matrix is the traceability artifact; CoverageCli is the testcase validator

- Status: Proposed (2026-10-27). Needs SDET lead approval.
- Context: Plan §23.3 / Blueprint §6 call for a "companion traceability artifact" and validators for YAML structure, naming,
  duplicate IDs and AC traceability. Phase 0 found that the team already has this: per-module coverage matrices
  (one Markdown file per subject, rows keyed by `uniqueIdentifier`, `Story` column per row) and `CoverageCli`
  (`scaffold`/`sync`/`rollup`/`check`, 31 gap types) gating PRs in CI. Pre-registration is fully migrated and green.
- Decision:
  1. The assistant writes scenarios as matrix rows (`🟡 not_automated` first), automates them, then flips them to `✅ automated`. It follows each module's `coverage/AGENTS.md` verbatim.
  2. `CoverageCli check` is the authoritative check for everything it covers. `sdetval coverage` only runs and normalises it.
  3. New validators (`sdetval`) cover only what CoverageCli does not: `$ID:` chain resolution, naming profile, expected-result history diff, secrets, DCO and workflow/repair-cap enforcement.
  4. AC-level granularity (finer than the Story key) is recorded in the task manifest (`requirements.acceptance_criteria[].matrix_row_ids`). The matrix format is not extended.
- Consequences: no parallel schema; the assistant's output is indistinguishable from a careful engineer's. If AC-level traceability must be committed to the repo, that is a change to the matrix design owned by the commons maintainers (a proposal, not a fork).
