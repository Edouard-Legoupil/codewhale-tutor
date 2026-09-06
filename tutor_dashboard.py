#!/usr/bin/env python3
"""
FastAPI backend for the tutor progress dashboard
"""

import asyncio
import base64
import hashlib
import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import library
import tutor_engine

# Data directories (single source of truth: library.py)
PROGRESS_DIR = library.PROGRESS_DIR
SYLLABI_DIR = library.SYLLABI_DIR
EXAMS_DIR = library.EXAMS_DIR
CHEATSHEETS_DIR = library.CHEATSHEETS_DIR

_LAST_SYNC_FP: Optional[str] = None


def _scan_fingerprint() -> str:
    """Cheap fingerprint of the raw source files (names + mtime + size)."""
    parts = []
    for d in (SYLLABI_DIR, EXAMS_DIR):
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.suffix.lower() not in library.SOURCE_EXTENSIONS:
                continue
            st = p.stat()
            parts.append(f"{p.name}:{st.st_mtime}:{st.st_size}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


async def _watcher() -> None:
    """Poll the source folders and re-sync whenever a document is added/changed."""
    global _LAST_SYNC_FP
    while True:
        await asyncio.sleep(5)
        try:
            fp = _scan_fingerprint()
            if fp != _LAST_SYNC_FP:
                await asyncio.to_thread(library.sync_library)
                _LAST_SYNC_FP = fp
        except Exception:  # noqa: BLE001
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _LAST_SYNC_FP
    try:
        await asyncio.to_thread(library.sync_library)
        _LAST_SYNC_FP = _scan_fingerprint()
    except Exception:  # noqa: BLE001
        pass
    task = asyncio.create_task(_watcher())
    yield
    task.cancel()


app = FastAPI(title="Tutor Dashboard API", lifespan=lifespan)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

library.ensure_dirs()

# --- Data Models ---

class ConceptMastery(BaseModel):
    concept: str
    mastery: float
    attempts: int
    trend: str = "stable"  # improving, declining, stable

class StudentProgress(BaseModel):
    student_id: str
    syllabus_id: str
    syllabus_name: str
    current_stage: float
    overall_mastery: float
    concept_mastery: List[ConceptMastery]
    weaknesses: List[str]
    response_history: List[Dict]
    last_session: Optional[str]
    session_count: int
    exam_scores: List[Dict]
    learning_objectives: List[str] = []

class ExamAnalysis(BaseModel):
    exam_id: str
    syllabus_id: str
    total_questions: int
    difficulty_distribution: Dict[str, int]
    concept_frequencies: Dict[str, int]
    avg_question_length: float
    question_types: Dict[str, int]

class AnalyticsSummary(BaseModel):
    total_syllabi: int
    total_exams: int
    total_mock_exams: int
    avg_learning_rate: float
    most_learned_concepts: List[str]
    most_challenging_concepts: List[str]
    recent_activity: List[Dict]

# --- API Endpoints ---

@app.get("/api/syllabi")
async def get_syllabi():
    """List organised syllabi from the library registry."""
    reg = library.load_registry()
    return list(reg.get("syllabi", {}).values())


@app.get("/api/syllabi/{syllabus_id}")
async def get_syllabus(syllabus_id: str):
    """Full organised syllabus (concepts, objectives, sources, linked exams)."""
    p = SYLLABI_DIR / f"{syllabus_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Syllabus not found")
    data = json.loads(p.read_text(encoding="utf-8"))
    reg = library.load_registry()
    data["summary"] = reg.get("syllabi", {}).get(syllabus_id, {})
    return data


@app.get("/api/cheatsheets/{syllabus_id}")
async def get_cheatsheet(syllabus_id: str):
    """Return the generated cheatsheet Markdown for a syllabus."""
    p = CHEATSHEETS_DIR / f"{syllabus_id}_cheatsheet.md"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Cheatsheet not found")
    return {"syllabus_id": syllabus_id, "content": p.read_text(encoding="utf-8")}


@app.post("/api/sync")
async def sync_now():
    """Re-run the ingestion pipeline immediately and return a summary."""
    global _LAST_SYNC_FP
    summary = await asyncio.to_thread(library.sync_library)
    _LAST_SYNC_FP = _scan_fingerprint()
    return summary

