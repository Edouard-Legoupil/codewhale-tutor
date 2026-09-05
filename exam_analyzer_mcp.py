#!/usr/bin/env python3
"""
Advanced exam analysis with question classification and difficulty estimation
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import PyPDF2
from dataclasses import dataclass, asdict
import numpy as np

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

app = Server("codewhale-exam-analyzer")

EXAMS_DIR = Path.home() / ".codewhale" / "exams"
EXAMS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class Question:
    id: int
    text: str
    type: str  # multiple_choice, essay, short_answer, calculation, true_false
    difficulty: float  # 0.0 - 1.0
    concepts: List[str]
    keywords: List[str]
    length: int
    has_diagram: bool
    sub_questions: int
    bloom_level: str  # remember, understand, apply, analyze, evaluate, create

@dataclass
class ExamAnalysis:
    exam_id: str
    syllabus_id: str
    total_questions: int
    question_types: Dict[str, int]
    difficulty_distribution: Dict[str, float]
    average_difficulty: float
    concept_coverage: Dict[str, int]
    bloom_distribution: Dict[str, int]
    time_estimate: int  # minutes
    question_quality_score: float
    recommended_focus: List[str]

@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="analyze_exam",
            description="Perform comprehensive analysis of an exam",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to exam PDF"},
                    "exam_id": {"type": "string"},
                    "syllabus_id": {"type": "string"}
                },
                "required": ["file_path", "exam_id"]
            }
        ),
        types.Tool(
            name="classify_question",
            description="Classify a single question by type and difficulty",
            inputSchema={
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "concepts": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["question_text"]
            }
        ),
        types.Tool(
            name="generate_study_plan",
            description="Generate a study plan based on exam analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "exam_id": {"type": "string"},
                    "student_id": {"type": "string"},
                    "days_until_exam": {"type": "integer"}
                },
                "required": ["exam_id", "days_until_exam"]
            }
        ),
        types.Tool(
            name="compare_exams",
            description="Compare difficulty and coverage across multiple exams",
            inputSchema={
                "type": "object",
                "properties": {
                    "exam_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["exam_ids"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    
    if name == "analyze_exam":
        return await analyze_exam(arguments)
    elif name == "classify_question":
        return await classify_question(arguments)
    elif name == "generate_study_plan":
        return await generate_study_plan(arguments)
    elif name == "compare_exams":
        return await compare_exams(arguments)
    
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def analyze_exam(args: dict):
    """Comprehensive exam analysis"""
    file_path = Path(args["file_path"])
    exam_id = args["exam_id"]
    syllabus_id = args.get("syllabus_id", "unknown")
    
    if not file_path.exists():
        return [types.TextContent(type="text", text=f"❌ File not found: {file_path}")]
    
    # Extract text
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        return [types.TextContent(type="text", text=f"❌ Error reading PDF: {str(e)}")]
    
    # Parse questions
    questions = parse_questions(text)
    
    # Classify each question
    classified_questions = []
    for q in questions:
        classified = await classify_question({"question_text": q, "concepts": []})
        # Parse the response
        try:
            result = json.loads(classified[0].text)
            classified_questions.append(result)
        except:
            # Fallback classification
            classified_questions.append({
                "text": q[:100],
                "type": "unknown",
                "difficulty": 0.5,
                "concepts": ["general"],
                "bloom_level": "understand"
            })
    
    # Aggregate statistics
    question_types = {}
    difficulties = []
    concepts = {}
    bloom_levels = {}
    
    for q in classified_questions:
        q_type = q.get("type", "unknown")
        question_types[q_type] = question_types.get(q_type, 0) + 1
        
        difficulty = q.get("difficulty", 0.5)
        difficulties.append(difficulty)
        
        for concept in q.get("concepts", ["general"]):
            concepts[concept] = concepts.get(concept, 0) + 1
        
        bloom = q.get("bloom_level", "understand")
        bloom_levels[bloom] = bloom_levels.get(bloom, 0) + 1
    
    avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0
    
    # Difficulty distribution
    diff_dist = {"easy": 0, "medium": 0, "hard": 0}
    for d in difficulties:
        if d < 0.33:
            diff_dist["easy"] += 1
        elif d < 0.67:
            diff_dist["medium"] += 1
        else:
            diff_dist["hard"] += 1
    
    # Question quality score (combination of factors)
    quality_score = min(1.0, (
        0.3 * (len(classified_questions) / 20) +  # More questions = better
        0.3 * (len(bloom_levels) / 3) +           # Diverse bloom levels
        0.2 * (len(concepts) / 5) +               # Concept coverage
        0.2 * (1 - abs(avg_difficulty - 0.5))     # Balanced difficulty
    ))
    
    # Recommended focus
    recommended_focus = []
    for concept, count in sorted(concepts.items(), key=lambda x: x[1], reverse=True):
        if count / len(classified_questions) > 0.3:  # Concept appears >30% of questions
            recommended_focus.append(concept)
    
    analysis = ExamAnalysis(
        exam_id=exam_id,
        syllabus_id=syllabus_id,
        total_questions=len(classified_questions),
        question_types=question_types,
        difficulty_distribution=diff_dist,
        average_difficulty=avg_difficulty,
        concept_coverage=concepts,
        bloom_distribution=bloom_levels,
        time_estimate=len(classified_questions) * 2 + 5,  # Rough estimate
        question_quality_score=quality_score,
        recommended_focus=recommended_focus[:5]
    )
    
    # Save analysis
    analysis_file = EXAMS_DIR / f"{exam_id}_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(analysis), f, indent=2)
    
    # Generate detailed report
    report = generate_exam_report(analysis, classified_questions[:3])
    
    return [types.TextContent(type="text", text=report)]

def parse_questions(text: str) -> List[str]:
    """Parse questions from exam text"""
    questions = []
    
    # Pattern for numbered questions
    patterns = [
        r'(\d+)[\.\)]\s*([^\n]+(?:\n(?!\d+[\.\)])[^\n]+)*)',  # "1. Question text"
        r'Question\s+(\d+)[:\.]\s*([^\n]+(?:\n(?!Question)[^\n]+)*)',  # "Question 1: text"
        r'[Qq](\d+)[:\.]\s*([^\n]+(?:\n(?!Q\d+)[^\n]+)*)'  # "Q1: text"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        for match in matches:
            if len(match) == 2:
                q_text = match[1].strip()
            else:
                q_text = match[0].strip()
            
            if len(q_text) > 10:  # Filter out very short matches
                questions.append(q_text)
    
    # If no questions found, split by double newlines
    if not questions:
        sections = re.split(r'\n\s*\n', text)
        for section in sections:
            if len(section) > 50 and any(char.isdigit() for char in section[:50]):
                questions.append(section.strip())
    
    return questions

async def classify_question(args: dict) -> list[types.TextContent]:
    """Classify a single question by type, difficulty, and Bloom's level"""
    question_text = args["question_text"]
    provided_concepts = args.get("concepts", [])
    
    # Detect question type
    q_lower = question_text.lower()
    
    # Multiple choice
    if re.search(r'[a-d][\.\)]|choose|select|which of the following', q_lower):
        q_type = "multiple_choice"
    # True/False
    elif re.search(r'(true|false)|(correct|incorrect)|(agree|disagree)', q_lower):
        q_type = "true_false"
    # Calculation
    elif re.search(r'calculate|compute|solve|what is|find the|derive|integrate', q_lower):
        q_type = "calculation"
    # Essay
    elif re.search(r'essay|discuss|analyze|evaluate|compare and contrast|critique', q_lower):
        q_type = "essay"
    # Short answer
    elif len(question_text) < 200 and q_type not in ["calculation", "essay", "multiple_choice", "true_false"]:
        q_type = "short_answer"
    else:
        q_type = "other"
    
    # Estimate difficulty
    difficulty = estimate_difficulty(question_text)
    
    # Detect concepts
    concepts = provided_concepts or detect_concepts(question_text)
    
    # Bloom's level
    bloom_level = detect_bloom_level(question_text)
    
    return [types.TextContent(type="text", text=json.dumps({
        "text": question_text[:200],
        "type": q_type,
        "difficulty": difficulty,
        "concepts": concepts,
        "bloom_level": bloom_level,
        "length": len(question_text),
        "has_diagram": 'figure' in q_lower or 'diagram' in q_lower or 'image' in q_lower,
        "sub_questions": len(re.findall(r'[a-d][\.\)]', q_lower))
    }))]

