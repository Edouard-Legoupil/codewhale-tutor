#!/usr/bin/env bash
#
# codewhale-tutor installer
#
# Installs the tutor MCP servers, skills, and dashboard backend into the
# Codewhale state root (~/.codewhale) using Codewhale's real conventions:
#   - MCP servers      -> ~/.codewhale/mcp.json
#   - skills           -> ~/.codewhale/skills/<name>/SKILL.md
#   - Python scripts   -> ~/.codewhale/tutor/  (with a private virtualenv)
#
# Your existing ~/.codewhale/config.toml and settings.toml are NOT touched.
#
# Safe to re-run (idempotent).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CW_HOME="${CODewhale_HOME:-$HOME/.codewhale}"
INSTALL_DIR="$CW_HOME/tutor"
VENV_DIR="$INSTALL_DIR/.venv"
MCP_JSON="$CW_HOME/mcp.json"
SKILLS_DIR="$CW_HOME/skills"

MCP_NAME_SYLLABUS="syllabus_processor"
MCP_NAME_EXAM="exam_analyzer"
MCP_NAME_MATH="math_engine"
MCP_NAME_PRACTICE="practice_engine"

log()  { printf '\033[1;34m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# --- Prerequisites -----------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die "python3 is required to install codewhale-tutor."
if ! command -v codewhale >/dev/null 2>&1; then
  warn "codewhale is not on PATH. The MCP servers will be installed, but you need Codewhale to use them."
fi

mkdir -p "$INSTALL_DIR"

# --- 1. Copy Python scripts --------------------------------------------------
log "Copying scripts to $INSTALL_DIR"
cp -f "$SCRIPT_DIR/syllabus_processor_mcp.py"      "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/exam_analyzer_mcp.py"           "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/tutor_dashboard.py"             "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/learning_style_analyzer.py"     "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/spaced_repetition.py"           "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/tracking_hook.py"               "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/weakness_assessment_hook.py"    "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/math_engine_mcp.py"             "$INSTALL_DIR/"
cp -f "$SCRIPT_DIR/practice_engine_mcp.py"         "$INSTALL_DIR/"

# --- 1b. Dashboard frontend --------------------------------------------------
log "Copying dashboard frontend"
mkdir -p "$INSTALL_DIR/dashboard"
cp -R "$SCRIPT_DIR/dashboard/." "$INSTALL_DIR/dashboard/"

# --- 2. Private virtualenv + dependencies ------------------------------------
if [ ! -x "$VENV_DIR/bin/python" ]; then
  log "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR" || die "Could not create a virtualenv. Install python3-venv and retry."
fi

log "Installing Python dependencies (mcp, PyPDF2, markdown, numpy, fastapi, uvicorn, sympy)"
"$VENV_DIR/bin/python" -m pip install --quiet --upgrade pip
# mcp pulls a modern pydantic; installing it here also fixes the global
# pydantic<2.7 "pydantic._internal._signature" incompatibility in this venv.
"$VENV_DIR/bin/python" -m pip install --quiet mcp PyPDF2 markdown numpy fastapi uvicorn sympy

# --- 3. Data directories -----------------------------------------------------
log "Creating data directories"
mkdir -p "$CW_HOME/syllabi" "$CW_HOME/exams" \
         "$CW_HOME/cheatsheets" "$CW_HOME/tutor_progress"

# --- 4. Skills (Codewhale's per-skill SKILL.md layout) -----------------------
log "Installing skills"
install_skill() {
  local slug="$1" src="$2"
  local dst="$SKILLS_DIR/$slug"
  mkdir -p "$dst"
  cp -f "$src" "$dst/SKILL.md"
}
install_skill math-problem-solver       "$SCRIPT_DIR/skills/math-problem-solver/SKILL.md"
install_skill economics-analysis        "$SCRIPT_DIR/skills/economics-analysis/SKILL.md"
install_skill social-science-analysis   "$SCRIPT_DIR/skills/social-science-analysis/SKILL.md"
install_skill metacognitive-tutor       "$SCRIPT_DIR/skills/metacognitive-tutor/SKILL.md"
install_skill linear-algebra            "$SCRIPT_DIR/skills/linear-algebra/SKILL.md"
install_skill probability-statistics    "$SCRIPT_DIR/skills/probability-statistics/SKILL.md"
install_skill python-programming        "$SCRIPT_DIR/skills/python-programming/SKILL.md"
install_skill data-visualization        "$SCRIPT_DIR/skills/data-visualization/SKILL.md"
install_skill exam-technique            "$SCRIPT_DIR/skills/exam-technique/SKILL.md"

# --- 5. Register MCP servers (merge into mcp.json, never clobber) ------------
log "Registering MCP servers in $MCP_JSON"
MCP_JSON="$MCP_JSON" \
VENV_PY="$VENV_DIR/bin/python" \
SYLLABUS_SRV="$INSTALL_DIR/syllabus_processor_mcp.py" \
EXAM_SRV="$INSTALL_DIR/exam_analyzer_mcp.py" \
MATH_SRV="$INSTALL_DIR/math_engine_mcp.py" \
PRACTICE_SRV="$INSTALL_DIR/practice_engine_mcp.py" \
MCP_NAME_SYLLABUS="$MCP_NAME_SYLLABUS" \
MCP_NAME_EXAM="$MCP_NAME_EXAM" \
MCP_NAME_MATH="$MCP_NAME_MATH" \
MCP_NAME_PRACTICE="$MCP_NAME_PRACTICE" \
python3 - <<'PY'
import json
import os
import sys
from pathlib import Path

mcp_json = Path(os.environ["MCP_JSON"])
data = {}
if mcp_json.exists():
    try:
        data = json.loads(mcp_json.read_text())
    except json.JSONDecodeError:
        bak = mcp_json.with_suffix(".json.bak")
        mcp_json.rename(bak)
        print(f"[warn] {mcp_json} was not valid JSON; backed it up to {bak}", file=sys.stderr)
        data = {}

data.setdefault("timeouts", {}).setdefault("connect_timeout", 10)
data["timeouts"].setdefault("execute_timeout", 60)
data["timeouts"].setdefault("read_timeout", 120)
data.setdefault("servers", {})


def stdio_entry(script: str) -> dict:
    return {
        "command": os.environ["VENV_PY"],
        "args": [script],
        "env": {},
        "url": None,
        "connect_timeout": None,
        "execute_timeout": None,
        "read_timeout": None,
        "disabled": False,
        "enabled": True,
        "required": False,
        "enabled_tools": [],
        "disabled_tools": [],
    }


data["servers"][os.environ["MCP_NAME_SYLLABUS"]] = stdio_entry(os.environ["SYLLABUS_SRV"])
data["servers"][os.environ["MCP_NAME_EXAM"]] = stdio_entry(os.environ["EXAM_SRV"])
data["servers"][os.environ["MCP_NAME_MATH"]] = stdio_entry(os.environ["MATH_SRV"])
data["servers"][os.environ["MCP_NAME_PRACTICE"]] = stdio_entry(os.environ["PRACTICE_SRV"])

mcp_json.write_text(json.dumps(data, indent=2) + "\n")
PY

# --- Done --------------------------------------------------------------------
log "Installation complete."
cat <<EOF

Next steps:
  1. Restart Codewhale so it re-reads MCP config (or run: codewhale mcp list).
  2. Put syllabus/exam PDFs into:
       $CW_HOME/syllabi
       $CW_HOME/exams
  3. Start a tutoring session with the skill: /skill metacognitive-tutor
  4. (Optional) Start the dashboard API and frontend:
       $VENV_DIR/bin/python $INSTALL_DIR/tutor_dashboard.py
       cd $INSTALL_DIR/dashboard && npm install && npm run dev   # http://localhost:5173

Run ./uninstall.sh to remove everything this script installed.
EOF
