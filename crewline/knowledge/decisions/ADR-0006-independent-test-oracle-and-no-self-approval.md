# ADR-0006: Tests come from the ACs before the code; authors never review or approve

- Status: Accepted (proposed by the assistant, 2026-10-28)

## Context
When the same model writes the code and the tests from the code, the tests confirm the implementation instead of the
requirement, and a reviewer sharing the author's context inherits its blind spots. PILOT-001 showed the value of a genuinely
fresh review (Review 2 found R2-1, a result-template gap Review 1 missed).

## Decision
- TESTCASE_DESIGN precedes IMPLEMENTATION_PLAN for feature, bug-fix and database-migration; the SDET designs from the ACs and the
  approved design only. The developer adds unit tests but may not rewrite agreed acceptance tests (test-integrity, expected-diff).
- Bug fixes start with a reproduction that fails on the base (`reproduction` gate).
- `implementation.authors` and `reviews.reviewers` are recorded per context; MAN-011 blocks author = reviewer and review 1 = review 2.
- Approvals are human: MAN-010 blocks an approval whose approver is an agent.
