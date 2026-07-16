# Server database layer

## Layout

```text
Server/
├── db/
│   ├── base.py              # DeclarativeBase
│   ├── engine.py            # Shared pooled engine + session_scope()
│   ├── models.py            # ChatSession, ChatTurn, Feedback, QueryEvent
│   ├── repositories/        # SQLAlchemy CRUD bound to an open Session
│   └── crud/                # Transactional wrappers + UnitOfWork
│       ├── uow.py           # unit_of_work() context
│       ├── sessions.py      # session / turn CRUD
│       ├── feedback.py      # feedback CRUD
│       └── query_events.py  # stats / analytics CRUD
├── controllers/             # API-facing validation + DTOs over db.crud
├── alembic/
│   ├── env.py               # Skips langchain_pg_* tables
│   └── versions/
└── alembic.ini
```

## Layers

| Layer | Role |
| --- | --- |
| `db.models` | ORM table definitions |
| `db.repositories` | Low-level create/read/update/delete on a `Session` |
| `db.crud` | Opens transactions; optional `uow=` for multi-table ops |
| `controllers` | HTTP validation, errors, response shaping |

```python
from db.crud import sessions, feedback, query_events, unit_of_work

# Single operation (owns its transaction)
sessions.create()
feedback.counts()

# Multi-table transaction
with unit_of_work() as uow:
    s = sessions.create(uow=uow)
    feedback.create(session_id=s.id, turn_number=1, question="…", rating="positive", uow=uow)
```

## Commands

```powershell
cd Server
uv sync
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe change"
```

## Rules

- Migrate **only** app tables in `db.models`.
- Never autogenerate drops against `langchain_pg_*`.
- Routes call `controllers.*`; controllers call `db.crud.*` (not raw SQL).
