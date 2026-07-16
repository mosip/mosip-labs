#!/bin/sh
set -e
cd /app/MosipNexus/Server
echo "Running Alembic migrations..."
uv run alembic upgrade head || {
    echo "Migration failed — stamping head and retrying..."
    uv run alembic stamp head
    uv run alembic upgrade head
}
echo "Starting: $*"
exec "$@"
