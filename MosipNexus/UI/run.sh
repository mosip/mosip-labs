#!/usr/bin/env bash
# Nexus UI — React / Vite (Linux / macOS equivalent of run.bat)
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo " Nexus UI — React (Vite)"
echo "========================================"
echo

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    echo "Creating .env from .env.example ..."
    cp .env.example .env
    echo
  else
    echo "ERROR: .env.example not found." >&2
    exit 1
  fi
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Install Node.js 20+ from https://nodejs.org" >&2
  exit 1
fi

echo "Checking npm dependencies ..."
NEED_INSTALL=0
if [[ ! -d node_modules ]]; then NEED_INSTALL=1; fi
if [[ ! -x node_modules/.bin/vite ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/react/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/react-dom/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/react-router-dom/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/react-markdown/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/remark-gfm/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/typescript/package.json ]]; then NEED_INSTALL=1; fi
if [[ ! -f node_modules/@vitejs/plugin-react/package.json ]]; then NEED_INSTALL=1; fi

if [[ "$NEED_INSTALL" -eq 1 ]]; then
  echo "Dependencies missing or incomplete — installing ..."
  echo
  if [[ -f package-lock.json ]]; then
    npm ci
  else
    npm install
  fi
  echo
  echo "Dependencies installed."
  echo
else
  echo "Dependencies OK."
  echo
fi

echo "Starting Vite on http://localhost:8501"
echo "API proxy: /api -> value of VITE_DEV_API_PROXY in .env"
echo "          (default http://localhost:8010 — start Server/run.sh first)"
echo
exec npm run dev
