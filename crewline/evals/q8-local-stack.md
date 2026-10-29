# Q8 local-stack (laptop)

Crewline does not provision a MOSIP cluster. For SYSTEM_TEST_EXECUTION of a code change, name an env that
runs **this branch**.

## Preferred on a developer machine

1. From the module worktree, start what `.crewline/development/local-context.md` names:
   - `docker compose up` in the module, or
   - `mvn -pl <service> spring-boot:run` on a free port.
2. Confirm a health URL answers (`curl http://127.0.0.1:<port>/...`).
3. Record on the manifest:
   - `test_plan.environment_kind`: `local-stack`
   - `test_plan.environment`: that URL (never `api-internal.released`).
4. Point TestRig / `baseUrl` at the same URL.
5. `python -m crewline branch-env --manifest tasks/<id>/task-manifest.json` must PASS (BEV-004 if you named released).

## Branch-deployed env

Ask the platform team to deploy **this** branch image to a named non-prod namespace. Health URL must answer.
`environment_kind=branch-deployed-env`.

## If neither exists this week

`environment_kind=post-merge-deferred` plus an attributed `system_tests` exception (environment + date). Results
stay DEFERRED. That is not testing the branch.
