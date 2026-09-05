#!/usr/bin/env python3
"""
MCP server for processing syllabi, exams, and educational materials.

Uses the modern FastMCP API (mcp.server.fastmcp.FastMCP).
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict

import PyPDF2
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codewhale-syllabus-processor")


# --- Data structures ---------------------------------------------------------
@dataclass
class Concept:
    name: str
    description: str
    prerequisites: List[str]
    difficulty: int  # 1-5
    exam_frequency: int
    common_misconceptions: List[str]
    related_questions: List[str]


@dataclass
class Syllabus:
    id: str
    name: str
    language: str
    concepts: List[Concept]
    learning_objectives: List[str]
    estimated_hours: int
    prerequisites: List[str]


@dataclass
class Exam:
    id: str
    syllabus_id: str
    questions: List[Dict]
    concepts_tested: List[str]
    difficulty_distribution: Dict[str, int]


@dataclass
class StudentProgress:
    student_id: str
    syllabus_id: str
    current_stage: int  # 0-100
    concept_mastery: Dict[str, float]  # 0-1
    response_history: List[Dict]
    weaknesses: List[str]
    last_session: datetime
    cheatsheets_accessed: List[str]


# --- Storage (single canonical progress directory) ---------------------------
SYLLABI_DIR = Path.home() / ".codewhale" / "syllabi"
EXAMS_DIR = Path.home() / ".codewhale" / "exams"
PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"
CHEATSHEETS_DIR = Path.home() / ".codewhale" / "cheatsheets"

for _dir in (SYLLABI_DIR, EXAMS_DIR, PROGRESS_DIR, CHEATSHEETS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


# --- Helpers -----------------------------------------------------------------
def _read_pdf_text(file_path: Path) -> str:
    """Extract text from a PDF, raising a readable error on failure."""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "".join(page.extract_text() or "" for page in reader.pages)


def _detect_language(text: str) -> str:
    if re.search(r"[éèêëàâäôûüîïç]", text):
        return "French"
    if re.search(r"[ñáéíóúü]", text):
        return "Spanish"
    if re.search(r"[äöüß]", text):
        return "German"
    if re.search(r"[가-힣]", text):
        return "Korean"
    if re.search(r"[一-龯]", text):
        return "Chinese"
    return "English"


def _new_progress(student_id: str, syllabus_id: str) -> dict:
    return {
        "student_id": student_id,
        "syllabus_id": syllabus_id,
        "current_stage": 0,
        "concept_mastery": {},
        "response_history": [],
        "weaknesses": [],
        "cheatsheets_accessed": [],
        "last_session": None,
    }


def _load_progress(student_id: str, syllabus_id: str) -> dict:
    """Load a progress file, merging into the canonical schema if needed."""
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if not progress_file.exists():
        return _new_progress(student_id, syllabus_id)

    with open(progress_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    base = _new_progress(student_id, syllabus_id)
    for key, default in base.items():
        data.setdefault(key, default)
    return data


def _save_progress(progress: dict) -> None:
    progress_file = PROGRESS_DIR / f"{progress['student_id']}_{progress['syllabus_id']}.json"
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, default=str)


# --- Tools -------------------------------------------------------------------
@mcp.tool()
def process_syllabus(file_path: str, syllabus_id: str, language: str = "auto") -> str:
    """Extract concepts and learning objectives from a syllabus PDF.

    Args:
        file_path: Path to the PDF syllabus.
        syllabus_id: Unique ID for this syllabus.
        language: Language of the syllabus (auto-detected when omitted).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return f"❌ File not found: {file_path}"

    try:
        text = _read_pdf_text(file_path)
    except Exception as e:  # noqa: BLE001
        return f"❌ Error reading PDF: {e}"

    if language == "auto":
        language = _detect_language(text)

    concepts: List[Concept] = []
    chapter_pattern = r"(?:Chapter|Topic|Module|Unit|Section)\s+(\d+):?\s*([^\n]+)"
    chapters = re.findall(chapter_pattern, text, re.IGNORECASE)

    for i, (num, title) in enumerate(chapters):
        concepts.append(Concept(
            name=title.strip(),
            description=f"Chapter {num}: {title.strip()}",
            prerequisites=[],
            difficulty=1 if i < 3 else 2 if i < 6 else 3,
            exam_frequency=0,
            common_misconceptions=[],
            related_questions=[],
        ))

    objective_pattern = r"(?:Learning Objective|Objective|Goal)\s*:?\s*([^\n]+)"
    learning_objectives = [o.strip() for o in re.findall(objective_pattern, text, re.IGNORECASE)]

    if not concepts:
        sections = re.split(r"\n\s*(?=\d+\.\s|\w+\.\s)", text)
        for i, section in enumerate(sections[:10]):
            lines = section.strip().split("\n")
            if lines:
                concepts.append(Concept(
                    name=lines[0][:50].strip(),
                    description=lines[0][:200].strip(),
                    prerequisites=[],
                    difficulty=1 if i < 3 else 2,
                    exam_frequency=0,
                    common_misconceptions=[],
                    related_questions=[],
                ))

    syllabus = Syllabus(
        id=syllabus_id,
        name=file_path.stem,
        language=language,
        concepts=concepts,
        learning_objectives=learning_objectives,
        estimated_hours=len(concepts) * 2,
        prerequisites=[],
    )

    with open(SYLLABI_DIR / f"{syllabus_id}.json", "w", encoding="utf-8") as f:
        json.dump(asdict(syllabus), f, indent=2, default=str)

    _generate_cheatsheet(syllabus_id, language, [])

    return f"""
✅ **Syllabus Processed Successfully!**

**ID:** {syllabus_id}
**Name:** {syllabus.name}
**Language:** {syllabus.language}
**Concepts Identified:** {len(concepts)}
**Learning Objectives:** {len(learning_objectives)}
**Estimated Study Hours:** {syllabus.estimated_hours}

📚 **First 5 Concepts:**
{chr(10).join(f"  - {c.name}" for c in concepts[:5])}

📝 **Generated Cheatsheet:** ~/.codewhale/cheatsheets/{syllabus_id}_cheatsheet.md

Ready to start tutoring!
"""


