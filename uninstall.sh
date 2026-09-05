#!/usr/bin/env bash
#
# codewhale-tutor uninstaller
#
# Reverses install.sh: removes the tutor MCP server entries, the installed
# skills, and the ~/.codewhale/tutor/ directory. Student data is left in place
# unless --purge-data is passed.
#
# Usage:
#   ./uninstall.sh              # remove code + config, keep student data
#   ./uninstall.sh --purge-data # also delete syllabi/exams/progress/cheatsheets
set -euo pipefail

CW_HOME="${CODewhale_HOME:-$HOME/.codewhale}"
INSTALL_DIR="$CW_HOME/tutor"
MCP_JSON="$CW_HOME/mcp.json"
SKILLS_DIR="$CW_HOME/skills"

PURGE_DATA=0
for arg in "$@"; do
  case "$arg" in
    --purge-data) PURGE_DATA=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

log()  { printf '\033[1;34m[uninstall]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }

# --- 1. Remove MCP server entries (preserve any other servers) ---------------
if [ -f "$MCP_JSON" ]; then
  log "Removing MCP server entries from $MCP_JSON"
  MCP_JSON="$MCP_JSON" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["MCP_JSON"])
try:
    data = json.loads(path.read_text())
except json.JSONDecodeError:
    print(f"[warn] {path} is not valid JSON; leaving it untouched.", file=__import__("sys").stderr)
    raise SystemExit(0)

servers = data.get("servers", {})
for name in ("syllabus_processor", "exam_analyzer", "math_engine", "practice_engine"):
    servers.pop(name, None)

if not servers and "servers" in data:
    # Keep a minimal valid structure so Codewhale doesn't choke on a bare file.
    data["servers"] = {}

path.write_text(json.dumps(data, indent=2) + "\n")
PY
else
  warn "No mcp.json found at $MCP_JSON; nothing to remove."
fi

# --- 2. Remove installed skills ----------------------------------------------
log "Removing installed skills"
for slug in math-problem-solver economics-analysis social-science-analysis metacognitive-tutor linear-algebra probability-statistics python-programming data-visualization exam-technique; do
  if [ -d "$SKILLS_DIR/$slug" ]; then
    rm -rf "$SKILLS_DIR/$slug"
    echo "  removed $SKILLS_DIR/$slug"
  fi
done

# Remove any generated per-syllabus skills (syllabus-*)
for d in "$SKILLS_DIR"/syllabus-*; do
  if [ -d "$d" ]; then
    rm -rf "$d"
    echo "  removed $d"
  fi
done

# --- 3. Remove the tutor install directory -----------------------------------
if [ -d "$INSTALL_DIR" ]; then
  log "Removing $INSTALL_DIR"
  rm -rf "$INSTALL_DIR"
else
  warn "No $INSTALL_DIR found; nothing to remove."
fi

# --- 4. Optional: purge student data -----------------------------------------
if [ "$PURGE_DATA" -eq 1 ]; then
  log "Purging student data directories"
  for d in syllabi exams progress cheatsheets tutor_progress; do
    if [ -d "$CW_HOME/$d" ]; then
      rm -rf "$CW_HOME/$d"
      echo "  removed $CW_HOME/$d"
    fi
  done
else
  echo "Student data (syllabi/exams/progress/cheatsheets/tutor_progress) was left in place."
  echo "Re-run with --purge-data to delete it too."
fi

log "Uninstall complete."
