# Agents by role

One orchestrator ([`orchestrator.md`](orchestrator.md)) owns state, approvals and evidence; every other agent is a
specialist grouped by the role it plays in a team. Folders are for people; the workflow and the installer find agents
by their `name:` (installed as `crewline-<name>`), so moving a file between role folders changes nothing at runtime.

| Role | Agent | Workflow states | Permission profile |
|---|---|---|---|
| Orchestration | [`orchestrator`](orchestrator.md) | all | analysis |
| Product Owner / Business Analyst | [`requirement-analyst`](product/requirement-analyst.md) | INPUT_VALIDATION, REQUIREMENT_ANALYSIS | read-only |
|  | [`acceptance-reviewer`](product/acceptance-reviewer.md) | ACCEPTANCE_REVIEW | read-only |
| UI / UX | [`ux-designer`](ui-ux/ux-designer.md) | DESIGN, TESTCASE_DESIGN (UI), IMPLEMENTATION_REVIEW (UI diffs) | read-only |
| Architect | [`impact-analyst`](architecture/impact-analyst.md) | IMPACT_ANALYSIS | analysis |
|  | [`solution-architect`](architecture/solution-architect.md) | DESIGN | read-only (writes design docs in the task workspace) |
|  | [`api-contract-designer`](architecture/api-contract-designer.md) | DESIGN, IMPLEMENTATION_REVIEW | read-only |
| Developer | [`software-developer`](development/software-developer.md) | IMPLEMENTATION, FAILURE_TRIAGE (CODE_UNDER_CHANGE) | workspace-write |
|  | [`database-engineer`](development/database-engineer.md) | DESIGN, IMPLEMENTATION | workspace-write (DB script folders only) |
| QA / SDET | [`sdet-architect`](qa/sdet-architect.md) | TESTCASE_DESIGN, TESTCASE_REVIEW, IMPLEMENTATION (testcases), SYSTEM_TEST_EXECUTION, FAILURE_TRIAGE (AUTOMATION) | workspace-write |
|  | [`testcase-designer`](qa/testcase-designer.md) | TESTCASE_DESIGN | workspace-write |
|  | [`testcase-reviewer`](qa/testcase-reviewer.md) | TESTCASE_REVIEW | read-only |
|  | [`api-automation`](qa/api-automation.md) | IMPLEMENTATION | workspace-write |
|  | [`ui-automation`](qa/ui-automation.md) | IMPLEMENTATION (P7+) | workspace-write |
|  | [`dsl-automation`](qa/dsl-automation.md) | IMPLEMENTATION (P7+) | workspace-write |
|  | [`failure-analyst`](qa/failure-analyst.md) | FAILURE_TRIAGE | analysis |
|  | [`defect-analyst`](qa/defect-analyst.md) | FAILURE_TRIAGE / S_ESCALATE | read-only |
| Reviewer | [`code-reviewer`](review/code-reviewer.md) | IMPLEMENTATION_REVIEW, PR_CLOSEOUT | analysis |
|  | [`fresh-context-reviewer`](review/fresh-context-reviewer.md) | FRESH_CONTEXT_REVIEW | analysis |
| Security | [`security-engineer`](security/security-engineer.md) | DETERMINISTIC_VALIDATION, IMPLEMENTATION_REVIEW | analysis |
| DevOps / Release | [`devops-engineer`](devops/devops-engineer.md) | IMPLEMENTATION, RELEASE_READINESS, AUTHORIZED_DEPLOYMENT | workspace-write (CI/build/deploy paths, with scope_change approval) |
|  | [`release-manager`](devops/release-manager.md) | RELEASE_READINESS | read-only |
| SRE / Operations | [`sre-analyst`](operations/sre-analyst.md) | INTAKE, IMPACT_ANALYSIS, POST_DEPLOYMENT_VALIDATION, FINAL_REPORT (incident template) | read-only |
| Knowledge | [`knowledge-curator`](knowledge/knowledge-curator.md) | KNOWLEDGE_UPDATE | workspace-write (knowledge/ and .crewline/qa/ only) |
|  | [`module-onboarder`](knowledge/module-onboarder.md) | IMPACT_ANALYSIS, KNOWLEDGE_UPDATE (module-onboarding) | analysis |

## Role folders

- `product/` - **Product Owner / Business Analyst**: what to build and how we know it is done
- `ui-ux/` - **UI / UX**: how users experience it: screens, states, copy, accessibility
- `architecture/` - **Architect**: how it fits: impact, design options, contracts
- `development/` - **Developer**: building it: code, unit/component tests, data changes
- `qa/` - **QA / SDET**: proving it works: test design, automation, failure analysis, defects
- `review/` - **Reviewer**: independent checks of the change
- `security/` - **Security**: threats, auth, secrets, dependencies
- `devops/` - **DevOps / Release**: pipelines, deploys, release readiness
- `operations/` - **SRE / Operations**: running systems: incidents, post-deployment checks
- `knowledge/` - **Knowledge**: what the team learns: verified knowledge, module onboarding

Adding an agent: put the contract in its role folder, add it to `core/permissions.yaml` `agents:`, mention it in the
orchestrator's delegation step if it owns a state, and run the validator tests.
