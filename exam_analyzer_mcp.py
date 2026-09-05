#!/usr/bin/env python3
"""
Advanced exam analysis with question classification and difficulty estimation.

Uses the modern FastMCP API (mcp.server.fastmcp.FastMCP).
"""

import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict

import PyPDF2
import numpy as np
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("codewhale-exam-analyzer")

EXAMS_DIR = Path.home() / ".codewhale" / "exams"
PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"
EXAMS_DIR.mkdir(parents=True, exist_ok=True)


# --- Data structures ---------------------------------------------------------
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


# --- Helpers -----------------------------------------------------------------
def _read_pdf_text(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "".join(page.extract_text() or "" for page in reader.pages)


def _strip_accents(text: str) -> str:
    """Lowercase and remove diacritics for accent-insensitive matching."""
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _parse_questions(text: str) -> List[str]:
    questions = []
    patterns = [
        r"(\d+)[\.\)]\s*([^\n]+(?:\n(?!\d+[\.\)])[^\n]+)*)",
        r"Question\s+(\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Question\s+\d+)[^\n]+)*)",
        r"[Qq](\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Q\d+)[^\n]+)*)",
        r"Exercice\s+(\d+)\s*[:\.\)]?\s*([^\n]+(?:\n(?!Exercice\s+\d+)[^\n]+)*)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, re.MULTILINE):
            q_text = match[1].strip() if len(match) == 2 else match[0].strip()
            if len(q_text) > 10:
                questions.append(q_text)

    if not questions:
        for section in re.split(r"\n\s*\n", text):
            if len(section) > 50 and any(c.isdigit() for c in section[:50]):
                questions.append(section.strip())

    return questions


def _estimate_difficulty(text: str) -> float:
    difficulty = 0.5
    length = len(text)
    if length < 50:
        difficulty -= 0.1
    elif length > 200:
        difficulty += 0.1

    technical_patterns = [
        r"\b(concept|theoretical|principle|derive|analyze|synthesize|evaluate|critique)\b",
        r"\b(equation|formula|algorithm|function|variable)\b",
        r"\b(however|therefore|consequently|furthermore)\b",
    ]
    tech_count = sum(len(re.findall(p, text.lower())) for p in technical_patterns)
    difficulty += min(0.2, tech_count * 0.05)

    if "if" in text.lower() or "when" in text.lower() or "unless" in text.lower():
        difficulty += 0.1

    words = text.split()
    if words:
        variety = len(set(words)) / len(words)
        if variety > 0.6:
            difficulty += 0.1
        elif variety < 0.3:
            difficulty -= 0.1

    return max(0, min(1, difficulty))


def _detect_concepts(text: str) -> List[str]:
    norm = _strip_accents(text)
    concept_patterns = {
        "linear_algebra": ["valeur propre", "vecteur propre", "diagonalis", "matrice", "determinant", "gram-schmidt", "moindres carres", "produit scalaire", "espace euclidien", "matrice symetrique", "eigenvalue", "eigenvector", "matrix", "determinant"],
        "calculus_analysis": ["derivee", "integrale", "serie", "suite", "taylor", "extremum", "fonction a deux variables", "derivative", "integral", "series", "sequence"],
        "probability": ["variable aleatoire", "esperance", "variance", "loi", "bayes", "bernoulli", "poisson", "probabilite", "covariance", "independance", "probability", "expectation", "distribution", "bayes"],
        "statistics": ["estimateur", "estimation", "echantillon", "risque quadratique", "inference", "regression", "statistique", "estimator", "hypothesis", "p-value", "regression"],
        "python_programming": ["python", "dictionnaire", "fonction", "objet", "classe", "attribut", "methode", "api", "algorithme", "programmation", "fichier", "dictionary", "class", "object", "algorithm"],
        "economics": ["offre", "demande", "producteur", "consommateur", "inegalite", "croissance", "inflation", "marche", "elasticite", "supply", "demand", "inflation", "market", "gdp", "unemployment"],
        "psychology": ["cognitif", "comportement", "memoire", "apprentissage", "personnalite", "cognitive", "behavior", "memory", "learning"],
        "sociology": ["social", "normes", "valeurs", "culture", "identite", "classe", "genre", "inegalite", "social", "norms", "culture"],
        "history": ["revolution", "empire", "colonial", "industriel", "renaissance", "revolution", "empire", "industrial"],
        "biology": ["cellule", "adn", "evolution", "espece", "organisme", "proteine", "cell", "dna", "evolution"],
        "computer_science": ["algorithme", "donnees", "structure", "programmation", "base de donnees", "reseau", "securite", "algorithm", "data", "programming", "database", "network"],
    }
    detected = [concept for concept, kws in concept_patterns.items() if any(kw in norm for kw in kws)]
    return detected or ["general"]


def _detect_bloom_level(text: str) -> str:
    norm = _strip_accents(text)
    bloom_keywords = {
        "remember": ["define", "definir", "list", "lister", "recognize", "identifier", "recall", "rappeler", "name", "nommer", "state", "enoncer", "citer"],
        "understand": ["explain", "expliquer", "describe", "decrire", "interpret", "interpreter", "paraphrase", "reformuler", "summarize", "resumer", "classify", "classer"],
        "apply": ["apply", "appliquer", "use", "utiliser", "calculate", "calculer", "solve", "resoudre", "implement", "implementer"],
        "analyze": ["analyze", "analyser", "compare", "comparer", "contrast", "distinguish", "distinguer", "examine", "examiner", "differentiate", "differentier", "deduire", "montrer", "demontrer", "prouver", "discuter"],
        "evaluate": ["evaluate", "evaluer", "critique", "critiquer", "justify", "justifier", "validate", "valider", "assess", "apprecier"],
        "create": ["create", "creer", "design", "concevoir", "develop", "developper", "propose", "proposer", "formulate", "formuler", "construct", "construire", "rediger"],
    }
    for level, kws in bloom_keywords.items():
        if any(kw in norm for kw in kws):
            return level
    return "understand"


def _classify_question(question_text: str, provided_concepts: List[str]) -> dict:
    q_lower = _strip_accents(question_text)

    if re.search(r"[a-d][\.\)]|choose|select|which of the following|choisir|laquelle|lesquelles|cocher", q_lower):
        q_type = "multiple_choice"
    elif re.search(r"(true|false)|(correct|incorrect)|(agree|disagree)|(vrai|faux)", q_lower):
        q_type = "true_false"
    elif re.search(r"calculate|compute|solve|what is|find the|derive|integrate|calculer|resoudre|quelle est|determiner", q_lower):
        q_type = "calculation"
    elif re.search(r"essay|discuss|analyze|evaluate|compare and contrast|critique|discuter|analyser|evaluer|justifier|rediger|commenter", q_lower):
        q_type = "essay"
    elif len(question_text) < 200:
        q_type = "short_answer"
    else:
        q_type = "other"

    return {
        "text": question_text[:200],
        "type": q_type,
        "difficulty": _estimate_difficulty(question_text),
        "concepts": provided_concepts or _detect_concepts(question_text),
        "bloom_level": _detect_bloom_level(question_text),
        "length": len(question_text),
        "has_diagram": any(w in q_lower for w in ("figure", "diagram", "image", "diagramme", "schema", "graphe")),
        "sub_questions": len(re.findall(r"[a-d][\.\)]", q_lower)),
    }


def _generate_exam_report(analysis: ExamAnalysis, sample_questions: List[Dict]) -> str:
    quality_score = analysis.question_quality_score
    if quality_score >= 0.8:
        quality_rating = "🌟 Excellent"
    elif quality_score >= 0.6:
        quality_rating = "👍 Good"
    elif quality_score >= 0.4:
        quality_rating = "📝 Adequate"
    else:
        quality_rating = "⚠️ Needs Improvement"

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
        pct = (count / analysis.total_questions) * 100 if analysis.total_questions else 0
        report += f"  - {q_type.replace('_', ' ').title()}: {count} ({pct:.0f}%)\n"

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
        pct = (count / analysis.total_questions) * 100 if analysis.total_questions else 0
        report += f"  - {concept.title()}: {count} question(s) ({pct:.0f}%)\n"

    report += "\n## 🧠 Bloom's Taxonomy Distribution\n\n"
    for level, count in analysis.bloom_distribution.items():
        pct = (count / analysis.total_questions) * 100 if analysis.total_questions else 0
        report += f"  - {level.title()}: {count} ({pct:.0f}%)\n"

    if analysis.recommended_focus:
        report += "\n## 💡 Recommended Focus Areas\n\nBased on concept frequency, focus on:\n"
        for concept in analysis.recommended_focus:
            report += f"  - {concept.title()}\n"

    if sample_questions:
        report += "\n## 📝 Sample Questions\n\n"
        report += f"1. {sample_questions[0].get('text', '')[:150]}...\n"
        report += f"   - Type: {sample_questions[0].get('type', 'unknown')}\n"
        report += f"   - Difficulty: {sample_questions[0].get('difficulty', 0.5):.0%}\n"
        report += f"   - Bloom's: {sample_questions[0].get('bloom_level', 'understand')}\n\n"
        if len(sample_questions) > 1:
            report += f"2. {sample_questions[1].get('text', '')[:150]}...\n"
            report += f"   - Type: {sample_questions[1].get('type', 'unknown')}\n"
            report += f"   - Difficulty: {sample_questions[1].get('difficulty', 0.5):.0%}\n"
            report += f"   - Bloom's: {sample_questions[1].get('bloom_level', 'understand')}\n\n"

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


# --- Tools -------------------------------------------------------------------
@mcp.tool()
def analyze_exam(file_path: str, exam_id: str, syllabus_id: str = "unknown") -> str:
    """Perform comprehensive analysis of an exam PDF.

    Args:
        file_path: Path to the exam PDF.
        exam_id: Unique ID for this exam.
        syllabus_id: Associated syllabus ID (optional).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return f"❌ File not found: {file_path}"

    try:
        text = _read_pdf_text(file_path)
    except Exception as e:  # noqa: BLE001
        return f"❌ Error reading PDF: {e}"

    questions = _parse_questions(text)
    classified = []
    for q in questions:
        try:
            classified.append(_classify_question(q, []))
        except Exception:  # noqa: BLE001
            classified.append({
                "text": q[:100],
                "type": "unknown",
                "difficulty": 0.5,
                "concepts": ["general"],
                "bloom_level": "understand",
            })

    question_types: Dict[str, int] = {}
    difficulties: List[float] = []
    concepts: Dict[str, int] = {}
    bloom_levels: Dict[str, int] = {}

    for q in classified:
        q_type = q.get("type", "unknown")
        question_types[q_type] = question_types.get(q_type, 0) + 1
        difficulties.append(q.get("difficulty", 0.5))
        for concept in q.get("concepts", ["general"]):
            concepts[concept] = concepts.get(concept, 0) + 1
        bloom = q.get("bloom_level", "understand")
        bloom_levels[bloom] = bloom_levels.get(bloom, 0) + 1

    avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0

    diff_dist = {"easy": 0, "medium": 0, "hard": 0}
    for d in difficulties:
        if d < 0.33:
            diff_dist["easy"] += 1
        elif d < 0.67:
            diff_dist["medium"] += 1
        else:
            diff_dist["hard"] += 1

    quality_score = min(1.0, (
        0.3 * (len(classified) / 20)
        + 0.3 * (len(bloom_levels) / 3)
        + 0.2 * (len(concepts) / 5)
        + 0.2 * (1 - abs(avg_difficulty - 0.5))
    ))

    recommended_focus = [
        concept for concept, count in sorted(concepts.items(), key=lambda x: x[1], reverse=True)
        if len(classified) and count / len(classified) > 0.3
    ]

    analysis = ExamAnalysis(
        exam_id=exam_id,
        syllabus_id=syllabus_id,
        total_questions=len(classified),
        question_types=question_types,
        difficulty_distribution=diff_dist,
        average_difficulty=avg_difficulty,
        concept_coverage=concepts,
        bloom_distribution=bloom_levels,
        time_estimate=len(classified) * 2 + 5,
        question_quality_score=quality_score,
        recommended_focus=recommended_focus[:5],
    )

    with open(EXAMS_DIR / f"{exam_id}_analysis.json", "w", encoding="utf-8") as f:
        json.dump(asdict(analysis), f, indent=2)

    return _generate_exam_report(analysis, classified[:3])


@mcp.tool()
def classify_question(question_text: str, concepts: list = None) -> str:
    """Classify a single question by type, difficulty, and Bloom's level.

    Args:
        question_text: The question text.
        concepts: Optional list of concepts.
    """
    result = _classify_question(question_text, concepts or [])
    return json.dumps(result)


@mcp.tool()
def generate_study_plan(exam_id: str, student_id: str = "unknown", days_until_exam: int = 7) -> str:
    """Generate a study plan based on a completed exam analysis.

    Args:
        exam_id: Exam ID to plan for.
        student_id: Student identifier (optional).
        days_until_exam: Days until the exam.
    """
    analysis_file = EXAMS_DIR / f"{exam_id}_analysis.json"
    if not analysis_file.exists():
        return f"❌ Exam {exam_id} not analyzed yet. Run analyze_exam first."

    with open(analysis_file, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    weaknesses = []
    progress_files = list(PROGRESS_DIR.glob(f"{student_id}_*.json")) if student_id != "unknown" else []
    if progress_files:
        with open(progress_files[0], "r", encoding="utf-8") as f:
            progress = json.load(f)
            weaknesses = progress.get("weaknesses", [])

    plan = f"""
📚 **Study Plan for {exam_id}**

**Student:** {student_id}
**Days Until Exam:** {days_until_exam}
**Exam Difficulty:** {analysis.get('average_difficulty', 0.5):.1%}

---

## 📅 Recommended Schedule

"""
    for day in range(days_until_exam, 0, -1):
        if day == days_until_exam:
            plan += f"**Day {days_until_exam - day + 1}** (Today): Review syllabus overview\n"
        elif day > days_until_exam // 2:
            plan += f"**Day {days_until_exam - day + 1}**: Focus on concepts: {', '.join(list(analysis.get('concept_coverage', {}).keys())[:3])}\n"
        else:
            plan += f"**Day {days_until_exam - day + 1}**: Practice with {analysis.get('question_types', {}).get('multiple_choice', 2)} MC questions and 1 essay\n"

    coverage = analysis.get("concept_coverage", {})
    total_q = analysis.get("total_questions", 1) or 1
    ranked = sorted(coverage.items(), key=lambda x: x[1], reverse=True)
    plan += "\n## 🎯 Predicted exam weighting\n\nAllocate study time proportionally to exam weight:\n"
    for concept, count in ranked[:8]:
        plan += f"  - {concept.title()}: {count / total_q:.0%} of the exam ({count}/{total_q} questions)\n"
    plan += "\nPrioritise the highest-weight concepts; revisit the low-weight ones just before the exam.\n"

    if weaknesses:
        plan += "\n## ⚠️ Your Weaknesses\n\nBased on your progress, extra focus needed on:\n"
        for weakness in weaknesses[:3]:
            plan += f"  - {weakness}\n"

    plan += f"""
## 📝 Practice Focus

- **Multiple Choice**: {analysis.get('question_types', {}).get('multiple_choice', 2)} questions per day
- **Essays**: Practice {analysis.get('question_types', {}).get('essay', 1)} essays per week
- **Calculations**: {analysis.get('question_types', {}).get('calculation', 0)} problems for practice

## 💡 Success Strategies

1. Review the cheatsheet daily
2. Practice active recall: cover answers and explain concepts
3. Time management: practice with a timer
4. Identify patterns: look for recurring question types
5. Self-test: create your own questions

## 🚀 Next Steps

1. Start with your weakest concept: {weaknesses[0] if weaknesses else 'General review'}
2. Take a practice exam
3. Review and adjust this plan as needed

---
*Plan generated based on exam analysis and your progress.*
"""
    return plan


@mcp.tool()
def compare_exams(exam_ids: list) -> str:
    """Compare difficulty and coverage across multiple exams.

    Args:
        exam_ids: List of exam IDs to compare.
    """
    analyses = []
    for exam_id in exam_ids:
        analysis_file = EXAMS_DIR / f"{exam_id}_analysis.json"
        if analysis_file.exists():
            with open(analysis_file, "r", encoding="utf-8") as f:
                analyses.append(json.load(f))

    if not analyses:
        return "❌ No valid exam analyses found."

    comparison = f"""
📊 **Exam Comparison Report**

{len(analyses)} exams compared.

---

## 📈 Key Metrics

| Metric | {analyses[0]['exam_id']} | {analyses[1]['exam_id'] if len(analyses) > 1 else 'N/A'} | {' | '.join(a['exam_id'] for a in analyses[2:])} |
|--------|{'|' + '-'*18 + '|' + '-'*18 + '|' + '|'.join('-'*18 for _ in analyses[2:])}|
| Total Questions | {analyses[0]['total_questions']} | {analyses[1]['total_questions'] if len(analyses) > 1 else 'N/A'} | {''.join(str(a['total_questions']) + ' |' for a in analyses[2:])} |
| Avg Difficulty | {analyses[0]['average_difficulty']:.1%} | {format(analyses[1]['average_difficulty'], '.1%') if len(analyses) > 1 else 'N/A'} | {''.join(format(a['average_difficulty'], '.1%') + ' |' for a in analyses[2:])} |
| Quality Score | {analyses[0]['question_quality_score']:.1%} | {format(analyses[1]['question_quality_score'], '.1%') if len(analyses) > 1 else 'N/A'} | {''.join(format(a['question_quality_score'], '.1%') + ' |' for a in analyses[2:])} |
| Estimated Time | {analyses[0]['time_estimate']} min | {analyses[1]['time_estimate'] if len(analyses) > 1 else 'N/A'} | {''.join(str(a['time_estimate']) + ' |' for a in analyses[2:])} |

## 🎯 Concept Coverage Comparison

"""

    all_concepts = set()
    for analysis in analyses:
        all_concepts.update(analysis.get("concept_coverage", {}).keys())

    for concept in sorted(all_concepts):
        coverage = []
        for analysis in analyses:
            count = analysis.get("concept_coverage", {}).get(concept, 0)
            total = analysis.get("total_questions", 1)
            coverage.append(f"{count}/{total}")
        comparison += f"  - **{concept}**: {' | '.join(coverage)}\n"

    comparison += "\n## 📊 Trends\n\n"

    difficulties = [a["average_difficulty"] for a in analyses]
    if len(difficulties) > 1:
        trend = "increasing" if difficulties[-1] > difficulties[0] else "decreasing" if difficulties[-1] < difficulties[0] else "stable"
        comparison += f"**Difficulty Trend**: {trend} ({difficulties[0]:.1%} → {difficulties[-1]:.1%})\n"

    qualities = [a["question_quality_score"] for a in analyses]
    if len(qualities) > 1:
        trend = "improving" if qualities[-1] > qualities[0] else "declining" if qualities[-1] < qualities[0] else "stable"
        comparison += f"**Quality Trend**: {trend} ({qualities[0]:.1%} → {qualities[-1]:.1%})\n"

    comparison += "\n## 💡 Insights\n\n"

    concept_counts: Dict[str, int] = {}
    for analysis in analyses:
        for concept, count in analysis.get("concept_coverage", {}).items():
            concept_counts[concept] = concept_counts.get(concept, 0) + count

    top_concepts = sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    comparison += f"**Most Tested Concepts Across All Exams**: {', '.join(c[0] for c in top_concepts)}\n"

    best_balanced = min(analyses, key=lambda a: abs(a["average_difficulty"] - 0.5))
    comparison += f"**Best Balanced Exam**: {best_balanced['exam_id']} (difficulty {best_balanced['average_difficulty']:.1%})\n"

    return comparison


if __name__ == "__main__":
    mcp.run()
