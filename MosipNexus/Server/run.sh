#!/usr/bin/env bash
# Nexus Server — FastAPI (Linux / macOS equivalent of run.bat)
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo " Nexus Server — FastAPI"
echo "========================================"
echo

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "Creating .env from .env.example ..."
    cp .env.example .env
    echo "Edit Server/.env and set PG_CONNECTION before chatting."
    echo
  else
    echo "ERROR: .env.example not found." >&2
    exit 1
  fi
fi

export PYTHONPATH="$(pwd)"

HAS_UV=0
if command -v uv >/dev/null 2>&1; then
  HAS_UV=1
fi

# ── 1. Ensure .venv exists ───────────────────────────────────────────────────
echo "Setting up virtual environment (.venv) ..."
if [[ -x .venv/bin/python ]]; then
  echo ".venv already present."
else
  if [[ "$HAS_UV" -eq 1 ]]; then
    echo "Creating .venv with uv (Python 3.13) ..."
    if [[ -f .python-version ]]; then
      uv venv --python 3.13
    else
      uv venv
    fi
  else
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
      echo "ERROR: Neither \"uv\" nor \"python\" found on PATH." >&2
      echo "Install uv (https://github.com/astral-sh/uv) or Python 3.13+." >&2
      exit 1
    fi
    PY=python3
    command -v python3 >/dev/null 2>&1 || PY=python
    echo "Creating .venv with ${PY} -m venv ..."
    "$PY" -m venv .venv
  fi
  if [[ ! -x .venv/bin/python ]]; then
    echo "ERROR: .venv was not created correctly." >&2
    exit 1
  fi
  echo ".venv created."
fi
echo

# ── 2. Install / sync dependencies into .venv ────────────────────────────────
echo "Checking dependencies in .venv ..."
NEED_INSTALL=0
if [[ ! -x .venv/bin/uvicorn ]]; then
  NEED_INSTALL=1
fi
if ! .venv/bin/python -c "import fastapi,uvicorn,sqlalchemy,alembic" >/dev/null 2>&1; then
  NEED_INSTALL=1
fi

if [[ "$NEED_INSTALL" -eq 1 ]]; then
  echo "Dependencies missing or incomplete — installing into .venv ..."
  echo
  if [[ "$HAS_UV" -eq 1 ]]; then
    # uv sync installs the project + lockfile deps into ./.venv
    uv sync
  else
    if [[ ! -f requirements.txt ]]; then
      echo "ERROR: requirements.txt not found (needed for pip install)." >&2
      exit 1
    fi
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt
  fi
  echo
  if [[ ! -x .venv/bin/uvicorn ]]; then
    echo "ERROR: uvicorn still missing from .venv after install." >&2
    exit 1
  fi
  if ! .venv/bin/python -c "import fastapi,uvicorn,sqlalchemy,alembic" >/dev/null 2>&1; then
    echo "ERROR: Core packages failed to import from .venv after install." >&2
    exit 1
  fi
  echo "Dependencies installed into .venv."
  echo
else
  echo "Dependencies OK in .venv."
  echo
fi

# ── 3. Activate .venv and run API ────────────────────────────────────────────
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Using:"
command -v python
echo
echo "Starting API on http://localhost:8010"
echo "Swagger: http://localhost:8010/docs"
echo
exec .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8010 --reload --limit-concurrency 64