@mcp.tool()
def process_exam(file_path: str, syllabus_id: str, exam_id: str) -> str:
    """Extract questions and tested concepts from an exam PDF.

    Args:
        file_path: Path to the exam PDF.
        syllabus_id: Associated syllabus ID.
        exam_id: Unique ID for this exam.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return f"❌ File not found: {file_path}"

    try:
        text = _read_pdf_text(file_path)
    except Exception as e:  # noqa: BLE001
        return f"❌ Error reading PDF: {e}"

    questions = []
    question_pattern = r"(\d+)[\.\)]\s*([^\n]+(?:\n[^a-zA-Z0-9][^\n]+)*)"
    matches = re.findall(question_pattern, text)
    concepts_tested = set()

    for num, qtext in matches:
        q_lower = qtext.lower()
        if "define" in q_lower or "what is" in q_lower:
            concept = "Definition"
        elif "compare" in q_lower or "contrast" in q_lower:
            concept = "Comparison"
        elif "explain" in q_lower or "describe" in q_lower:
            concept = "Explanation"
        elif "solve" in q_lower or "calculate" in q_lower:
            concept = "Problem Solving"
        else:
            concept = "General"

        questions.append({
            "number": int(num),
            "text": qtext.strip(),
            "concept": concept,
            "difficulty": "medium",
        })
        concepts_tested.add(concept)

    exam = Exam(
        id=exam_id,
        syllabus_id=syllabus_id,
        questions=questions,
        concepts_tested=list(concepts_tested),
        difficulty_distribution={"easy": 0, "medium": len(questions) // 2, "hard": len(questions) // 3},
    )

    with open(EXAMS_DIR / f"{exam_id}.json", "w", encoding="utf-8") as f:
        json.dump(asdict(exam), f, indent=2, default=str)

    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if syllabus_file.exists():
        with open(syllabus_file, "r", encoding="utf-8") as f:
            syllabus_data = json.load(f)
        for concept_name in concepts_tested:
            for concept in syllabus_data.get("concepts", []):
                if concept["name"] == concept_name:
                    concept["exam_frequency"] = concept.get("exam_frequency", 0) + 1
        with open(syllabus_file, "w", encoding="utf-8") as f:
            json.dump(syllabus_data, f, indent=2)

    return f"""
✅ **Exam Processed Successfully!**

**ID:** {exam_id}
**Syllabus:** {syllabus_id}
**Questions Found:** {len(questions)}
**Concepts Tested:** {', '.join(concepts_tested)}

