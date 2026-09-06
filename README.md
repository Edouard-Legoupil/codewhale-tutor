# codewhale-tutor

A [codewhale](https://codewhale.net/en) set up designed for students to benefit from advanced AI tutoring within your own computer - and with the model of your choice.

## Features

 * Multiple syllabus types → process_syllabus handles any subject from PDFs
 * Build tutoring plans → Automatic concept extraction and curriculum mapping
 * Socratic approach → metacognitive_tutor prompt with questioning framework
 * Metacognition focus → Specialized prompts for self-reflection and strategy awareness
 * Track student responses → tracking hook  with full response history
 * Return to theory → Weakness detection triggers concept review
 * Learn from exams → process_exam identifies tested concepts and frequencies
 * Track learning stage → current_stage and concept_mastery in progress data
 * Multi-language → Language detection and support throughout
 * Cheatsheets → generate cheatsheet for each syllabus
 * Recall support → Cheatsheets and spaced repetition system
 * Adaptive → Adjusts based on mastery, confidence, and learning style
 * Subject-Specific Skills → Math problem-solving, economic analysis, social science critical thinking
 * Web Dashboard → Visualize student progress, concept mastery, exam analytics
 * Sophisticated Exam Analysis → Question classification, difficulty estimation, Bloom's taxonomy mapping, study plan generation


## User journey

1. **Drop documents.** Put syllabi and exams in `~/.codewhale/syllabi` and
   `~/.codewhale/exams` as Markdown (`.md`), plain text (`.txt`), or PDF. One file
   can describe one or more syllabi, and you can keep adding files over time.
2. **The library builds itself.** The dashboard — or the tutor agent via
   `sync_library` — scans both folders, organises the concepts and objectives into
   a per-syllabus registry, and infers two useful artefacts for every syllabus:
   a **cheatsheet** (`~/.codewhale/cheatsheets/<id>_cheatsheet.md`) and an
   **inferred mock exam** (`~/.codewhale/exams/<id>_mock.json`).
3. **Keep adding documents.** Adding a file to the syllabus folder updates the
   registry and regenerates the related cheatsheet + mock exam. Adding a file to the
   exam folder links it to its syllabus and updates the syllabus, the exam list, and
   the cheatsheet's exam tips.
4. **Everything is visible in the dashboard** at `http://localhost:5173`: syllabi
   (concepts, objectives, sources), generated cheatsheets, real exams and inferred
   mock exams, plus student progress.

### Document conventions

- By default a syllabus's `id` is its filename stem. Two files merge into one
  syllabus when they share an `id`.
- Optional front matter at the top of a Markdown file overrides the defaults and
  lets you be explicit:

  ````
  ---
  id: algebra3            # syllabus id (merge key)
  name: Algebra III       # display name
  language: French        # auto-detected if omitted
  ---
  # ...course content (# = module, ## = concept)…
  ````

- An exam file links to a syllabus with front matter `syllabus_id: algebra3`; without
  it, the library matches it to the syllabus whose concepts overlap the most.


## Install / Uninstall

```bash
## First install codewhale
curl -fsSL https://codewhale.net/install.sh | sh
codewhale doctor

## Once configured with your inferrence provider, stop codewhale and Clone this repo
git clone https://github.com/Edouard-Legoupil/codewhale-tutor.git

# Get in the folder
cd codewhale-tutor
# One command installs the MCP servers, skills, and dashboard backend
# into ~/.codewhale using Codewhale's real conventions.
./install.sh

# If needed, remove everything install.sh added (keeps student data).
./uninstall.sh

# If needed, remove everything including student data.
./uninstall.sh --purge-data
```

After installing, restart Codewhale so it re-reads `~/.codewhale/mcp.json`,
then drop syllabus/exam PDFs into `~/.codewhale/syllabi` and
`~/.codewhale/exams`. Start tutoring with the `metacognitive-tutor` skill
(`/skill metacognitive-tutor`).


# Working with the Tutor

Tutoring is driven by the `metacognitive-tutor` skill plus four MCP servers.
There are no bespoke slash commands — the tutor agent calls these tools for you
when you ask in plain language.


1. Put syllabus/exam documents (`.md`, `.txt`, or PDF) in:
     ~/.codewhale/syllabi
     ~/.codewhale/exams

2. Start Codewhale and activate the tutor:

```bash
/skill metacognitive-tutor
```

3. Ask naturally, e.g.:
     "Sync my library and plan my revision."
     "I'm stuck on diagonalisation — quiz me Socratically."
     "Analyze proba_2023.pdf and make a 7-day study plan."

The library rebuilds itself from the folders (see the user journey above), so adding
or editing a document is enough — the dashboard re-syncs automatically, or the agent
can call `sync_library`.


Tools available to the tutor (`syllabus_processor` MCP server):

- `sync_library` — rebuild the registry, cheatsheets, and inferred mock exams from
  the documents in `~/.codewhale/syllabi` and `~/.codewhale/exams`.
- `process_syllabus` — extract concepts and objectives from a syllabus PDF or Markdown file.
- `process_exam` — extract questions and tested concepts from an exam PDF.
- `generate_cheatsheet` — write a Markdown cheatsheet for a syllabus or concept.
- `get_student_progress` / `update_student_progress` — read/write mastery.
- `identify_weaknesses` — list concepts with mastery below 60%.
- `suggest_next_topic` — recommend what to study next.
- `schedule_review` / `get_due_reviews` — spaced-repetition scheduling.
- `get_learning_objectives` — list a syllabus's competencies (Compétences visées).
- `record_attempt` — log a practice attempt with confidence + correctness.
- `get_error_patterns` — surface recurring error types (sign, jacobian, units, …).
- `get_calibration` — compare predicted confidence to actual accuracy.
- `diagnose_root_cause` — trace a weak concept back to its unmet prerequisite.
- `generate_syllabus_skill` — generate a syllabus-specific study-guide skill from the
  processed syllabus (its modules, topics, prerequisites, and competencies).
- `list_syllabus_skills` / `remove_syllabus_skill` — list and remove generated
  per-syllabus skills.

Tools from the `exam_analyzer` MCP server:

- `analyze_exam` — classify questions, estimate difficulty, map Bloom's levels.
- `classify_question` — classify a single question.
- `generate_study_plan` — build a day-by-day plan from an exam analysis.
- `compare_exams` — compare difficulty and coverage across exams.

Tools from the `math_engine` MCP server (SymPy):

- `check_math` — simplify/evaluate an expression and check it against an expected
  result (supports derivatives, integrals, and eigenvalues).
- `solve_equation` — solve an equation for a variable.
- `sanity_check` — flag implausible results (probability out of range, negative variance, …).

Tools from the `practice_engine` MCP server:

- `generate_exercises` — generate parameterized practice problems per concept.
- `grade_answer` — grade a student's answer against the expected result.
- `generate_mock_exam` — build a timed mock exam from a syllabus.
- `generate_bug_hunt` — produce a worked solution with a planted error to find.

Progress is written to `~/.codewhale/tutor_progress/` and can be inspected in the
dashboard at `http://localhost:5173`. The subject skills (`math-problem-solver`,
`linear-algebra`, `probability-statistics`, `python-programming`,
`data-visualization`, `exam-technique`, `economics-analysis`, `social-science-analysis`) load
automatically when their domain is relevant.

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

The dashboard keeps a single **library registry** at `~/.codewhale/registry.json`.
It re-syncs from the `syllabi/` and `exams/` folders automatically (on startup, on a
poll every few seconds, and via the **Sync now** button), so documents you drop in
appear without a restart. The same engine is shared with the `sync_library` MCP tool,
so the agent and the dashboard always agree on the state of the library.


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
```

## File Structure Summary

```text
~/.codewhale/
├── mcp.json                          # MCP servers (syllabus_processor, exam_analyzer, math_engine, practice_engine)
├── skills/
│   ├── metacognitive-tutor/SKILL.md
│   ├── math-problem-solver/SKILL.md
│   ├── linear-algebra/SKILL.md
│   ├── probability-statistics/SKILL.md
│   ├── python-programming/SKILL.md
│   ├── data-visualization/SKILL.md
│   ├── exam-technique/SKILL.md
│   ├── economics-analysis/SKILL.md
│   └── social-science-analysis/SKILL.md
├── tutor/
│   ├── .venv/                        # private Python environment
│   ├── library.py                    # shared ingestion engine + registry
│   ├── syllabus_processor_mcp.py     # MCP server
│   ├── exam_analyzer_mcp.py          # MCP server
│   ├── math_engine_mcp.py            # MCP server (SymPy)
│   ├── practice_engine_mcp.py        # MCP server (exercises/grading)
│   ├── tutor_dashboard.py            # dashboard API
│   ├── dashboard/                    # React (Vite) frontend
│   └── ...                           # helper scripts
├── registry.json                     # library index (syllabi, exams, sources)
├── syllabi/                          # organised syllabus JSON (+ raw sources)
├── exams/                            # analysed + inferred mock exam JSON
├── cheatsheets/                      # generated cheatsheets
└── tutor_progress/                   # student progress (unified)
```