def estimate_difficulty(text: str) -> float:
    """Estimate question difficulty based on text features"""
    difficulty = 0.5  # Default
    
    # Length factor (longer = more difficult)
    length = len(text)
    if length < 50:
        difficulty -= 0.1
    elif length > 200:
        difficulty += 0.1
    
    # Technical vocabulary
    technical_patterns = [
        r'\b(concept|theoretical|principle|derive|analyze|synthesize|evaluate|critique)\b',
        r'\b(equation|formula|algorithm|function|variable)\b',
        r'\b(however|therefore|consequently|furthermore)\b'
    ]
    tech_count = sum(len(re.findall(pattern, text.lower())) for pattern in technical_patterns)
    difficulty += min(0.2, tech_count * 0.05)
    
    # Conditional statements (suggest complexity)
    if 'if' in text.lower() or 'when' in text.lower() or 'unless' in text.lower():
        difficulty += 0.1
    
    # Word variety (proxy for complexity)
    words = text.split()
    if words:
        unique_words = len(set(words))
        variety = unique_words / len(words)
        if variety > 0.6:
            difficulty += 0.1
        elif variety < 0.3:
            difficulty -= 0.1
    
    # Constrain to [0,1]
    return max(0, min(1, difficulty))

def detect_concepts(text: str) -> List[str]:
    """Detect concepts from question text"""
    # This would ideally use an LLM or knowledge base
    # Simple keyword matching for common academic concepts
    concept_patterns = {
        "economics": ["supply", "demand", "elasticity", "market", "trade", "inflation", "gdp", "unemployment"],
        "psychology": ["cognitive", "behavior", "personality", "conscious", "memory", "learning", "perception"],
        "sociology": ["social", "norms", "values", "culture", "identity", "class", "gender", "race"],
        "mathematics": ["function", "derivative", "integral", "probability", "statistics", "equation", "matrix"],
        "history": ["revolution", "empire", "colonial", "industrial", "renaissance", "feudalism", "democracy"],
        "biology": ["cell", "dna", "evolution", "species", "organism", "ecosystem", "protein", "gene"],
        "computer_science": ["algorithm", "data", "structure", "programming", "database", "network", "security"]
    }
    
    detected = []
    text_lower = text.lower()
    for concept, keywords in concept_patterns.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(concept)
    
    return detected if detected else ["general"]

