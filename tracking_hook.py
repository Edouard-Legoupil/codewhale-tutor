#!/usr/bin/env python3
"""
Track student learning progress and update weaknesses
"""

import json
import sys
import re
import unicodedata
from pathlib import Path
from datetime import datetime

PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

def _normalize(text: str) -> str:
    """Lowercase and strip accents for accent-insensitive matching."""
    text = text.lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def analyze_student_response(question: str, response: str) -> dict:
    """Analyze student response for metacognitive markers (French + English)."""
    r = _normalize(response)
    analysis = {
        "confidence": 50,
        "strategy_mentioned": False,
        "shows_understanding": False,
        "contains_correction": False,
        "effort_level": 0,
    }

    high = r"\b(confident|sure|certain|know|understand|confiant|evidemment)\b|je sais|je connais|je comprends|je suis sur|j'en suis sur|bien sur"
    low = r"\b(unsure|incertain|maybe|perhaps)\b|not sure|pas sur|peut-etre|peut etre|je pense|je crois|je ne sais pas|je suppose|pas certain|je ne suis pas sur"
    very_high = r"\b(definitely|certainly|absolutely|definitivement|certainement|absolument)\b|tout a fait"

    if re.search(high, r):
        analysis["confidence"] = 70
    if re.search(low, r):
        analysis["confidence"] = 40
    if re.search(very_high, r):
        analysis["confidence"] = 85

    strategy = r"\b(strategy|approach|method|strategie|approche|methode|facon|etape)\b|essayer|j'ai essaye|je procede|ma methode"
    if re.search(strategy, r):
        analysis["strategy_mentioned"] = True

    if len(response.split()) > 20:  # Longer response shows effort
        analysis["shows_understanding"] = True

    correction = r"\b(actually|correction|wait|no)\b|en fait|plutot|je me suis trompe|attends|a vrai dire"
    if re.search(correction, r):
        analysis["contains_correction"] = True

    return analysis

def main():
    data = json.loads(sys.stdin.read())
    
    student_id = data.get('student_id', 'unknown')
    syllabus_id = data.get('syllabus_id', 'unknown')
    question = data.get('question', '')
    response = data.get('response', '')
    concept = data.get('concept', 'general')
    
    # Analyze response
    analysis = analyze_student_response(question, response)
    
    # Load progress (canonical schema, preserving any existing keys)
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        progress = {}

    progress.setdefault("student_id", student_id)
    progress.setdefault("syllabus_id", syllabus_id)
    progress.setdefault("response_history", [])
    progress.setdefault("weaknesses", [])
    progress.setdefault("concept_mastery", {})
    progress.setdefault("current_stage", 0)
    progress.setdefault("last_session", None)

    # Record interaction
    progress["response_history"].append({
        "timestamp": datetime.now().isoformat(),
        "concept": concept,
        "question": question,
        "response": response,
        "confidence": analysis["confidence"],
        "analysis": analysis
    })
    progress["last_session"] = datetime.now().isoformat()

    # Update weaknesses
    if analysis["confidence"] < 40 and concept not in progress.get("weaknesses", []):
        progress["weaknesses"].append(concept)
    
    # Save progress
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)
    
    # Provide feedback (optional)
    feedback = ""
    if analysis["strategy_mentioned"]:
        feedback = "Great job explaining your strategy!"
    elif analysis["confidence"] > 70:
        feedback = "I can see you're confident in this. Let's challenge you further!"
    elif analysis["confidence"] < 40:
        feedback = "Let's slow down and review this concept together."
    
    if feedback:
        print(json.dumps({
            "decision": "allow",
            "system_message": f"🧠 {feedback}"
        }))
    else:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()