def _progress_detail(data: dict, student_id: str, syllabus_id: str) -> dict:
    """Build a per-syllabus progress view for the single learner."""
    syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
    syllabus_name = syllabus_id
    learning_objectives = []
    if syllabus_file.exists():
        try:
            with open(syllabus_file, "r", encoding="utf-8") as f:
                sd = json.load(f)
            syllabus_name = sd.get("name", syllabus_id)
            learning_objectives = sd.get("learning_objectives", [])
        except (json.JSONDecodeError, OSError):
            pass

    attempts_by_concept: Dict[str, List[Dict]] = {}
    for a in data.get("attempts", []) or []:
        attempts_by_concept.setdefault(a.get("concept"), []).append(a)

    concept_mastery = []
    for concept, score in data.get("concept_mastery", {}).items():
        history = [h for h in data.get("response_history", []) if h.get("concept") == concept]
        trend = "stable"
        if len(history) >= 3:
            recent = [h.get("confidence", 50) for h in history[-3:]]
            if recent[-1] > recent[0] + 10:
                trend = "improving"
            elif recent[-1] < recent[0] - 10:
                trend = "declining"
        evidence = tutor_engine.build_evidence(attempts_by_concept.get(concept, []))
        status = tutor_engine.mastery_state(score, evidence)
        observed: Dict[str, int] = {}
        for a in attempts_by_concept.get(concept, []):
            et = a.get("error_type")
            if et:
                observed[et] = observed.get(et, 0) + 1
        concept_mastery.append({
            "concept": concept, "mastery": score, "attempts": len(history),
            "trend": trend, "mastery_state": status,
            "evidence": evidence,
            "observed_errors": sorted(observed.items(), key=lambda x: -x[1]),
        })

    cm = data.get("concept_mastery", {})
    overall = (sum(cm.values()) / len(cm)) if cm else 0
    return {
        "student_id": student_id,
        "syllabus_id": syllabus_id,
        "syllabus_name": syllabus_name,
        "current_stage": data.get("current_stage", 0),
        "overall_mastery": overall,
        "concept_mastery": concept_mastery,
        "weaknesses": data.get("weaknesses", []),
        "response_history": data.get("response_history", [])[-20:],
        "last_session": data.get("last_session"),
        "session_count": len(data.get("response_history", [])) // 5 + 1,
        "exam_scores": data.get("exam_scores", []),
        "learning_objectives": learning_objectives,
    }


def _aggregate_analytics(progress_files: list) -> dict:
    """Aggregate analytics across a set of progress files."""
    all_concepts = {}
    weak_concepts = []
    total_sessions = 0

    for file in progress_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for concept, mastery in data.get("concept_mastery", {}).items():
            all_concepts.setdefault(concept, []).append(mastery)
        weak_concepts.extend(data.get("weaknesses", []))
        total_sessions += len(data.get("response_history", [])) // 5 + 1

    learning_rate = 0
    if all_concepts:
        avg_improvement = sum(
            max(0, scores[-1] - scores[0]) for scores in all_concepts.values() if len(scores) > 1
        ) / len(all_concepts)
        learning_rate = avg_improvement / total_sessions if total_sessions > 0 else 0

    challenging = sorted(all_concepts.items(), key=lambda x: min(x[1]) if x[1] else 0)[:5]

    error_counts = {}
    n_attempts = 0
    overconfidence_sum = 0.0
    for file in progress_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for a in data.get("attempts", []):
            n_attempts += 1
            if not a.get("correct"):
                error_counts[a.get("error_type") or "other"] = error_counts.get(a.get("error_type") or "other", 0) + 1
            pred = a.get("predicted_confidence", 50) / 100.0
            actual = 1.0 if a.get("correct") else 0.0
            overconfidence_sum += max(0, pred - actual)

    return {
        "total_concepts": len(all_concepts),
        "weak_concepts_count": len(weak_concepts),
        "total_sessions": total_sessions,
        "learning_rate": learning_rate,
        "most_challenging": [c[0] for c in challenging if c[0] not in weak_concepts],
        "concept_progress": {c: scores[-1] if scores else 0 for c, scores in all_concepts.items()},
        "error_patterns": sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        "overconfidence": overconfidence_sum / n_attempts if n_attempts else 0.0,
        "attempt_count": n_attempts,
    }


