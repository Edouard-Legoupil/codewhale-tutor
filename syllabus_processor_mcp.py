#!/usr/bin/env python3
"""
MCP server for processing syllabi, exams, and educational materials
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import PyPDF2
import markdown
from dataclasses import dataclass, asdict

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

app = Server("codewhale-syllabus-processor")

# Data structures
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

# Global storage
SYLLABI_DIR = Path.home() / ".codewhale" / "syllabi"
EXAMS_DIR = Path.home() / ".codewhale" / "exams"
PROGRESS_DIR = Path.home() / ".codewhale" / "progress"
CHEATSHEETS_DIR = Path.home() / ".codewhale" / "cheatsheets"

SYLLABI_DIR.mkdir(parents=True, exist_ok=True)
EXAMS_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
CHEATSHEETS_DIR.mkdir(parents=True, exist_ok=True)

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="process_syllabus",
            description="Process a syllabus PDF and extract concepts, learning objectives, and structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the PDF syllabus"},
                    "language": {"type": "string", "description": "Language of the syllabus (auto-detected if not provided)"},
                    "syllabus_id": {"type": "string", "description": "Unique ID for this syllabus"}
                },
                "required": ["file_path", "syllabus_id"]
            }
        ),
        types.Tool(
            name="process_exam",
            description="Process an exam PDF to extract questions and identify concepts tested",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the exam PDF"},
                    "syllabus_id": {"type": "string", "description": "Associated syllabus ID"},
                    "exam_id": {"type": "string", "description": "Unique ID for this exam"}
                },
                "required": ["file_path", "syllabus_id", "exam_id"]
            }
        ),
        types.Tool(
            name="generate_cheatsheet",
            description="Generate a cheatsheet for a specific syllabus or concept",
            inputSchema={
                "type": "object",
                "properties": {
                    "syllabus_id": {"type": "string", "description": "Syllabus ID"},
                    "concepts": {"type": "array", "items": {"type": "string"}, "description": "Specific concepts to include (optional)"},
                    "language": {"type": "string", "description": "Output language"}
                },
                "required": ["syllabus_id"]
            }
        ),
        types.Tool(
            name="get_student_progress",
            description="Get current progress for a student",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "syllabus_id": {"type": "string"}
                },
                "required": ["student_id", "syllabus_id"]
            }
        ),
        types.Tool(
            name="update_student_progress",
            description="Update student progress after a learning session",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "syllabus_id": {"type": "string"},
                    "concept": {"type": "string"},
                    "mastery": {"type": "number", "minimum": 0, "maximum": 1},
                    "response": {"type": "string"},
                    "correction": {"type": "string", "description": "Teacher correction if needed"}
                },
                "required": ["student_id", "syllabus_id", "concept", "mastery"]
            }
        ),
        types.Tool(
            name="identify_weaknesses",
            description="Identify weak concepts for a student based on their performance",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "syllabus_id": {"type": "string"}
                },
                "required": ["student_id", "syllabus_id"]
            }
        ),
        types.Tool(
            name="suggest_next_topic",
            description="Suggest the next topic to study based on student progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "syllabus_id": {"type": "string"}
                },
                "required": ["student_id", "syllabus_id"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    
    if name == "process_syllabus":
        return await process_syllabus(arguments)
    
    elif name == "process_exam":
        return await process_exam(arguments)
    
    elif name == "generate_cheatsheet":
        return await generate_cheatsheet(arguments)
    
    elif name == "get_student_progress":
        return await get_student_progress(arguments)
    
    elif name == "update_student_progress":
        return await update_student_progress(arguments)
    
    elif name == "identify_weaknesses":
        return await identify_weaknesses(arguments)
    
    elif name == "suggest_next_topic":
        return await suggest_next_topic(arguments)
    
    return [types.TextContent(type="text", text="Unknown tool")]

async def process_syllabus(args: dict):
    """Extract structured information from a syllabus PDF"""
    file_path = Path(args["file_path"])
    syllabus_id = args["syllabus_id"]
    language = args.get("language", "auto")
    
    if not file_path.exists():
        return [types.TextContent(type="text", text=f"❌ File not found: {file_path}")]
    
    # Extract text from PDF
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error reading PDF: {str(e)}")]
    
    # Language detection
    if language == "auto":
        # Simple language detection based on character patterns
        if re.search(r'[éèêëàâäôûüîïç]', text):
            language = "French"
        elif re.search(r'[ñáéíóúü]', text):
            language = "Spanish"
        elif re.search(r'[äöüß]', text):
            language = "German"
        elif re.search(r'[가-힣]', text):
            language = "Korean"
        elif re.search(r'[一-龯]', text):
            language = "Chinese"
        else:
            language = "English"
    
    # Extract concepts (simplified - in production, use an LLM for this)
    # For now, we'll look for patterns like "Learning Objective", "Topic", "Chapter"
    concepts = []
    learning_objectives = []
    
    # Find chapter/section headers
    chapter_pattern = r'(?:Chapter|Topic|Module|Unit|Section)\s+(\d+):?\s*([^\n]+)'
    chapters = re.findall(chapter_pattern, text, re.IGNORECASE)
    
    for i, (num, title) in enumerate(chapters):
        concept = Concept(
            name=title.strip(),
            description=f"Chapter {num}: {title.strip()}",
            prerequisites=[],
            difficulty=1 if i < 3 else 2 if i < 6 else 3,
            exam_frequency=0,
            common_misconceptions=[],
            related_questions=[]
        )
        concepts.append(concept)
    
    # Find learning objectives
    objective_pattern = r'(?:Learning Objective|Objective|Goal)\s*:?\s*([^\n]+)'
    objectives = re.findall(objective_pattern, text, re.IGNORECASE)
    learning_objectives = [o.strip() for o in objectives]
    
    # If no chapters found, create generic concepts from sections
    if not concepts:
        # Split by common section headers
        sections = re.split(r'\n\s*(?=\d+\.\s|\w+\.\s)', text)
        for i, section in enumerate(sections[:10]):  # Limit to 10 sections
            lines = section.strip().split('\n')
            if lines:
                concept = Concept(
                    name=lines[0][:50].strip(),
                    description=lines[0][:200].strip(),
                    prerequisites=[],
                    difficulty=1 if i < 3 else 2,
                    exam_frequency=0,
                    common_misconceptions=[],
                    related_questions=[]
                )
                concepts.append(concept)
    
    # Save syllabus data
    syllabus = Syllabus(
        id=syllabus_id,
        name=file_path.stem,
        language=language,
        concepts=concepts,
        learning_objectives=learning_objectives,
        estimated_hours=len(concepts) * 2,  # Rough estimate
        prerequisites=[]
    )
    
    # Save to file
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    with open(syllabus_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(syllabus), f, indent=2, default=str)
    
    # Generate initial cheatsheet
    await generate_cheatsheet({"syllabus_id": syllabus_id, "language": language})
    
    return [types.TextContent(type="text", text=f"""
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