def detect_bloom_level(text: str) -> str:
    """Detect Bloom's Taxonomy level"""
    bloom_keywords = {
        "remember": ["define", "list", "recognize", "identify", "recall", "name", "state"],
        "understand": ["explain", "describe", "interpret", "paraphrase", "summarize", "classify"],
        "apply": ["apply", "use", "demonstrate", "calculate", "solve", "implement"],
        "analyze": ["analyze", "compare", "contrast", "distinguish", "examine", "differentiate"],
        "evaluate": ["evaluate", "critique", "justify", "validate", "support", "assess"],
        "create": ["create", "design", "develop", "propose", "formulate", "construct"]
    }
    
    text_lower = text.lower()
    for level, keywords in bloom_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return level
    
    return "understand"  # Default

def generate_exam_report(analysis: ExamAnalysis, sample_questions: List[Dict]) -> str:
    """Generate a human-readable exam report"""
    
    # Quality rating
    quality_score = analysis.question_quality_score
    if quality_score >= 0.8:
        quality_rating = "🌟 Excellent"
    elif quality_score >= 0.6:
        quality_rating = "👍 Good"
    elif quality_score >= 0.4:
        quality_rating = "📝 Adequate"
    else:
        quality_rating = "⚠️ Needs Improvement"
    
    # Difficulty rating
    avg_diff = analysis.average_difficulty
    if avg_diff < 0.33:
        difficulty_rating = "🟢 Easy"
    elif avg_diff < 0.67:
        difficulty_rating = "🟡 Moderate"
    else:
        difficulty_rating = "🔴 Challenging"
    
    report = f"""
📊 **Comprehensive Exam Analysis**

**Exam ID:** {analysis.exam_id}
**Syllabus:** {analysis.syllabus_id}
**Total Questions:** {analysis.total_questions}
**Estimated Time:** {analysis.time_estimate} minutes

---

## 📋 Question Types

"""
    
    for q_type, count in analysis.question_types.items():
        percentage = (count / analysis.total_questions) * 100
        report += f"  - {q_type.replace('_', ' ').title()}: {count} ({percentage:.0f}%)\n"
    
    report += f"""
## 📈 Difficulty Analysis

**Overall Difficulty:** {difficulty_rating} ({avg_diff:.1%})
**Quality Score:** {quality_rating} ({quality_score:.0%})

**Distribution:**
  - Easy: {analysis.difficulty_distribution.get('easy', 0)}
  - Medium: {analysis.difficulty_distribution.get('medium', 0)}  
  - Hard: {analysis.difficulty_distribution.get('hard', 0)}

## 🎯 Concept Coverage

"""
    
    for concept, count in sorted(analysis.concept_coverage.items(), key=lambda x: x[1], reverse=True)[:5]:
        percentage = (count / analysis.total_questions) * 100
        report += f"  - {concept.title()}: {count} question(s) ({percentage:.0f}%)\n"
    
    report += f"""
## 🧠 Bloom's Taxonomy Distribution

"""
    
    for level, count in analysis.bloom_distribution.items():
        percentage = (count / analysis.total_questions) * 100
        report += f"  - {level.title()}: {count} ({percentage:.0f}%)\n"
    
    if analysis.recommended_focus:
        report += f"""
## 💡 Recommended Focus Areas

Based on concept frequency, focus on:
"""
        for concept in analysis.recommended_focus:
            report += f"  - {concept.title()}\n"
    
    if sample_questions:
        report += f"""
## 📝 Sample Questions

1. {sample_questions[0].get('text', '')[:150]}...
   - Type: {sample_questions[0].get('type', 'unknown')}
   - Difficulty: {sample_questions[0].get('difficulty', 0.5):.0%}
   - Bloom's: {sample_questions[0].get('bloom_level', 'understand')}

"""
        if len(sample_questions) > 1:
            report += f"""2. {sample_questions[1].get('text', '')[:150]}...
   - Type: {sample_questions[1].get('type', 'unknown')}
   - Difficulty: {sample_questions[1].get('difficulty', 0.5):.0%}
   - Bloom's: {sample_questions[1].get('bloom_level', 'understand')}

"""

    report += f"""
## 📝 Study Suggestions

1. **Time Management**: Allocate {analysis.time_estimate} minutes for this exam
2. **Priority Topics**: Focus on concepts appearing in 30%+ of questions
3. **Practice Strategy**: Start with {analysis.question_types.get('multiple_choice', 0)} multiple choice questions for review
4. **Essay Preparation**: Practice {analysis.question_types.get('essay', 0)} essay questions
5. **Weakness Identification**: Focus on {analysis.bloom_distribution.get('analyze', 0)} analysis-level questions

---
*This analysis is based on question patterns and should be used alongside instructor guidance.*
"""
    
    return report