@app.get("/api/progress")
async def get_progress():
    """All learning progress for the single learner, one entry per syllabus."""
    out = []
    for file in sorted(PROGRESS_DIR.glob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        student_id = data.get("student_id") or (file.stem.split("_")[0] if "_" in file.stem else "me")
        syllabus_id = data.get("syllabus_id") or (file.stem.split("_", 1)[1] if "_" in file.stem else file.stem)
        out.append(_progress_detail(data, student_id, syllabus_id))
    return out


@app.get("/api/analytics")
async def get_analytics():
    """Aggregated learning analytics for the single learner."""
    return _aggregate_analytics(list(PROGRESS_DIR.glob("*.json")))

@app.get("/api/students/{student_id}/progress")
async def get_student_progress(student_id: str, syllabus_id: Optional[str] = None):
    """Get detailed progress for a student"""
    if syllabus_id:
        # Get specific syllabus progress
        progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
        if not progress_file.exists():
            raise HTTPException(status_code=404, detail="Progress not found")
        
        with open(progress_file, 'r') as f:
            data = json.load(f)
        
        # Load syllabus info
        syllabus_file = SYLLABI_DIR / f"{syllabus_id}.json"
        syllabus_name = syllabus_id
        learning_objectives = []
        if syllabus_file.exists():
            with open(syllabus_file, 'r') as f:
                syllabus_data = json.load(f)
                syllabus_name = syllabus_data.get('name', syllabus_id)
                learning_objectives = syllabus_data.get('learning_objectives', [])
        
        concept_mastery = []
        for concept, score in data.get('concept_mastery', {}).items():
            # Calculate trend (simplified)
            history = [h for h in data.get('response_history', []) if h.get('concept') == concept]
            trend = "stable"
            if len(history) >= 3:
                recent = [h.get('confidence', 50) for h in history[-3:]]
                if recent[-1] > recent[0] + 10:
                    trend = "improving"
                elif recent[-1] < recent[0] - 10:
                    trend = "declining"
            
            concept_mastery.append(ConceptMastery(
                concept=concept,
                mastery=score,
                attempts=len(history),
                trend=trend
            ))
        
        return StudentProgress(
            student_id=student_id,
            syllabus_id=syllabus_id,
            syllabus_name=syllabus_name,
            current_stage=data.get('current_stage', 0),
            overall_mastery=sum(data.get('concept_mastery', {}).values()) / len(data.get('concept_mastery', {1: 0})) if data.get('concept_mastery') else 0,
            concept_mastery=concept_mastery,
            weaknesses=data.get('weaknesses', []),
            response_history=data.get('response_history', [])[-20:],  # Last 20
            last_session=data.get('last_session'),
            session_count=len(data.get('response_history', [])) // 5 + 1,
            exam_scores=data.get('exam_scores', []),
            learning_objectives=learning_objectives
        )
    else:
        # Get all syllabi progress
        progress_files = list(PROGRESS_DIR.glob(f"{student_id}_*.json"))
        syllabi_progress = []
        
        for file in progress_files:
            syllabus_id = file.stem.split('_')[1]
            try:
                progress = await get_student_progress(student_id, syllabus_id)
                syllabi_progress.append(progress)
            except:
                continue
        
        return syllabi_progress

@app.get("/api/students/{student_id}/analytics")
async def get_student_analytics(student_id: str):
    """Get learning analytics for a student (kept for compatibility)."""
    progress_files = list(PROGRESS_DIR.glob(f"{student_id}_*.json"))
    result = _aggregate_analytics(progress_files)
    result["student_id"] = student_id
    return result

@app.get("/api/exams")
async def get_exams(syllabus_id: Optional[str] = None):
    """Get all exams (real + inferred mock exams) from the registry."""
    reg = library.load_registry()
    exams = list(reg.get("exams", {}).values())
    if syllabus_id:
        exams = [e for e in exams if e.get("syllabus_id") == syllabus_id]
    return exams

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get overall analytics summary"""
    progress_files = list(PROGRESS_DIR.glob("*.json"))
    reg = library.load_registry()
    syllabi = list(reg.get("syllabi", {}).values())
    exams = list(reg.get("exams", {}).values())
    
    # Most learned concepts
    concepts = {}
    for file in progress_files:
        with open(file, 'r') as f:
            data = json.load(f)
        for concept, mastery in data.get('concept_mastery', {}).items():
            concepts[concept] = concepts.get(concept, 0) + 1
    
    # Most challenging concepts
    weak_concepts = {}
    for file in progress_files:
        with open(file, 'r') as f:
            data = json.load(f)
        for weakness in data.get('weaknesses', []):
            weak_concepts[weakness] = weak_concepts.get(weakness, 0) + 1
    
    # Recent activity
    recent_activity = []
    for file in progress_files:
        with open(file, 'r') as f:
            data = json.load(f)
        history = data.get('response_history', [])
        if history:
            recent = history[-1] if history else {}
            recent_activity.append({
                "student": file.stem.split('_')[0],
                "concept": recent.get('concept', 'Unknown'),
                "timestamp": recent.get('timestamp', ''),
                "confidence": recent.get('confidence', 0)
            })
    
    recent_activity = sorted(recent_activity, key=lambda x: x['timestamp'], reverse=True)[:10]
    
    return AnalyticsSummary(
        total_syllabi=len(syllabi),
        total_exams=sum(1 for e in exams if e.get("kind") != "mock"),
        total_mock_exams=sum(1 for e in exams if e.get("kind") == "mock"),
        avg_learning_rate=0.15,  # Placeholder - calculate from data
        most_learned_concepts=[c for c, _ in sorted(concepts.items(), key=lambda x: x[1], reverse=True)[:5]],
        most_challenging_concepts=[c for c, _ in sorted(weak_concepts.items(), key=lambda x: x[1], reverse=True)[:5]],
        recent_activity=recent_activity
    )

@app.post("/api/students/{student_id}/progress")
async def update_student_progress_endpoint(student_id: str, data: Dict):
    """Update student progress via API"""
    syllabus_id = data.get('syllabus_id')
    concept = data.get('concept')
    mastery = data.get('mastery')
    response = data.get('response', '')
    confidence = data.get('confidence', 50)
    
    if not syllabus_id or not concept or mastery is None:
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    
    # Load or create progress
    if progress_file.exists():
        with open(progress_file, 'r') as f:
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
            "last_session": None,
            "exam_scores": []
        }
    
    # Update
    progress["concept_mastery"][concept] = mastery
    progress["last_session"] = datetime.now().isoformat()
    
    progress["response_history"].append({
        "concept": concept,
        "response": response,
        "mastery": mastery,
        "confidence": confidence,
        "timestamp": datetime.now().isoformat()
    })
    
    # Update weaknesses
    if mastery < 0.6 and concept not in progress["weaknesses"]:
        progress["weaknesses"].append(concept)
    elif mastery >= 0.6 and concept in progress["weaknesses"]:
        progress["weaknesses"].remove(concept)
    
    # Update stage
    mastered = sum(1 for m in progress["concept_mastery"].values() if m >= 0.7)
    total = len(progress["concept_mastery"])
    if total > 0:
        progress["current_stage"] = (mastered / total) * 100
    
    # Save
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)
    
    return {"status": "success", "message": "Progress updated"}

@app.get("/api/exams/{exam_id}/analysis")
async def analyze_exam(exam_id: str):
    """Get detailed exam analysis"""
    exam_file = EXAMS_DIR / f"{exam_id}.json"
    if not exam_file.exists():
        raise HTTPException(status_code=404, detail="Exam not found")
    
    with open(exam_file, 'r') as f:
        exam = json.load(f)
    
    questions = exam.get('questions', [])
    
    # Classify question types
    question_types = {"definition": 0, "conceptual": 0, "calculation": 0, "application": 0, "analysis": 0}
    
    for q in questions:
        text = q.get('text', '').lower()
        if any(word in text for word in ['define', 'what is', 'list', 'identify']):
            question_types['definition'] += 1
        elif any(word in text for word in ['explain', 'describe', 'why']):
            question_types['conceptual'] += 1
        elif any(word in text for word in ['calculate', 'compute', 'solve', 'equation']):
            question_types['calculation'] += 1
        elif any(word in text for word in ['apply', 'use', 'example']):
            question_types['application'] += 1
        elif any(word in text for word in ['compare', 'contrast', 'evaluate', 'analyze']):
            question_types['analysis'] += 1
    
    # Estimate difficulty based on length and complexity
    difficulties = {'easy': 0, 'medium': 0, 'hard': 0}
    for q in questions:
        text_length = len(q.get('text', ''))
        if text_length < 50:
            difficulties['easy'] += 1
        elif text_length < 150:
            difficulties['medium'] += 1
        else:
            difficulties['hard'] += 1
    
    return {
        "exam_id": exam_id,
        "question_types": question_types,
        "difficulty_distribution": difficulties,
        "total_questions": len(questions),
        "concepts": exam.get('concepts_tested', []),
        "sample_questions": questions[:3]  # Show first # Show first 3 for preview
    }


# --- Layered competence model + pedagogical engine ---------------------------

class DiagnoseRequest(BaseModel):
    question: str = ""
    response: str = ""
    correct: Optional[bool] = None
    confidence: Optional[float] = None


class ChatRequest(BaseModel):
    message: str = ""
    locale: Optional[str] = "en"
    persona: Optional[Dict] = None
    syllabus_id: Optional[str] = None


@app.get("/api/model/{syllabus_id}")
async def get_model(syllabus_id: str):
    """Full layered model: domains, observable competencies and prerequisite graph."""
    p = SYLLABI_DIR / f"{syllabus_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Syllabus not found")
    data = json.loads(p.read_text(encoding="utf-8"))
    return {
        "syllabus_id": syllabus_id,
        "name": data.get("name", syllabus_id),
        "discipline": data.get("discipline", "general"),
        "source_status": data.get("source_status", "document_interne"),
        "domaines": data.get("domaines", []) or data.get("modules", []),
        "competences": data.get("competences", []),
        "graph": data.get("competence_graph", {"nodes": [], "edges": []}),
        "learning_objectives": data.get("learning_objectives", []),
    }


@app.get("/api/competencies")
async def list_competencies(syllabus_id: Optional[str] = None):
    """Flat list of observable competencies across one or all syllabi."""
    files = [SYLLABI_DIR / f"{syllabus_id}.json"] if syllabus_id else sorted(SYLLABI_DIR.glob("*.json"))
    out: List[Dict] = []
    for p in files:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for c in data.get("competences", []):
            out.append({**c, "syllabus_id": data.get("id", p.stem)})
    return out


def _learner_state_for_syllabus(syllabus_id: str, competences: List[Dict]) -> Dict:
    """Merge raw progress files into a per-competence learner state."""
    name_to_id = {c.get("name"): c.get("id") for c in competences}
    learner: Dict[str, Dict] = {}
    for f in sorted(PROGRESS_DIR.glob(f"*_{syllabus_id}.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        st = tutor_engine.build_learner_state(data)
        for name, s in st.items():
            learner[name_to_id.get(name, name)] = s
    return learner


@app.get("/api/policy/next/{syllabus_id}")
async def policy_next(syllabus_id: str):
    """Adaptive next-action recommendation (the tutor policy, §18)."""
    p = SYLLABI_DIR / f"{syllabus_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Syllabus not found")
    data = json.loads(p.read_text(encoding="utf-8"))
    competences = data.get("competences", [])
    learner = _learner_state_for_syllabus(syllabus_id, competences)
    return tutor_engine.next_action(competences, learner)


@app.post("/api/diagnose")
async def diagnose(req: DiagnoseRequest):
    """Diagnose the nature of an error and recommend the tutoring action."""
    return tutor_engine.diagnose_error(
        req.question, req.response, req.correct,
        {"confidence": req.confidence if req.confidence is not None else 50},
    )


@app.get("/api/learner-model")
async def learner_model(syllabus_id: Optional[str] = None):
    """Five-state learner model derived from evidence, separated from the curriculum."""
    result: Dict[str, Dict] = {}
    for f in sorted(PROGRESS_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        sid = data.get("syllabus_id") or (f.stem.split("_", 1)[1] if "_" in f.stem else f.stem)
        if syllabus_id and sid != syllabus_id:
            continue
        student_id = data.get("student_id") or (f.stem.split("_")[0] if "_" in f.stem else "me")
        entry = result.setdefault(sid, {"syllabus_id": sid, "student_id": student_id, "states": {}})
        entry["states"].update(tutor_engine.build_learner_state(data))
    return list(result.values())


def _chat_context(locale: str, persona: Optional[Dict], syllabus_id: Optional[str]) -> Dict:
    """Assemble the context (persona + learner + policy) for a tutor turn."""
    reg = library.load_registry()
    syllabi = list(reg.get("syllabi", {}).values())
    exams = list(reg.get("exams", {}).values())

    weaknesses: List[str] = []
    for f in PROGRESS_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue
        weaknesses.extend(data.get("weaknesses", []) or [])

    next_action: Dict = {}
    sid = syllabus_id or (syllabi[0]["id"] if syllabi else None)
    if sid:
        p = SYLLABI_DIR / f"{sid}.json"
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                competences = data.get("competences", [])
                learner = _learner_state_for_syllabus(sid, competences)
                next_action = tutor_engine.next_action(competences, learner)
            except (json.JSONDecodeError, OSError):
                next_action = {}

    return {
        "locale": locale or "en",
        "persona": persona or {},
        "weaknesses": list(dict.fromkeys(weaknesses)),
        "next_action": next_action,
        "syllabi": [s.get("name", s.get("id")) for s in syllabi],
        "exam_count": len(exams),
    }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Hybrid tutor chat: LLM-backed when a provider is configured, else rules."""
    context = _chat_context(req.locale, req.persona, req.syllabus_id)
    return tutor_engine.tutor_reply(req.message, context)


@app.post("/api/activity")
async def activity(req: ChatRequest):
    """Generate a practice activity (hybrid) for the recommended competence."""
    sid = req.syllabus_id
    if not sid:
        reg = library.load_registry()
        syllabi = list(reg.get("syllabi", {}).values())
        if not syllabi:
            raise HTTPException(status_code=404, detail="No syllabus available")
        sid = syllabi[0]["id"]
    p = SYLLABI_DIR / f"{sid}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Syllabus not found")
    data = json.loads(p.read_text(encoding="utf-8"))
    competences = data.get("competences", [])
    if not competences:
        raise HTTPException(status_code=404, detail="No competences modelled")
    learner = _learner_state_for_syllabus(sid, competences)
    na = tutor_engine.next_action(competences, learner)
    target = competences[0]
    if na.get("target_competence"):
        for c in competences:
            if c.get("id") == na["target_competence"]:
                target = c
                break
    state = learner.get(target.get("id")) or {}
    return tutor_engine.generate_activity(target, state)


