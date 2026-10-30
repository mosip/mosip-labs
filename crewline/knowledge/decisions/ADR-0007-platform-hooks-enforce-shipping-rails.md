# ADR-0007: Platform hooks enforce shipping rails (commit / push / PR)

- Status: Accepted (2026-10-29). All adapters: Cursor, Claude Code, generic (git hooks).
- Date: 2026-10-29 · Deciders: proposed in-repo · Task: tighten guard rails

## Context
Validators only run when the model invokes them. A prompt-only adapter (Cursor rule, Claude skill, generic ENTRY.md)
lets an agent skip `crewline manifest` and still `git commit` / `git push` / `gh pr create`. That is the failure
mode the rest of the framework exists to prevent. Engineers do not use only Cursor.

## Options
| Option | Pros | Cons |
|---|---|---|
| Stronger prompt only | Cheap | Still honor-system |
| One `crewline guard` policy, platform-specific enforcement | Same rules everywhere | Each tool has a different hook JSON |
| Git `pre-commit` only | Works for any tool | `--no-verify` skips it; cannot see force-push the same way |

## Decision
1. `python -m crewline guard --shell|--write` (GRD-001..006) is the single policy entry.
2. **Cursor:** `.cursor/hooks.json` (`beforeShellExecution`, `preToolUse`, `sessionStart`), `failClosed: true`, rule `alwaysApply: true`.
3. **Claude Code:** `.claude/settings.json` `PreToolUse` (Bash, Write|Edit) + `SessionStart`, plus `permissions.deny` for force-push / `--no-verify` / hard reset / stash / branch delete / PR merge. Subagent tool allow-lists stay. Output is Claude `hookSpecificOutput.permissionDecision`.
4. **Generic:** git `pre-commit`, `commit-msg`, `pre-push` calling the same trampoline (`git-commit` / `git-push`). Use when the tool has no hook API. Cannot catch `--no-verify`; ENTRY.md forbids it.
5. Shared trampoline: `adapters/hooks/crewline_hook.py` (CORE baked in at install).
6. `git commit --no-verify` is GRD-006 on Cursor/Claude, not a workaround.

## Consequences
Shipping from Cursor or Claude Code without a live task and passing gates is blocked even if the model ignores the markdown.
Generic installs block commit/push at git, which also covers Copilot / Gemini / a human in that clone, unless they pass `--no-verify`.
A human can still commit from a terminal that is not hooked (Cursor) or with `--no-verify` (generic).