Ready to start tutoring! Use: `/tutor start {syllabus_id}`
""")]

async def process_exam(args: dict):
    """Extract questions and concepts from an exam PDF"""
    file_path = Path(args["file_path"])
    syllabus_id = args["syllabus_id"]
    exam_id = args["exam_id"]
    
    if not file_path.exists():
        return [types.TextContent(type="text", text=f"❌ File not found: {file_path}")]
    
    # Extract text from PDF
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error reading PDF: {str(e)}")]
    
    # Find questions (simplified - looks for numbered items)
    questions = []
    question_pattern = r'(\d+)[\.\)]\s*([^\n]+(?:\n[^a-zA-Z0-9][^\n]+)*)'
    matches = re.findall(question_pattern, text)
    
    concepts_tested = set()
    
    for num, qtext in matches:
        # Attempt to identify concept
        concept = "General"
        if "define" in qtext.lower() or "what is" in qtext.lower():
            concept = "Definition"
        elif "compare" in qtext.lower() or "contrast" in qtext.lower():
            concept = "Comparison"
        elif "explain" in qtext.lower() or "describe" in qtext.lower():
            concept = "Explanation"
        elif "solve" in qtext.lower() or "calculate" in qtext.lower():
            concept = "Problem Solving"
        
        questions.append({
            "number": int(num),
            "text": qtext.strip(),
            "concept": concept,
            "difficulty": "medium"  # Default
        })
        concepts_tested.add(concept)
    
    # Save exam data
    exam = Exam(
        id=exam_id,
        syllabus_id=syllabus_id,
        questions=questions,
        concepts_tested=list(concepts_tested),
        difficulty_distribution={"easy": 0, "medium": len(questions)//2, "hard": len(questions)//3}
    )
    
    exam_file = EXAMS_DIR / f"{exam_id}.json"
    with open(exam_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(exam), f, indent=2, default=str)
    
    # Update syllabus with exam data
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if syllabus_file.exists():
        with open(syllabus_file, 'r', encoding='utf-8') as f:
            syllabus_data = json.load(f)
        
        # Update concept exam frequencies
        for concept_name in concepts_tested:
            for concept in syllabus_data.get('concepts', []):
                if concept['name'] == concept_name:
                    concept['exam_frequency'] = concept.get('exam_frequency', 0) + 1
        
        with open(syllabus_file, 'w', encoding='utf-8') as f:
            json.dump(syllabus_data, f, indent=2)
    
    return [types.TextContent(type="text", text=f"""