async def generate_study_plan(args: dict) -> list[types.TextContent]:
    """Generate a study plan based on exam analysis"""
    exam_id = args["exam_id"]
    student_id = args.get("student_id", "unknown")
    days_until_exam = args.get("days_until_exam", 7)
    
    # Load exam analysis
    analysis_file = EXAMS_DIR / f"{exam_id}_analysis.json"
    if not analysis_file.exists():
        return [types.TextContent(type="text", text=f"❌ Exam {exam_id} not analyzed yet. Run analyze_exam first.")]
    
    with open(analysis_file, 'r') as f:
        analysis = json.load(f)
    
    # Load student progress
    progress_file = Path.home() / ".codewhale" / "tutor_progress" / f"{student_id}_*.json"
    weaknesses = []
    progress_files = list(Path.home().glob(f".codewhale/tutor_progress/{student_id}_*.json"))
    if progress_files:
        with open(progress_files[0], 'r') as f:
            progress = json.load(f)
            weaknesses = progress.get("weaknesses", [])
    
    # Generate plan
    plan = f"""
📚 **Study Plan for {exam_id}**

**Student:** {student_id}
**Days Until Exam:** {days_until_exam}
**Exam Difficulty:** {analysis.get('average_difficulty', 0.5):.1%}

---

## 📅 Recommended Schedule

### Week {max(1, days_until_exam // 7 + 1)} - {days_until_exam} Days Remaining

"""
    
    # Day-by-day breakdown
    for day in range(days_until_exam, 0, -1):
        if day == days_until_exam:
            plan += f"**Day {days_until_exam - day + 1}** (Today): Review syllabus overview\n"
        elif day > days_until_exam // 2:
            plan += f"**Day {days_until_exam - day + 1}**: Focus on concepts: {', '.join(list(analysis.get('concept_coverage', {}).keys())[:3])}\n"
        else:
            plan += f"**Day {days_until_exam - day + 1}**: Practice with {analysis.get('question_types', {}).get('multiple_choice', 2)} MC questions and 1 essay\n"
    
    # Concept focus
    plan += f"""
## 🎯 Priority Concepts

Based on exam analysis, focus on:
"""
    concepts = list(analysis.get('concept_coverage', {}).keys())[:5]
    for concept in concepts:
        plan += f"  - {concept.title()}: Appears in {analysis['concept_coverage'].get(concept, 0)} questions\n"
    
    # Weakness focus
    if weaknesses:
        plan += f"""
## ⚠️ Your Weaknesses

Based on your progress, extra focus needed on:
"""
        for weakness in weaknesses[:3]:
            plan += f"  - {weakness}\n"
    
    # Question type practice
    plan += f"""
## 📝 Practice Focus

- **Multiple Choice**: {analysis.get('question_types', {}).get('multiple_choice', 2)} questions per day
- **Essays**: Practice {analysis.get('question_types', {}).get('essay', 1)} essays per week
- **Calculations**: {analysis.get('question_types', {}).get('calculation', 0)} problems for practice

## 💡 Success Strategies

1. Review the cheatsheet daily: `/cheatsheet {analysis.get('syllabus_id', '')}`
2. Practice active recall: Cover answers and explain concepts
3. Time management: Practice with a timer
4. Identify patterns: Look for recurring question types
5. Self-test: Create your own questions

## 🚀 Next Steps

1. Start with your weakest concept: {weaknesses[0] if weaknesses else 'General review'}
2. Use `/tutor focus {weaknesses[0] if weaknesses else 'general'}` for targeted help
3. Take a practice exam with the `/tutor exam` command
4. Review and adjust this plan as needed

---
*Plan generated based on exam analysis and your progress.*
"""
    
    return [types.TextContent(type="text", text=plan)]

