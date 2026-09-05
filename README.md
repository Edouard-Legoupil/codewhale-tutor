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

## Install

```bash
# 1. Install dependencies
pip install PyPDF2 markdown

# 2. Create directories
mkdir -p ~/.codewhale/{syllabi,exams,progress,cheatsheets,skills/education}

# 3. Place syllabus PDFs in the syllabi directory
cp ~/Downloads/economics_101.pdf ~/.codewhale/syllabi/
cp ~/Downloads/calculus_201.pdf ~/.codewhale/syllabi/

# 4. Place exam PDFs in the exams directory  
cp ~/Downloads/economics_exam_2023.pdf ~/.codewhale/exams/
cp ~/Downloads/calculus_exam_2023.pdf ~/.codewhale/exams/

# 5. Start CodeWhale in tutor mode
codewhale --agent metacognitive_tutor
```

## File Structure Summary

```text
~/.codewhale/
├── config.toml                       # Main configuration
├── agents/
│   └── metacognitive_tutor.toml      # Tutor agent config
├── prompts/
│   └── metacognitive_tutor.md        # Tutor system prompt
├── syllabi/
│   ├── economics_101.json           # Processed syllabus
│   └── calculus_201.json
├── exams/
│   ├── economics_exam_2023.json     # Processed exam
│   └── calculus_exam_2023.json
├── progress/
│   ├── student1_economics.json      # Student progress
│   └── student1_calculus.json
├── cheatsheets/
│   ├── economics_cheatsheet.md      # Generated cheatsheets
│   └── calculus_cheatsheet.md
├── skills/education/
│   ├── socratic_questioning.md
│   ├── metacognitive_reflection.md
│   └── spaced_repetition.md
└── mcp_servers/
    └── syllabus_processor_mcp.py     # MCP server
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

```bash
# Install Python dependencies
pip install fastapi uvicorn recharts PyPDF2 pandas numpy

# Install Node.js dependencies for dashboard
cd dashboard
npm install recharts axios
npm run dev  # For development

# For production build
npm run build
```

Start the Services

```bash
# Terminal 1: Start CodeWhale with MCP servers
codewhale --agent metacognitive_tutor

# Terminal 2: Start the dashboard API
python tutor_dashboard.py

# Terminal 3: Start the React dashboard (development)
cd dashboard && npm run dev
```

Navigate to http://localhost:5173
View student progress, exam analytics, and learning insights