📊 **Question Distribution:**
{chr(10).join(f"  - Q{num}: {qtext[:50]}..." for num, qtext in matches[:5])}

💡 **Useful For:** Identifying which concepts students struggle with most.
"""


def _generate_cheatsheet(syllabus_id: str, language: str, specific_concepts: List[str]) -> str:
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if not syllabus_file.exists():
        return f"❌ Syllabus {syllabus_id} not found"

    with open(syllabus_file, "r", encoding="utf-8") as f:
        syllabus_data = json.load(f)

    concepts = syllabus_data.get("concepts", [])
    if specific_concepts:
        concepts = [c for c in concepts if c["name"] in specific_concepts]

    cheatsheet = f"""# 📚 {syllabus_data['name']} - Cheatsheet

**Language:** {language}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Total Concepts:** {len(concepts)}

---

## 🎯 Key Concepts

"""

    for i, concept in enumerate(concepts):
        difficulty = concept.get("difficulty", 1)
        difficulty_emoji = "🟢" if difficulty <= 2 else "🟡" if difficulty <= 3 else "🔴"
        cheatsheet += f"""
### {i + 1}. {concept['name']}
{difficulty_emoji} Difficulty: {difficulty}/5

**Description:** {concept.get('description', 'No description available')}

**Prerequisites:** {', '.join(concept.get('prerequisites', ['None'])) or 'None'}

**Exam Frequency:** {concept.get('exam_frequency', 0)} times

**Common Misconceptions:**
{chr(10).join(f"  - {m}" for m in concept.get('common_misconceptions', ['None identified yet']))}

---
"""

    if syllabus_data.get("learning_objectives"):
        cheatsheet += "\n## 📖 Learning Objectives\n\n"
        for obj in syllabus_data["learning_objectives"]:
            cheatsheet += f"- {obj}\n"

    cheatsheet += "\n## 💡 Exam Tips\n\n"

    from collections import Counter
    all_exam_concepts = []
    for exam_file in EXAMS_DIR.glob("*.json"):
        if exam_file.stem.endswith("_analysis"):
            continue
        try:
            with open(exam_file, "r", encoding="utf-8") as f:
                exam_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if exam_data.get("syllabus_id") == syllabus_id:
            all_exam_concepts.extend(exam_data.get("concepts_tested", []))

    if all_exam_concepts:
        cheatsheet += "Based on past exams, focus on:\n\n"
        for concept, count in Counter(all_exam_concepts).most_common(5):
            cheatsheet += f"- **{concept}** (appears in {count} exam(s))\n"
    else:
        cheatsheet += "No exam data available yet. Take a practice exam to generate tips!"

    cheatsheet += """

## 🧠 Mnemonic Devices

*Create your own memory aids! Here are some techniques:*

- **Acronyms:** Create a word from the first letters
- **Visualization:** Create a mental image
- **Chunking:** Group information into smaller pieces
- **Story Method:** Create a narrative connecting concepts

"""

    cheatsheet_file = CHEATSHEETS_DIR / f"{syllabus_id}_cheatsheet.md"
    with open(cheatsheet_file, "w", encoding="utf-8") as f:
        f.write(cheatsheet)

    return f"""
✅ **Cheatsheet Generated!**

**Location:** {cheatsheet_file}
**Concepts Covered:** {len(concepts)}
**Language:** {language}
"""


@mcp.tool()
def generate_cheatsheet(syllabus_id: str, concepts: list = None, language: str = "English") -> str:
    """Generate a cheatsheet for a syllabus or specific concepts.

    Args:
        syllabus_id: Syllabus ID.
        concepts: Specific concepts to include (optional).
        language: Output language.
    """
    return _generate_cheatsheet(syllabus_id, language, concepts or [])


@mcp.tool()
def get_student_progress(student_id: str, syllabus_id: str) -> str:
    """Get current progress for a student on a syllabus."""
    progress = _load_progress(student_id, syllabus_id)

    concept_mastery = progress.get("concept_mastery", {})
    if not concept_mastery:
        return f"📊 No progress found for student {student_id} on syllabus {syllabus_id}. Let's start learning!"

    avg_mastery = sum(concept_mastery.values()) / len(concept_mastery)
    next_topic = _suggest_next_topic(student_id, syllabus_id)

    return f"""
📊 **Student Progress Report**