async def compare_exams(args: dict) -> list[types.TextContent]:
    """Compare multiple exams"""
    exam_ids = args.get("exam_ids", [])
    
    analyses = []
    for exam_id in exam_ids:
        analysis_file = EXAMS_DIR / f"{exam_id}_analysis.json"
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                analyses.append(json.load(f))
    
    if not analyses:
        return [types.TextContent(type="text", text="❌ No valid exam analyses found.")]
    
    comparison = f"""
📊 **Exam Comparison Report**

{len(analyses)} exams compared.

---

## 📈 Key Metrics

| Metric | {analyses[0]['exam_id']} | {analyses[1]['exam_id'] if len(analyses) > 1 else 'N/A'} | {' | '.join(a['exam_id'] for a in analyses[2:])} |
|--------|{'|' + '-'*18 + '|' + '-'*18 + '|' + '|'.join('-'*18 for _ in analyses[2:])}|
| Total Questions | {analyses[0]['total_questions']} | {analyses[1]['total_questions'] if len(analyses) > 1 else 'N/A'} | {''.join(str(a['total_questions']) + ' |' for a in analyses[2:])} |
| Avg Difficulty | {analyses[0]['average_difficulty']:.1%} | {analyses[1]['average_difficulty']:.1% if len(analyses) > 1 else 'N/A'} | {''.join(str(a['average_difficulty']:.1%) + ' |' for a in analyses[2:])} |
| Quality Score | {analyses[0]['question_quality_score']:.1%} | {analyses[1]['question_quality_score']:.1% if len(analyses) > 1 else 'N/A'} | {''.join(str(a['question_quality_score']:.1%) + ' |' for a in analyses[2:])} |
| Estimated Time | {analyses[0]['time_estimate']} min | {analyses[1]['time_estimate'] if len(analyses) > 1 else 'N/A'} | {''.join(str(a['time_estimate']) + ' |' for a in analyses[2:])} |

## 🎯 Concept Coverage Comparison

"""
    
    # Compare concept coverage
    all_concepts = set()
    for analysis in analyses:
        all_concepts.update(analysis.get('concept_coverage', {}).keys())
    
    for concept in sorted(all_concepts):
        coverage = []
        for analysis in analyses:
            count = analysis.get('concept_coverage', {}).get(concept, 0)
            total = analysis.get('total_questions', 1)
            coverage.append(f"{count}/{total}")
        comparison += f"  - **{concept}**: {' | '.join(coverage)}\n"
    
    comparison += """
## 📊 Trends

"""
    # Difficulty trend
    difficulties = [a['average_difficulty'] for a in analyses]
    if len(difficulties) > 1:
        trend = "increasing" if difficulties[-1] > difficulties[0] else "decreasing" if difficulties[-1] < difficulties[0] else "stable"
        comparison += f"**Difficulty Trend**: {trend} ({difficulties[0]:.1%} → {difficulties[-1]:.1%})\n"
    
    # Quality trend
    qualities = [a['question_quality_score'] for a in analyses]
    if len(qualities) > 1:
        trend = "improving" if qualities[-1] > qualities[0] else "declining" if qualities[-1] < qualities[0] else "stable"
        comparison += f"**Quality Trend**: {trend} ({qualities[0]:.1%} → {qualities[-1]:.1%})\n"
    
    comparison += """
## 💡 Insights

"""
    # Find most common concepts across exams
    concept_counts = {}
    for analysis in analyses:
        for concept, count in analysis.get('concept_coverage', {}).items():
            concept_counts[concept] = concept_counts.get(concept, 0) + count
    
    top_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    comparison += f"**Most Tested Concepts Across All Exams**: {', '.join(c[0] for c in top_concepts)}\n"
    
    # Identify exam with best balance
    best_balanced = min(analyses, key=lambda a: abs(a['average_difficulty'] - 0.5))
    comparison += f"**Best Balanced Exam**: {best_balanced['exam_id']} (difficulty {best_balanced['average_difficulty']:.1%})\n"
    
    return [types.TextContent(type="text", text=comparison)]

if __name__ == "__main__":
    import asyncio
    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="codewhale-exam-analyzer",
                    server_version="0.1.0"
                )
            )
    asyncio.run(main())