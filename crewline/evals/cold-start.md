# Cold-start P5 (human)

This is the proof the framework cannot give itself: **one feature, one new machine, every `manifest --apply`, no Crewline author in the chat.**

## Machine (anyone)

```bat
cd crewline
scripts\setup.bat cursor <workspace>
python -m crewline cold-start
```

`cold-start` must PASS (frozen pack, adapter --check, synthetic --apply sequence). If it FAIL, fix Crewline first; do not start a MOSIP story.

## Feature walk (different person than the Crewline author)

1. New Cursor (or Claude Code) chat. Do not paste this repo's internals. Story only, e.g. a small pre-registration AC.
2. Classify `feature`. Create `tasks/<id>/task-manifest.json`. `started_at` now.
3. Every state: `python -m crewline manifest <m> --to <STATE>` then `--apply` only on exit 0.
4. Q8: `test_plan.environment_kind=local-stack` and a URL **this branch** actually serves (`docker compose` / `spring-boot:run`). Never `api-internal.released`.
5. Stop at every WAITING_FOR_USER. One question.
6. When DONE, write `evals/expected-outcomes/EV-36.json` with gate statuses and the PR URL.

## Must not

- Crewline author driving the chat
- Skipping `--apply`
- Treating the released env as the branch