✅ **Exam Processed Successfully!**

**ID:** {exam_id}
**Syllabus:** {syllabus_id}
**Questions Found:** {len(questions)}
**Concepts Tested:** {', '.join(concepts_tested)}

📊 **Question Distribution:**
{chr(10).join(f"  - Q{num}: {qtext[:50]}..." for num, qtext in matches[:5])}

💡 **Useful For:** Identifying which concepts students struggle with most.
""")]

async def generate_cheatsheet(args: dict):
    """Generate a cheatsheet for a syllabus"""
    syllabus_id = args["syllabus_id"]
    language = args.get("language", "English")
    specific_concepts = args.get("concepts", [])
    
    # Load syllabus
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    if not syllabus_file.exists():
        return [types.TextContent(type="text", text=f"❌ Syllabus {syllabus_id} not found")]
    
    with open(syllabus_file, 'r', encoding='utf-8') as f:
        syllabus_data = json.load(f)
    
    concepts = syllabus_data.get('concepts', [])
    if specific_concepts:
        concepts = [c for c in concepts if c['name'] in specific_concepts]
    
    # Generate cheatsheet in markdown
    cheatsheet = f"""# 📚 {syllabus_data['name']} - Cheatsheet

**Language:** {language}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**Total Concepts:** {len(concepts)}

---

## 🎯 Key Concepts

"""
    
    for i, concept in enumerate(concepts):
        difficulty_emoji = "🟢" if concept.get('difficulty', 1) <= 2 else "🟡" if concept.get('difficulty', 1) <= 3 else "🔴"
        cheatsheet += f"""
### {i+1}. {concept['name']}
{difficulty_emoji} Difficulty: {concept.get('difficulty', 'Unknown')}/5

**Description:** {concept.get('description', 'No description available')}

**Prerequisites:** {', '.join(concept.get('prerequisites', ['None'])) or 'None'}

**Exam Frequency:** {concept.get('exam_frequency', 0)} times

**Common Misconceptions:**
{chr(10).join(f"  - {m}" for m in concept.get('common_misconceptions', ['None identified yet']))}

---
"""
    
    # Add learning objectives
    if syllabus_data.get('learning_objectives'):
        cheatsheet += """
## 📖 Learning Objectives

"""
        for obj in syllabus_data['learning_objectives']:
            cheatsheet += f"- {obj}\n"
    
    # Add exam tips
    cheatsheet += """

## 💡 Exam Tips

