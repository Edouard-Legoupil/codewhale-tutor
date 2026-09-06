#!/usr/bin/env python3
"""
Assess weaknesses from the evidence trail (attempts), classify the *nature* of
each difficulty, and recommend the matching tutoring action.

Aligned with the error-diagnosis layer of the reference model: a weakness is not
just "a concept with low confidence", it is a concept where the learner shows a
recurring error type (knowledge, procedure, reasoning, transfer…).
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

try:
    import tutor_engine
except ImportError:  # pragma: no cover
    tutor_engine = None

PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"


def assess_weaknesses(student_id: str, syllabus_id: str) -> dict:
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if not progress_file.exists():
        return {"weaknesses": [], "patterns": []}

    with open(progress_file, 'r') as f:
        progress = json.load(f)

    attempts = progress.get("attempts", [])
    history = progress.get("response_history", [])
    concept_mastery = progress.get("concept_mastery", {})

    # Group attempts per concept.
    attempts_by_concept = defaultdict(list)
    for a in attempts:
        attempts_by_concept[a.get("concept", "general")].append(a)

    weaknesses = []
    for concept, atts in attempts_by_concept.items():
        error_counts = defaultdict(int)
        n_wrong = 0
        for a in atts:
            if not a.get("correct"):
                n_wrong += 1
            et = a.get("error_type")
            if et:
                error_counts[et] += 1

        if not n_wrong:
            continue

        evidence = tutor_engine.build_evidence(atts) if tutor_engine else {}
        score = concept_mastery.get(concept)
        state = tutor_engine.mastery_state(score, evidence) if tutor_engine else "en_cours"

        top_errors = sorted(error_counts.items(), key=lambda x: -x[1])[:3]
        weaknesses.append({
            "concept": concept,
            "state": state,
            "score": score,
            "attempts": len(atts),
            "wrong": n_wrong,
            "error_types": [
                {
                    "type": et,
                    "label": (tutor_engine.ERROR_TYPES.get(et, {}) or {}).get("label", et) if tutor_engine else et,
                    "action": (tutor_engine.ERROR_TYPES.get(et, {}) or {}).get("action", "") if tutor_engine else "",
                    "count": count,
                }
                for et, count in top_errors
            ],
        })

    # Order: most wrong first, then lowest score.
    weaknesses.sort(key=lambda w: (-w["wrong"], (w["score"] if w["score"] is not None else 0)))

    patterns = []
    if len(history) > 5:
        confidence_trend = [h.get("confidence", 50) for h in history[-10:]]
        if confidence_trend and confidence_trend[-1] < confidence_trend[0]:
            patterns.append("confidence_trend: decreasing")

    return {"weaknesses": weaknesses, "patterns": patterns}


def main():
    data = json.loads(sys.stdin.read())
    student_id = data.get('student_id', 'unknown')
    syllabus_id = data.get('syllabus_id', 'unknown')

    assessment = assess_weaknesses(student_id, syllabus_id)

    if assessment["weaknesses"]:
        lines = []
        for w in assessment["weaknesses"][:3]:
            lines.append(f"  - {w['concept']} ({w['state']})")
            for et in w["error_types"]:
                lines.append(f"      • {et['label']}: {et['action']}")
        print(json.dumps({
            "decision": "allow",
            "system_message": "🔴 **Weakness Assessment**\n\n" + "\n".join(lines),
            "weaknesses": assessment["weaknesses"],
        }))
    else:
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
