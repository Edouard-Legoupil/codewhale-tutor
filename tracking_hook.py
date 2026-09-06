#!/usr/bin/env python3
"""
Track student responses as *evidence*, diagnose the nature of errors, and
update the inferred mastery state.

This hook is the observation layer of the pedagogical loop described in
``approche_modelisation_tutorat_ia.md``: every interaction appends evidence
(attempt, correctness, error type, autonomy), which the engine turns into a
five-state mastery estimate (non_abordé → maîtrisé).
"""

import json
import sys
import re
import unicodedata
from pathlib import Path
from datetime import datetime

try:
    import tutor_engine
except ImportError:  # pragma: no cover - hook still works without the engine
    tutor_engine = None

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


def _update_mastery(current, correct, confidence):
    """Move a 0..1 mastery estimate toward the latest observation."""
    if correct is True:
        base = current if current is not None else 0.5
        return round(min(1.0, base + 0.25), 3)
    if correct is False:
        base = current if current is not None else 0.4
        return round(max(0.0, base - 0.25), 3)
    return round((confidence or 50) / 100.0, 3)


def main():
    data = json.loads(sys.stdin.read())

    student_id = data.get('student_id', 'unknown')
    syllabus_id = data.get('syllabus_id', 'unknown')
    question = data.get('question', '')
    response = data.get('response', '')
    concept = data.get('concept', 'general')
    correct = data.get('correct')  # optional explicit verdict
    support = data.get('support', 'independent')  # independent | guided | prompted
    transfer = bool(data.get('transfer', False))

    analysis = analyze_student_response(question, response)
    diagnosis = None
    if tutor_engine:
        diagnosis = tutor_engine.diagnose_error(question, response, correct, analysis)

    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            progress = json.load(f)
    else:
        progress = {}

    progress.setdefault("student_id", student_id)
    progress.setdefault("syllabus_id", syllabus_id)
    progress.setdefault("response_history", [])
    progress.setdefault("attempts", [])
    progress.setdefault("weaknesses", [])
    progress.setdefault("concept_mastery", {})
    progress.setdefault("current_stage", 0)
    progress.setdefault("last_session", None)

    # Evidence: one attempt per observation.
    attempt = {
        "timestamp": datetime.now().isoformat(),
        "concept": concept,
        "correct": correct,
        "error_type": diagnosis["primary"] if diagnosis else data.get('error_type'),
        "predicted_confidence": analysis["confidence"],
        "support": support,
        "transfer": transfer,
    }
    progress["attempts"].append(attempt)

    # Observable trace of the interaction.
    progress["response_history"].append({
        "timestamp": attempt["timestamp"],
        "concept": concept,
        "question": question,
        "response": response,
        "confidence": analysis["confidence"],
        "analysis": analysis,
        "diagnosis": diagnosis,
    })

    # Inferred mastery + weakness bookkeeping.
    progress["concept_mastery"][concept] = _update_mastery(
        progress["concept_mastery"].get(concept), correct, analysis["confidence"])

    evidence = tutor_engine.build_evidence([
        a for a in progress["attempts"] if a.get("concept") == concept
    ]) if tutor_engine else {}
    state = tutor_engine.mastery_state(progress["concept_mastery"][concept], evidence) if tutor_engine else "en_cours"

    if state in ("non_aborde", "en_cours") and concept not in progress["weaknesses"]:
        progress["weaknesses"].append(concept)
    elif state in ("acquis", "maitrise") and concept in progress["weaknesses"]:
        progress["weaknesses"].remove(concept)

    progress["last_session"] = datetime.now().isoformat()

    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)

    # Feedback grounded in the diagnostic (adaptation before repetition).
    if diagnosis:
        print(json.dumps({
            "decision": "allow",
            "system_message": f"🧠 {diagnosis['label']}\n\n{diagnosis['action']}",
            "diagnosis": diagnosis,
            "mastery_state": state,
        }))
    elif analysis["strategy_mentioned"]:
        print(json.dumps({"decision": "allow", "system_message": "🧠 Great job explaining your strategy!"}))
    else:
        print(json.dumps({"decision": "allow", "mastery_state": state}))


if __name__ == "__main__":
    main()