**Student:** {student_id}
**Syllabus:** {syllabus_id}
**Current Stage:** {progress.get('current_stage', 0):.0f}%
**Overall Mastery:** {avg_mastery:.1%}

**Concept Mastery:**
{chr(10).join(f"  - {concept}: {score:.1%}" for concept, score in concept_mastery.items())}

**Weaknesses Identified:**
{chr(10).join(f"  - {w}" for w in progress.get('weaknesses', ['None identified']))}

**Cheatsheets Accessed:** {len(progress.get('cheatsheets_accessed', []))}

💡 **Next Topic:** {next_topic}
"""


@mcp.tool()
def update_student_progress(
    student_id: str,
    syllabus_id: str,
    concept: str,
    mastery: float,
    response: str = "",
    correction: str = "",
) -> str:
    """Update a student's progress after a learning session.

    Args:
        student_id: Student identifier.
        syllabus_id: Syllabus identifier.
        concept: Concept being assessed.
        mastery: Mastery score from 0.0 to 1.0.
        response: The student's response.
        correction: Teacher correction, if any.
    """
    progress = _load_progress(student_id, syllabus_id)

    progress["concept_mastery"][concept] = mastery
    progress["last_session"] = datetime.now().isoformat()
    progress["response_history"].append({
        "concept": concept,
        "response": response,
        "mastery": mastery,
        "correction": correction,
        "timestamp": datetime.now().isoformat(),
    })

    if mastery < 0.6:
        if concept not in progress["weaknesses"]:
            progress["weaknesses"].append(concept)
    elif concept in progress["weaknesses"]:
        progress["weaknesses"].remove(concept)

    mastered = [c for c, m in progress["concept_mastery"].items() if m >= 0.7]
    total = len(progress["concept_mastery"])
    if total:
        progress["current_stage"] = (len(mastered) / total) * 100

    _save_progress(progress)

    return f"""
✅ **Progress Updated!**

**Student:** {student_id}
**Concept:** {concept}
**Mastery:** {mastery:.1%}
**Stage:** {progress['current_stage']:.0f}%

📝 **Learning Summary:**
- Concepts mastered: {len(mastered)}
- Weaknesses: {len(progress['weaknesses'])}
- Total responses: {len(progress['response_history'])}

{'🔴 Keep practicing this concept!' if mastery < 0.6 else '🟢 Great job! Ready to move on!'}
"""


@mcp.tool()
def identify_weaknesses(student_id: str, syllabus_id: str) -> str:
    """Identify a student's weak concepts for a syllabus."""
    progress = _load_progress(student_id, syllabus_id)
    concept_mastery = progress.get("concept_mastery", {})

    weak_concepts = sorted(
        [(c, m) for c, m in concept_mastery.items() if m < 0.6],
        key=lambda x: x[1],
    )

    if not weak_concepts:
        return "🎉 No weaknesses identified! Keep up the great work!"

    return f"""
🔴 **Weaknesses Identified**

**Student:** {student_id}
**Syllabus:** {syllabus_id}

**Concepts Needing Improvement:**
{chr(10).join(f"  - {concept}: {score:.1%} mastery" for concept, score in weak_concepts[:5])}

💡 **Recommendation:** Focus on these concepts in your next session.
Start a targeted session on: {weak_concepts[0][0]}
"""


def _suggest_next_topic(student_id: str, syllabus_id: str) -> str:
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if not syllabus_file.exists():
        return "Syllabus not found"

    with open(syllabus_file, "r", encoding="utf-8") as f:
        syllabus_data = json.load(f)
    concepts = syllabus_data.get("concepts", [])

    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if not progress_file.exists():
        return f"Start with: {concepts[0]['name'] if concepts else 'Introduction'}"

    progress = _load_progress(student_id, syllabus_id)

    weaknesses = progress.get("weaknesses", [])
    if weaknesses:
        return f"Review: {weaknesses[0]} (weakness)"

    mastery = progress.get("concept_mastery", {})
    for concept in concepts:
        concept_name = concept["name"]
        if concept_name not in mastery or mastery[concept_name] < 0.7:
            return concept_name

    return "🎉 All concepts mastered! Consider taking the final exam."


@mcp.tool()
def suggest_next_topic(student_id: str, syllabus_id: str) -> str:
    """Suggest the next topic a student should study."""
    return _suggest_next_topic(student_id, syllabus_id)


if __name__ == "__main__":
    mcp.run()
