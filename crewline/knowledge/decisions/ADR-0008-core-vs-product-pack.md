# ADR-0008: Crewline core vs swappable product pack

- Status: Accepted (2026-10-29). Default pack remains `mosip`.
- Date: 2026-10-29 · Deciders: proposed in-repo · Task: split MOSIP plugin from gated SDLC core

## Context
Crewline's control model (one orchestrator, 28-state workflow, gates, `crewline guard` hooks) is product-neutral.
Its knowledge and SDET oracle were not: `core/tools.yaml` listed Java 21, Maven, MOSIP Jira, TestRig, CoverageCli;
orchestrators loaded `knowledge/mosip` on every task. That made Crewline a gated SDLC **with a MOSIP plugin built in**,
not a language-agnostic agent. Selling “any project” required a seam.

Knowledge files stay where they are (`knowledge/mosip`, `knowledge/frameworks`). Moving them would break ~200 links.
The pack **references** those dirs.

## Options
| Option | Pros | Cons |
|---|---|---|
| Keep MOSIP in core | No churn | Cannot sell a generic SDLC without lying |
| Physically move knowledge into `packs/mosip/` | Clean tree | Breaks links; large diff |
| Pack overlay: `packs/<id>/pack.yaml` + `tools.yaml`; knowledge by reference | Swappable; MOSIP default unchanged | Agents must load pack knowledge, not `knowledge/mosip` blindly |

## Decision
1. **Core** (`core/`, `agents/` contracts, `validators/` except TestRig CLIs, adapters, hooks): workflow, gates, permissions, evidence, `crewline guard`.
2. **Pack** (`packs/<id>/`): `pack.yaml` (id, `sdet.testrig`, `sdet.coverage_cli`, `knowledge:` dirs, `tools:` overlay). Committed default `packs/ACTIVE` = `mosip`.
3. **MOSIP pack** overlays Java 21, Maven, test credentials, Jira, browser upload, CoverageCli, module build, branch TestRig env. Knowledge: `knowledge/mosip`, `knowledge/frameworks`.
4. **Generic pack** overlays nothing. Knowledge: none. System tests = the module's own suite via `crewline run` / `regression`.
5. Select pack: `CREWLINE_PACK=<id>` (process, used by tests) or `python -m crewline pack --set <id>` (writes `packs/ACTIVE`).
6. `python -m crewline tools` merges `core/tools.yaml` + pack overlay. TestRig CLIs (`testcase`, `expected-diff`, `scope`, `coverage`) return `NOT_RUN` when the pack has `sdet.testrig` / `coverage_cli` false.
7. To add a product: copy `packs/generic/`, set `id`, point `knowledge:` at that product's map, overlay stack tools.

## Consequences
MOSIP engineering does not change (default pack). A non-MOSIP repo can run the same gates and hooks without Java, TestRig or the MOSIP application map. The SDLC still requires tests-before-code, evidence, and shipping rails; only the **oracle and stack** are the pack. `diff_coverage` already accepts JaCoCo or lcov; `test-integrity` already accepts JUnit or Jest. Module facts stay in `<repo>/.crewline/`.