# --- Setup / settings: sources, upload, delete, model editing, LLM -----------

class UploadRequest(BaseModel):
    filename: str
    kind: str = "syllabus"  # syllabus | exam
    data: str = ""
    encoding: str = "text"  # text | base64


class ModelUpdateRequest(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    learning_objectives: Optional[List[str]] = None
    competences: Optional[List[Dict]] = None
    domaines: Optional[List[Dict]] = None


class LlmSettingsRequest(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None


@app.get("/api/sources")
async def list_sources():
    """List the raw syllabus/exam files currently on disk."""
    out: List[Dict] = []
    for kind, d in (("syllabus", SYLLABI_DIR), ("exam", EXAMS_DIR)):
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if not p.is_file() or p.suffix.lower() not in library.SOURCE_EXTENSIONS:
                continue
            out.append({
                "name": p.name,
                "rel": str(p.relative_to(library.CW_HOME)),
                "kind": kind,
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            })
    return out


@app.post("/api/upload")
async def upload(req: UploadRequest):
    """Write an uploaded document into the syllabus/exam folder and re-sync."""
    if req.kind not in ("syllabus", "exam"):
        raise HTTPException(status_code=400, detail="kind must be 'syllabus' or 'exam'")
    name = Path(req.filename).name
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    dest_dir = SYLLABI_DIR if req.kind == "syllabus" else EXAMS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    try:
        content = base64.b64decode(req.data) if req.encoding == "base64" else req.data.encode("utf-8")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not decode content: {e}") from e
    dest.write_bytes(content)
    summary = await asyncio.to_thread(library.sync_library)
    return {"status": "ok", "saved": name, "summary": summary}


@app.delete("/api/syllabi/{syllabus_id}")
async def delete_syllabus(syllabus_id: str):
    """Remove a syllabus, its source files, generated artifacts and progress."""
    reg = library.load_registry()
    removed: List[str] = []
    for rel, info in list(reg.get("sources", {}).items()):
        if info.get("kind") == "syllabus" and info.get("syllabus_id") == syllabus_id:
            p = library.CW_HOME / rel
            if p.exists():
                p.unlink()
                removed.append(rel)
    for p in (SYLLABI_DIR / f"{syllabus_id}.json",
              CHEATSHEETS_DIR / f"{syllabus_id}_cheatsheet.md",
              EXAMS_DIR / f"{syllabus_id}_mock.json"):
        if p.exists():
            p.unlink()
    for p in PROGRESS_DIR.glob(f"*_{syllabus_id}.json"):
        p.unlink()
    summary = await asyncio.to_thread(library.sync_library)
    return {"status": "ok", "removed": removed, "summary": summary}


@app.put("/api/model/{syllabus_id}")
async def update_model(syllabus_id: str, req: ModelUpdateRequest):
    """Edit the generated model (name, objectives, domains, competences)."""
    p = SYLLABI_DIR / f"{syllabus_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Syllabus not found")
    data = json.loads(p.read_text(encoding="utf-8"))
    if req.name is not None:
        data["name"] = req.name
    if req.language is not None:
        data["language"] = req.language
    if req.learning_objectives is not None:
        data["learning_objectives"] = req.learning_objectives
    if req.competences is not None:
        data["competences"] = req.competences
        data["competence_graph"] = library._build_competence_graph(data)
    if req.domaines is not None:
        data["domaines"] = req.domaines
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    reg = library.load_registry()
    if syllabus_id in reg.get("syllabi", {}):
        s = reg["syllabi"][syllabus_id]
        s["name"] = data.get("name", s.get("name"))
        s["language"] = data.get("language", s.get("language"))
        s["competences"] = len(data.get("competences", []))
        s["learning_objectives"] = len(data.get("learning_objectives", []))
        s["domaines"] = len(data.get("domaines", []) or data.get("modules", []))
        s["updated_at"] = datetime.now().isoformat(timespec="seconds")
        library._save_registry(reg)
    return {"status": "ok", "syllabus_id": syllabus_id}


@app.get("/api/settings/llm")
async def get_llm_settings():
    """Current LLM configuration + Ollama availability probe."""
    cfg = tutor_engine.load_llm_config()
    return {
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model"),
        "api_key": cfg.get("api_key") or "",
        "has_key": bool(cfg.get("api_key")),
        "enabled": cfg.get("enabled"),
        "ollama": tutor_engine.list_ollama_models(),
    }


@app.put("/api/settings/llm")
async def put_llm_settings(req: LlmSettingsRequest):
    """Persist the LLM provider/model selection and invalidate the cached client."""
    current = tutor_engine.load_llm_config()
    cfg = {
        "base_url": req.base_url if req.base_url is not None else current.get("base_url"),
        "model": req.model if req.model is not None else current.get("model"),
        "api_key": req.api_key if req.api_key is not None else current.get("api_key"),
        "enabled": req.enabled if req.enabled is not None else current.get("enabled", True),
    }
    tutor_engine.write_llm_config_file(cfg)
    tutor_engine.reset_llm()
    return {"status": "ok", "config": {"base_url": cfg["base_url"], "model": cfg["model"], "enabled": cfg["enabled"]}}


# --- Serve Static Files (React Build) ---
# Uncomment if serving React build from same server
# app.mount("/", StaticFiles(directory="dashboard/dist", html=True), name="dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)