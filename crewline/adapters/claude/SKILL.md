---
name: crewline
description: "Use for MOSIP engineering work across the SDLC: features, bug fixes, refactors, dependency upgrades, DB migrations, incidents, release readiness, and API/UI test automation. Classifies the task, drives one gated workflow (requirements -> design -> tests from ACs -> code -> reviews -> system tests -> signed-off PR to upstream -> release readiness) with deterministic validators and human approvals."
---

# Crewline (Claude Code adapter)

Core: `{{CORE}}`. This file is a thin adapter. The workflow, templates, gates, permissions and agent contracts live in the core.

## How to run a task

1. Read `{{CORE}}/core/principles.md`, then the target repository's `.crewline/development/local-context.md` (staging copy:
   `<module repo>/.crewline/development/`) and, for test work, `.crewline/qa/module-context.md`, `coverage/README.md`,
   `coverage/AGENTS.md`. Repository guidance wins where it is more specific.
2. INTAKE: classify the request into one task type (`{{CORE}}/core/workflows/`: feature, bug-fix, refactor,
   dependency-upgrade, database-migration, incident, release, test-automation) and its risk tier. Create the task manifest
   (`{{CORE}}/templates/task-manifest.schema.json`) in the task workspace `{{CORE}}/tasks/<id>/`, never in a repository.
3. S0_BOOTSTRAP_CHECK: `python -m crewline tools` (from `{{CORE}}/validators`) plus any connector/browser the task type needs.
   Missing -> stop and give the user the numbered steps from `{{CORE}}/core/tools.yaml`; never work around it.
   An action the platform refuses at runtime (e.g. `npm ci`) -> stop and offer the `permission_gated` options in
   `{{CORE}}/core/tools.yaml` (you run it / narrowest project allow rule / leave unverified); record approval `tool_permission`.
4. Drive `{{CORE}}/core/workflow.yaml` through the template's path. Before each transition:
   `python -m crewline manifest <manifest> --to <STATE>`; move with `--apply`. Never move on a non-zero exit.
5. Delegate each state to the agent contract in `{{CORE}}/agents/` (SDET specialty in `agents/qa/`) with a minimal
   context packet. Acceptance tests are designed from the ACs before the code. Review 2 runs in a fresh context.
   Record authors and reviewers in the manifest.
6. Fork model: ask the upstream base branch before creating any branch; branch from it; only task changes; push to `origin`;
   (to add work to an existing PR the user names: work on that PR's head branch, allow its existing commits, push to it - orchestrator step 4b);
   PR against the upstream branch (`crewline branch`). Linked repos each get their own branch, gates and PR, dependency first.
7. Evidence: run builds and tests through `python -m crewline run --repo <dir> --out <record> -- <command>`; gates use
   `crewline evidence`, `change-scope`, `test-integrity`, `migration`, `trace`, `regression` (TestRig reports or surefire XML),
   plus the SDET validators (`testcase`, `expected-diff`, `scope`, `coverage`) and `secrets` / `dco`.
8. Ask before every action `{{CORE}}/core/permissions.yaml` marks as needing approval; record it (approver, reason, scope,
   timestamp). Approvals are human and single-use.
9. Failure triage: AUTOMATION -> SDET loop, CODE_UNDER_CHANGE -> developer loop (3 each); APPLICATION / SECURITY /
   SPECIFICATION escalate. Bugs carry the secret-scanned run report.
10. Finish with `{{CORE}}/templates/final-report.md`. SUCCESS only when every gate the template requires has evidence.

## Claude Code specifics

- Specialists are installed as subagents named `crewline-<agent>` (`crewline-software-developer`, `crewline-sdet-architect`, ...).
  Give each the smallest context packet; use a NEW subagent for the fresh-context review and record its id as `context_id`.
- Use a git worktree per task and repository; never edit the user's main checkout.
- Credentials: never read their values into context; merge them into the worktree config, mark it skip-worktree, restore after.
- Long runs (full suites, builds) go in the background; gates read the `crewline run` record, not the console.

## Rules

Never: run a second workflow or let a specialist move state; approve or review your own change; weaken, disable or delete
a test or expected result to pass; exceed three repair attempts per track; change files outside `scope.approved_paths`
without a `scope_change` approval; deploy to production; file an application bug without explicit confirmation; publish
raw run reports or logs; touch uncommitted work that is not yours; paste a result a command should produce.
