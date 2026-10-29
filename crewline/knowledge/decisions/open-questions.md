# Open questions (Phase 0, Blueprint v2.1 §17)

| # | Question | Status | Answer / evidence |
|---|---|---|---|
| Q1 | Pilot module and repositories | Answered (SDET), proposed (dev) | pre-registration (`mosip/pre-registration`) + apitest-commons. Dev pilot: a `pre-registration-application-service` bug fix or small feature in the same repo |
| Q2 | API TestRig YAML structure, ID convention, loader, command | Answered (Verified) | knowledge/frameworks/apitestrig.md; profile pre-registration/.crewline/qa/profile.yaml |
| Q3 | Language/build/unit-test commands for the dev pilot | Answered (Verified, 2026-10-28) | Java 21, Maven, JUnit (vintage engine present), JaCoCo 0.8.11; pre-registration/.crewline/development/local-context.md |
| Q4 | Architecture/ADR conventions in the repos | Open | none found in pre-registration `docs/` yet; assistant ADRs live in knowledge/decisions/ |
| Q5 | Approved CI, static-analysis, security, dependency, secret scanning | Partly answered | CI: `mosip/kattu` reusable maven/docker workflows; CodeQL (`codeql_custom.yml`); CodeRabbit + DCO seen on PR #1088. Local OWASP dependency-check: to confirm |
| Q6 | GitHub issue/PR conventions, DCO, branch protection | Answered | fork model (ADR-0003), DCO required, PR to `mosip/develop` |
| Q7 | Pre-authorized actions, how approvals are recorded | Answered | none pre-authorized; approvals in manifest + approvals.yaml, human and single-use |
| Q8 | Non-production environment for a release/rollback drill, and how a branch build gets deployed there | **Open** | `api-internal.released` runs released builds only; system tests of a production-code change need an env running the branch build |
| Q9 | Where to host the assistant repositories (org-wide rules) | Open | carried from SDET assistant |
