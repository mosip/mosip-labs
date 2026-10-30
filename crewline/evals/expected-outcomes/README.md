# Expected outcomes

One file per evals/task-scenarios id, written when the scenario is first run in a pilot (input, gate statuses, final outcome).

The official **frozen pack** (`evals/frozen-pack.yaml`) already has files for EV-02, EV-23, EV-25, EV-48, EV-50, EV-51, EV-54, EV-56.
Those freeze the **rails** both Cursor and Claude must keep green:

```bash
python -m crewline evals --pack frozen --run
```

That is the two-model contract. It does not invoke the LLMs. Agent-walk outcomes for EV-01 / EV-36 wait on a human cold-start P5 (`evals/cold-start.md`).
