#!/usr/bin/env python3
"""
Assess student weaknesses and trigger targeted review
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"

def assess_weaknesses(student_id: str, syllabus_id: str) -> dict:
    """Identify consistent weaknesses from history"""
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    
    if not progress_file.exists():
        return {"weaknesses": [], "patterns": []}
    
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    # Analyze history for patterns
    history = progress.get("response_history", [])
    concept_performance = defaultdict(list)
    
    for entry in history:
        concept = entry.get("concept", "general")
        confidence = entry.get("confidence", 50)
        concept_performance[concept].append(confidence)
    
    # Identify weak concepts (average < 50)
    weaknesses = []
    for concept, scores in concept_performance.items():
        avg = sum(scores) / len(scores)
        if avg < 50:
            weaknesses.append({
                "concept": concept,
                "average_confidence": avg,
                "attempts": len(scores)
            })
    
    # Identify patterns
    patterns = []
    if len(history) > 5:
        # Check for confidence dropping on specific topics
        confidence_trend = [h.get("confidence", 50) for h in history[-10:]]
        if confidence_trend and confidence_trend[-1] < confidence_trend[0]:
            patterns.append("confidence_trend: decreasing")
    
    return {
        "weaknesses": sorted(weaknesses, key=lambda x: x["average_confidence"]),
        "patterns": patterns
    }

def main():
    data = json.loads(sys.stdin.read())
    student_id = data.get('student_id', 'unknown')
    syllabus_id = data.get('syllabus_id', 'unknown')
    
    assessment = assess_weaknesses(student_id, syllabus_id)
    
    if assessment["weaknesses"]:
        weakness_list = "\n".join(
            f"  - {w['concept']} (avg confidence: {w['average_confidence']:.0f}%)" 
            for w in assessment["weaknesses"][:3]
        )
        
        print(json.dumps({
            "decision": "allow",
            "system_message": f"""
🔴 **Weakness Assessment**

The following concepts need reinforcement:
{weakness_list}

💡 Recommended action:
Use `/tutor focus {assessment['weaknesses'][0]['concept']}` to start a targeted session.
"""
        }))
    else:
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()