"""
    # Load exam data
    exam_files = list(EXAMS_DIR.glob(f"*_{syllabus_id}.json"))
    if exam_files:
        cheatsheet += "Based on past exams, focus on:\n\n"
        # Collect concepts from exams
        all_exam_concepts = []
        for exam_file in exam_files:
            with open(exam_file, 'r', encoding='utf-8') as f:
                exam_data = json.load(f)
                all_exam_concepts.extend(exam_data.get('concepts_tested', []))
        
        from collections import Counter
        concept_counts = Counter(all_exam_concepts)
        for concept, count in concept_counts.most_common(5):
            cheatsheet += f"- **{concept}** (appears in {count} exam(s))\n"
    else:
        cheatsheet += "No exam data available yet. Take a practice exam to generate tips!"
    
    # Add mnemonic devices section
    cheatsheet += """

## 🧠 Mnemonic Devices

*Create your own memory aids! Here are some techniques:*

- **Acronyms:** Create a word from the first letters
- **Visualization:** Create a mental image
- **Chunking:** Group information into smaller pieces
- **Story Method:** Create a narrative connecting concepts

"""
    
    # Save cheatsheet
    cheatsheet_file = CHEATSHEETS_DIR / f"{syllabus_id}_cheatsheet.md"
    with open(cheatsheet_file, 'w', encoding='utf-8') as f:
        f.write(cheatsheet)
    
    return [types.TextContent(type="text", text=f"""
✅ **Cheatsheet Generated!**

**Location:** {cheatsheet_file}
**Concepts Covered:** {len(concepts)}
**Language:** {language}

Use `/cheatsheet {syllabus_id}` to view it anytime!
""")]

async def get_student_progress(args: dict):
    """Retrieve student progress"""
    student_id = args["student_id"]
    syllabus_id = args["syllabus_id"]
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    
    if not progress_file.exists():
        return [types.TextContent(type="text", text=f"📊 No progress found for student {student_id} on syllabus {syllabus_id}. Let's start learning!")]
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    
    # Calculate overall mastery
    concept_mastery = progress.get('concept_mastery', {})
    avg_mastery = sum(concept_mastery.values()) / len(concept_mastery) if concept_mastery else 0
    
    return [types.TextContent(type="text", text=f"""
📊 **Student Progress Report**

**Student:** {student_id}
**Syllabus:** {syllabus_id}
**Current Stage:** {progress.get('current_stage', 0)}/100%
**Overall Mastery:** {avg_mastery:.1%}

**Concept Mastery:**
{chr(10).join(f"  - {concept}: {score:.1%}" for concept, score in concept_mastery.items())}

**Weaknesses Identified:**
{chr(10).join(f"  - {w}" for w in progress.get('weaknesses', ['None identified']))}

**Cheatsheets Accessed:** {len(progress.get('cheatsheets_accessed', []))}

💡 **Next Topic:** {await suggest_next_topic(args) if progress.get('weaknesses') else 'Complete the current material first'}
""")]

async def update_student_progress(args: dict):
    """Update student progress after a learning session"""
    student_id = args["student_id"]
    syllabus_id = args["syllabus_id"]
    concept = args["concept"]
    mastery = args["mastery"]
    response = args.get("response", "")
    correction = args.get("correction", "")
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    
    # Load or create progress
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {
            "student_id": student_id,
            "syllabus_id": syllabus_id,
            "current_stage": 0,
            "concept_mastery": {},
            "response_history": [],
            "weaknesses": [],
            "cheatsheets_accessed": [],
            "last_session": None
        }
    
    # Update mastery
    progress["concept_mastery"][concept] = mastery
    progress["last_session"] = datetime.now().isoformat()
    
    # Record response
    progress["response_history"].append({
        "concept": concept,
        "response": response,
        "mastery": mastery,
        "correction": correction,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update weaknesses
    if mastery < 0.6:
        if concept not in progress["weaknesses"]:
            progress["weaknesses"].append(concept)
    else:
        if concept in progress["weaknesses"]:
            progress["weaknesses"].remove(concept)
    
    # Update stage (simple version)
    mastered_concepts = [c for c, m in progress["concept_mastery"].items() if m >= 0.7]
    total_concepts = len(progress["concept_mastery"])
    if total_concepts > 0:
        progress["current_stage"] = (len(mastered_concepts) / total_concepts) * 100
    
    # Save progress
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, default=str)
    
    return [types.TextContent(type="text", text=f"""
