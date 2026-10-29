#!/usr/bin/env bash
# One-time Crewline setup for Linux / macOS / Git Bash.
# Installs Python deps, runs validator tests, checks tools.yaml, optionally installs an adapter.
#
#   ./scripts/setup.sh
#   ./scripts/setup.sh cursor /path/to/mosip-clones
#   ./scripts/setup.sh claude /path/to/mosip-clones --force
#   ./scripts/setup.sh generic /path/to/module-repo
#
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM=""
TARGET=""
FORCE=""
SKIP_TESTS=""

usage() {
  cat <<EOF
Crewline setup (prerequisites + optional adapter)

  $0
  $0 <cursor|claude|generic> <target-folder> [--force] [--skip-tests]

  target-folder  folder where you keep MOSIP module clones (Cursor/Claude),
                 or the module repo itself (generic git hooks)

This script does not install Git, GitHub CLI, or the active pack's stack
(MOSIP default: JDK 21, Maven). Missing ones are listed with numbered
enable steps from core/tools.yaml + packs/ACTIVE.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --force) FORCE=--force; shift ;;
    --skip-tests) SKIP_TESTS=1; shift ;;
    cursor|claude|generic) PLATFORM="$1"; shift ;;
    *)
      if [ -z "$TARGET" ]; then TARGET="$1"; shift
      else echo "unexpected argument: $1" >&2; usage; exit 2
      fi ;;
  esac
done

if [ -n "$PLATFORM" ] && [ -z "$TARGET" ]; then
  echo "error: $PLATFORM needs a target folder (where your MOSIP clones live)." >&2
  usage
  exit 2
fi

cd "$ROOT"
echo "== Crewline setup =="
echo "    core: $ROOT"

find_python() {
  local c
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

if ! PY="$(find_python)"; then
  echo "error: Python 3.11+ is required and must be on PATH." >&2
  echo "  1. Install Python 3.11+ from https://www.python.org/downloads/" >&2
  echo "  2. Open a new terminal and run: python3 --version" >&2
  echo "  3. Re-run: $0" >&2
  exit 1
fi
echo "-- python: $($PY --version)"

echo "-- pip install -r validators/requirements.txt"
if ! "$PY" -m pip install -r "$ROOT/validators/requirements.txt"; then
  echo "error: pip install failed." >&2
  exit 1
fi

if [ -z "$SKIP_TESTS" ]; then
  echo "-- pytest validators"
  if ! (cd "$ROOT/validators" && "$PY" -m pytest -q tests); then
    echo "error: validator tests failed. Do not install the adapter until they pass." >&2
    exit 1
  fi
else
  echo "-- pytest skipped (--skip-tests)"
fi

echo "-- python -m crewline tools"
TOOLS_RC=0
(cd "$ROOT/validators" && "$PY" -m crewline tools) || TOOLS_RC=$?
if [ "$TOOLS_RC" -ne 0 ]; then
  echo ""
  echo "Some tools.yaml capabilities are missing. Follow the numbered enable steps above."
  echo "You can still install an adapter; a task that needs a missing tool will stop at S0."
fi

if [ -n "$PLATFORM" ]; then
  echo "-- adapters/install.py --platform $PLATFORM --target $TARGET --write ${FORCE}"
  if ! "$PY" "$ROOT/adapters/install.py" --platform "$PLATFORM" --target "$TARGET" --write $FORCE; then
    echo "error: adapter install failed." >&2
    exit 1
  fi
  echo ""
  echo "Next: open $TARGET in ${PLATFORM} and describe the work in one message."
  echo "      (Cursor or Claude Code starts the crew; this script does not.)"
else
  echo ""
  echo "Prerequisites for Crewline itself are in place (Python package + tests)."
  echo "Install an adapter when you are ready:"
  echo "  $0 cursor  /path/to/mosip-clones"
  echo "  $0 claude  /path/to/mosip-clones"
  echo "  $0 generic /path/to/module-repo"
fi

if [ "$TOOLS_RC" -ne 0 ]; then
  exit 2
fi
echo "OK"
exit 0
