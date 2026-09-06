#!/usr/bin/env bash
#
# start.sh — one command to launch the Knowledge Quest Academy.
#
#   * starts the tutor API (FastAPI) on http://localhost:8000
#   * installs frontend deps if needed
#   * starts the Vite dev server and opens the browser on http://localhost:5173
#
# Works after `./install.sh`, or standalone from a fresh clone (it creates a
# local .venv when the Codewhale tutor venv is not present).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { printf "${GREEN}==>${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}!!${NC} %s\n" "$1"; }
die() { printf "${RED}\u2717${NC} %s\n" "$1" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.10+ first."
command -v npm >/dev/null 2>&1 || die "npm not found. Install Node.js (18+) first."

# --- Python + venv ----------------------------------------------------------
PYTHON="${PYTHON:-python3}"
CW_VENV="$HOME/.codewhale/tutor/.venv"
if [ -x "$CW_VENV/bin/python" ]; then
  PY="$CW_VENV/bin/python"
else
  warn "No Codewhale tutor venv at $CW_VENV — using a local .venv"
  if [ ! -x ".venv/bin/python" ]; then
    "$PYTHON" -m venv .venv || die "Could not create .venv. Install python3-venv."
  fi
  PY=".venv/bin/python"
fi

if ! "$PY" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  log "Installing backend dependencies (fastapi, uvicorn, PyPDF2)"
  "$PY" -m pip install --quiet --upgrade pip
  "$PY" -m pip install --quiet fastapi uvicorn PyPDF2
fi

# --- Backend ----------------------------------------------------------------
BACKEND_PID=""
cleanup() { [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT

if curl -sf http://localhost:8000/api/syllabi >/dev/null 2>&1; then
  log "Tutor API already running on http://localhost:8000"
else
  log "Starting tutor API on http://localhost:8000"
  "$PY" tutor_dashboard.py > /tmp/codewhale-tutor-api.log 2>&1 &
  BACKEND_PID=$!
  for _ in $(seq 1 40); do
    curl -sf http://localhost:8000/api/syllabi >/dev/null 2>&1 && break
    sleep 0.5
  done
  if ! curl -sf http://localhost:8000/api/syllabi >/dev/null 2>&1; then
    warn "Tutor API did not become ready — check /tmp/codewhale-tutor-api.log"
  fi
fi

# --- Frontend ---------------------------------------------------------------
cd "$SCRIPT_DIR/dashboard"
if [ ! -d node_modules ]; then
  log "Installing frontend dependencies (npm install)"
  npm install --no-audit --no-fund
fi

log "Opening the frontend in your browser at http://localhost:5173"
exec npm run dev -- --host --open
