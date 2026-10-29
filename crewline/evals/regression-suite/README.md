# Regression suite (frozen eval pack)

`evals/task-scenarios/scenarios.yaml` is the pack. Each `automated_by` line must name a pytest that still exists.

```bash
cd validators
python -m crewline evals                     # EVAL-001 if a nodeid vanished
python -m crewline evals --run               # also execute those tests
python -m crewline evals --pack frozen --run # 8-story official pack + expected-outcomes/
```

The two-model contract is that Cursor and Claude both keep `--pack frozen --run` green. Agent-walk SHAs for EV-01 / EV-36 wait on a human observer (`evals/cold-start.md`).
