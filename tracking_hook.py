#!/usr/bin/env python3
"""
Track student learning progress and update weaknesses
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

def analyze_student_response(question: str, response: str) -> dict:
    """Analyze student response for metacognitive markers"""
    analysis = {
        "confidence": 50,  # Default
        "strategy_mentioned": False,
        "shows_understanding": False,
        "contains_correction": False,
        "effort_level": 0
    }
    
    # Confidence indicators
    if re.search(r'\b(confident|sure|know|understand)\b', response, re.I):
        analysis["confidence"] = 70
    if re.search(r'\b(unsure|not sure|maybe|perhaps)\b', response, re.I):
        analysis["confidence"] = 40
    if re.search(r'\b(definitely|certainly|absolutely)\b', response, re.I):
        analysis["confidence"] = 85
    
    # Strategy indicators
    if re.search(r'\b(strategy|approach|method|way|try)\b', response, re.I):
        analysis["strategy_mentioned"] = True
    
    # Understanding indicators
    if len(response.split()) > 20:  # Longer response shows effort
        analysis["shows_understanding"] = True
    
    # Self-correction
    if re.search(r'\b(actually|correction|wait|no)\b', response, re.I):
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
    
    # Load progress
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        progress = {"history": [], "weaknesses": []}
    
    # Record interaction
    progress["history"].append({
        "timestamp": datetime.now().isoformat(),
        "concept": concept,
        "question": question,
        "response": response,
        "confidence": analysis["confidence"],
        "analysis": analysis
    })
    
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