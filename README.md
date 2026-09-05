# codewhale-tutor

A codewhale set up designed for student to benefit from advanced tutoring

## Requirement → Implementation

Multiple syllabus types → process_syllabus handles any subject from PDFs

Build tutoring plans → Automatic concept extraction and curriculum mapping

Socratic approach → metacognitive_tutor.md prompt with questioning framework

Metacognition focus → Specialized prompts for self-reflection and strategy awareness

Track student responses → tracking_hook.py with full response history

Return to theory → Weakness detection triggers concept review

Learn from exams → process_exam identifies tested concepts and frequencies

Track learning stage → current_stage and concept_mastery in progress data

Multi-language → Language detection and support throughout

Cheatsheets → generate_cheatsheet for each syllabus

Recall support → Cheatsheets and spaced repetition system

Adaptive → Adjusts based on mastery, confidence, and learning style

Subject-Specific Skills → Math problem-solving, economic analysis, social science critical thinking `math_problem_solver.md`, `economics_analysis.md`, `social_science_analysis.md`

Web Dashboard → Visualize student progress, concept mastery, exam analytics  `tutor_dashboard.py`, `App.jsx`, `App.css`

Sophisticated Exam Analysis → Question classification, difficulty estimation, Bloom's taxonomy mapping, study plan generation `exam_analyzer_mcp.py`

## Architecture

```text
┌────────────────────────────────────────────────────────────────┐
│                     CodeWhale Tutor System                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Syllabus    │  │  Exam Data   │  │  Student     │          │
│  │  Processor   │  │  Analyzer    │  │  Tracker     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                  ┌────────▼────────┐                           │
│                  │  MCP Learning   │                           │
│                  │     Engine      │                           │
│                  └────────┬────────┘                           │
│                           │                                    │
│         ┌─────────────────┼─────────────────┐                  │
│         │                 │                 │                  │
│  ┌──────▼───────┐ ┌───────▼────────┐ ┌──────▼──────┐           │
│  │  Socratic    │ │  Metacognition │ │  Adaptive   │           │
│  │  Tutor Agent │ │   Agent        │ │  Planner    │           │
│  └──────────────┘ └────────────────┘ └─────────────┘           │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Student Progress Database                  │   │
│  │  - Learning stages per syllabus                         │   │
│  │  - Concept mastery scores                               │   │
│  │  - Response history                                     │   │
│  │  - Weakness identification                              │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```text

## Install / Uninstall

```bash
# One command installs the MCP servers, skills, and dashboard backend
# into ~/.codewhale using Codewhale's real conventions.
./install.sh

# Remove everything install.sh added (keeps student data).
./uninstall.sh

# Remove everything including student data.
./uninstall.sh --purge-data
```

After installing, restart Codewhale so it re-reads `~/.codewhale/mcp.json`,
then drop syllabus/exam PDFs into `~/.codewhale/syllabi` and
`~/.codewhale/exams`. Start tutoring with the `metacognitive-tutor` skill
(`/skill metacognitive-tutor`).

## File Structure Summary

```text
~/.codewhale/
├── mcp.json                          # MCP servers (syllabus_processor, exam_analyzer)
├── skills/
│   ├── math-problem-solver/SKILL.md
│   ├── economics-analysis/SKILL.md
│   ├── social-science-analysis/SKILL.md
│   └── metacognitive-tutor/SKILL.md
├── tutor/
│   ├── .venv/                        # private Python environment
│   ├── syllabus_processor_mcp.py     # MCP server
│   ├── exam_analyzer_mcp.py          # MCP server
│   ├── tutor_dashboard.py            # dashboard API
│   ├── dashboard/                    # React (Vite) frontend
│   └── ...                           # helper scripts
├── syllabi/                          # processed syllabus JSON
├── exams/                            # processed exam JSON
├── cheatsheets/                      # generated cheatsheets
└── tutor_progress/                   # student progress (unified)
```text

# Working with the Tutor

```bash
# In the CodeWhale TUI:

# Process a new syllabus
> /process_syllabus ~/.codewhale/syllabi/economics_101.pdf economics

# Process an exam
> /process_exam ~/.codewhale/exams/economics_exam_2023.pdf economics exam_2023

# Start a tutoring session
> /tutor start economics

# The tutor will:
# 1. Analyze your progress (if any)
# 2. Identify weak concepts
# 3. Begin Socratic questioning
# 4. Generate cheatsheets as needed
# 5. Track your responses

# View progress
> /progress economics

# Focus on a specific concept
> /tutor focus "New Liberalism"

# Generate a cheatsheet
> /cheatsheet economics

# Switch language
> /language French
> /language English
> /language auto

# Review weaknesses
> /weaknesses economics

# Recall training
> /recall economics

# Analyze an exam
> /analyze_exam ~/.codewhale/exams/math_2023.pdf math_2023

# Generate a study plan
> /generate_study_plan math_2023 student1 7

# Compare exams
> /compare_exams math_2023 math_2024 physics_2023

```

## Dashboard

The dashboard has a FastAPI backend (`tutor_dashboard.py`) and a React (Vite)
frontend (`dashboard/`). `./install.sh` installs the Python dependencies into a
private venv and copies the frontend into `~/.codewhale/tutor/dashboard/`.

```bash
# Terminal 1: start Codewhale (the tutor MCP servers are auto-discovered)
codewhale

# Terminal 2: start the dashboard API (serves /api on :8000)
~/.codewhale/tutor/.venv/bin/python ~/.codewhale/tutor/tutor_dashboard.py

# Terminal 3: start the React frontend (proxies /api to :8000)
cd ~/.codewhale/tutor/dashboard && npm install && npm run dev
```

Open http://localhost:5173 to view student progress, exam analytics, and
learning insights. For a production build, run `npm run build` in the dashboard
directory.