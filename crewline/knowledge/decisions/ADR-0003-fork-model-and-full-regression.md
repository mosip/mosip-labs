# ADR-0003: Fork model for every change; full-suite regression before commit

- Status: **Accepted** (2026-10-28, user decision; enforced in core/workflow.yaml).
- Context: PILOT-001's first branch was cut from local `develop`, 18 commits ahead of the fork's develop and 18 behind
  `mosip/develop`. Its PR carried 19 commits, failed DCO on two other authors' commits and conflicted on `pom.xml`.
  Separately, the pilot had only ever run the touched cases, so nobody could say whether the change broke anything else.
- Decision:
  1. **Fork model.** Ask the user which upstream branch to base on **before** creating a branch (approval `base_branch`).
     Cut the branch from that upstream ref exactly; commit only the task's changes; nothing origin/local-only unless the user
     names it; push to `origin`; PR against the upstream branch. Gate `branch_scope` (`sdetval branch`: BR-001..005) on S17→S18.
  2. **Targeted runs while iterating, full suite before commit.** Gate `full_regression` (`sdetval regression`) on S16→S17:
     full suite on the base and on the branch, same env, sequentially; block on pass→fail and on failing new cases without an
     attributed exception.
  3. **Approvals are single-use.** A guarded transition consumes the approval it used (`consumed_by`), so an approval for one
     target (e.g. a fork PR) can't authorise another (an upstream PR).
- Consequences: two full runs per change (~10 min each on released for prereg, 381+ cases). Upstream branches may lack
  fork-only tooling (prereg: no coverage matrix), so validators must cover rules CoverageCli normally enforces (NAME-004
  duplicate IDs) and tolerate unrelated broken files (YAML-PARSE WARN).