✅ **Progress Updated!**

**Student:** {student_id}
**Concept:** {concept}
**Mastery:** {mastery:.1%}
**Stage:** {progress['current_stage']:.0f}%

📝 **Learning Summary:**
- Concepts mastered: {len(mastered_concepts)}
- Weaknesses: {len(progress['weaknesses'])}
- Total responses: {len(progress['response_history'])}

{'🔴 Keep practicing this concept!' if mastery < 0.6 else '🟢 Great job! Ready to move on!'}
""")]

async def identify_weaknesses(args: dict):
    """Identify weak concepts for a student"""
    student_id = args["student_id"]
    syllabus_id = args["syllabus_id"]
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    
    if not progress_file.exists():
        return [types.TextContent(type="text", text="No progress data available yet.")]
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    
    weaknesses = progress.get('weaknesses', [])
    concept_mastery = progress.get('concept_mastery', {})
    
    # Sort by mastery
    weak_concepts = sorted(
        [(c, m) for c, m in concept_mastery.items() if m < 0.6],
        key=lambda x: x[1]
    )
    
    if not weak_concepts:
        return [types.TextContent(type="text", text="🎉 No weaknesses identified! Keep up the great work!")]
    
    return [types.TextContent(type="text", text=f"""
🔴 **Weaknesses Identified**

**Student:** {student_id}
**Syllabus:** {syllabus_id}

**Concepts Needing Improvement:**
{chr(10).join(f"  - {concept}: {score:.1%} mastery" for concept, score in weak_concepts[:5])}

💡 **Recommendation:** Focus on these concepts in your next session.
Use `/tutor focus {weak_concepts[0][0]}` to start a targeted session.
""")]

async def suggest_next_topic(args: dict):
    """Suggest the next topic to study"""
    student_id = args["student_id"]
    syllabus_id = args["syllabus_id"]
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    
    if not syllabus_file.exists():
        return "Syllabus not found"
    
    with open(syllabus_file, 'r', encoding='utf-8') as f:
        syllabus_data = json.load(f)
    
    concepts = syllabus_data.get('concepts', [])
    
    if not progress_file.exists():
        return f"Start with: {concepts[0]['name'] if concepts else 'Introduction'}"
    
    with open(progress_file, 'r', encoding='utf-8') as f:
        progress = json.load(f)
    
    # First, address weaknesses
    weaknesses = progress.get('weaknesses', [])
    if weaknesses:
        return f"Review: {weaknesses[0]} (weakness)"
    
    # Find the next unmastered concept
    mastery = progress.get('concept_mastery', {})
    for concept in concepts:
        concept_name = concept['name']
        if concept_name not in mastery or mastery[concept_name] < 0.7:
            return concept_name
    
    return "🎉 All concepts mastered! Consider taking the final exam."


async 
def build_concept_map(syllabus_id: str) -> dict:
    """Build a relationship map between concepts"""
    # Load syllabus
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    with open(syllabus_file, 'r') as f:
        syllabus = json.load(f)
    
    # Build graph
    relationships = {}
    concepts = syllabus.get('concepts', [])
    
    for i, concept in enumerate(concepts):
        name = concept['name']
        relationships[name] = {
            "prerequisites": concept.get('prerequisites', []),
            "depends_on": [],
            "exam_weight": concept.get('exam_frequency', 0),
            "difficulty": concept.get('difficulty', 1)
        }
        
        # Find dependencies
        for j, other in enumerate(concepts):
            if i != j and concept.get('prerequisites'):
                if any(p in other['name'] for p in concept['prerequisites']):
                    relationships[name]["depends_on"].append(other['name'])
    
    return relationships

if __name__ == "__main__":
    import asyncio
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="codewhale-syllabus-processor",
                    server_version="0.1.0"
                )
            )
    asyncio.run(main())