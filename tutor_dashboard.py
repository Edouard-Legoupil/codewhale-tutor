#!/usr/bin/env python3
"""
FastAPI backend for the tutor progress dashboard
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid
import os

app = FastAPI(title="Tutor Dashboard API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directories
PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"
SYLLABI_DIR = Path.home() / ".codewhale" / "syllabi"
EXAMS_DIR = Path.home() / ".codewhale" / "exams"
CHEATSHEETS_DIR = Path.home() / ".codewhale" / "cheatsheets"

PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

# --- Data Models ---

class StudentProfile(BaseModel):
    student_id: str
    name: str
    email: Optional[str] = None
    join_date: str
    learning_style: str = "balanced"
    active_syllabi: List[str] = []

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
    total_students: int
    total_syllabi: int
    total_exams: int
    avg_learning_rate: float
    most_learned_concepts: List[str]
    most_challenging_concepts: List[str]
    recent_activity: List[Dict]

# --- API Endpoints ---

@app.get("/api/students", response_model=List[StudentProfile])
async def get_students():
    """Get all student profiles"""
    students = []
    progress_files = list(PROGRESS_DIR.glob("*.json"))
    
    # Extract unique student IDs
    student_ids = set()
    for file in progress_files:
        if '_' in file.stem:
            student_id = file.stem.split('_')[0]
            student_ids.add(student_id)
    
    for student_id in student_ids:
        # Get student data from first available file
        for file in progress_files:
            if file.stem.startswith(student_id):
                with open(file, 'r') as f:
                    data = json.load(f)
                    students.append(StudentProfile(
                        student_id=student_id,
                        name=student_id.replace('_', ' ').title(),
                        join_date=data.get('last_session', datetime.now().isoformat()),
                        learning_style=data.get('learning_style', 'balanced'),
                        active_syllabi=[f.stem.split('_')[1] for f in progress_files if f.stem.startswith(student_id)]
                    ))
                break
    
    return students

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
    """Get learning analytics for a student"""
    progress_files = list(PROGRESS_DIR.glob(f"{student_id}_*.json"))
    
    all_concepts = {}
    weak_concepts = []
    total_sessions = 0
    learning_rate = 0
    
    for file in progress_files:
        with open(file, 'r') as f:
            data = json.load(f)
        
        for concept, mastery in data.get('concept_mastery', {}).items():
            if concept not in all_concepts:
                all_concepts[concept] = []
            all_concepts[concept].append(mastery)
        
        weak_concepts.extend(data.get('weaknesses', []))
        total_sessions += len(data.get('response_history', [])) // 5 + 1
    
    # Calculate rates
    if all_concepts:
        avg_improvement = sum(max(0, scores[-1] - scores[0]) for scores in all_concepts.values() if len(scores) > 1) / len(all_concepts)
        learning_rate = avg_improvement / total_sessions if total_sessions > 0 else 0
    
    # Most challenging concepts
    challenging = sorted(all_concepts.items(), key=lambda x: min(x[1]) if x[1] else 0)[:5]

    # Error patterns and calibration from practice attempts
    error_counts = {}
    n_attempts = 0
    overconfidence_sum = 0.0
    for file in progress_files:
        with open(file, 'r') as f:
            data = json.load(f)
        for a in data.get('attempts', []):
            n_attempts += 1
            if not a.get('correct'):
                t = a.get('error_type') or 'other'
                error_counts[t] = error_counts.get(t, 0) + 1
            pred = a.get('predicted_confidence', 50) / 100.0
            actual = 1.0 if a.get('correct') else 0.0
            overconfidence_sum += max(0, pred - actual)

    error_patterns = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    overconfidence = overconfidence_sum / n_attempts if n_attempts else 0.0

    return {
        "student_id": student_id,
        "total_concepts": len(all_concepts),
        "weak_concepts_count": len(weak_concepts),
        "total_sessions": total_sessions,
        "learning_rate": learning_rate,
        "most_challenging": [c[0] for c in challenging if c[0] not in weak_concepts],
        "concept_progress": {c: scores[-1] if scores else 0 for c, scores in all_concepts.items()},
        "error_patterns": error_patterns,
        "overconfidence": overconfidence,
        "attempt_count": n_attempts
    }

@app.get("/api/exams")
async def get_exams(syllabus_id: Optional[str] = None):
    """Get all exams or exams for a syllabus"""
    exam_files = list(EXAMS_DIR.glob("*.json"))
    
    if syllabus_id:
        exam_files = [f for f in exam_files if f.stem.endswith(syllabus_id)]
    
    exams = []
    for file in exam_files:
        with open(file, 'r') as f:
            data = json.load(f)
        
        exam_analysis = ExamAnalysis(
            exam_id=data.get('id', file.stem),
            syllabus_id=data.get('syllabus_id', 'unknown'),
            total_questions=len(data.get('questions', [])),
            difficulty_distribution=data.get('difficulty_distribution', {}),
            concept_frequencies=dict(zip(data.get('concepts_tested', []), [1]*len(data.get('concepts_tested', [])))),
            avg_question_length=sum(len(q.get('text', '')) for q in data.get('questions', [])) / len(data.get('questions', [1])) if data.get('questions') else 0,
            question_types={}
        )
        exams.append(exam_analysis)
    
    return exams

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get overall analytics summary"""
    progress_files = list(PROGRESS_DIR.glob("*.json"))
    syllabus_files = list(SYLLABI_DIR.glob("*.json"))
    exam_files = list(EXAMS_DIR.glob("*.json"))
    
    # Student count
    student_ids = set()
    for file in progress_files:
        if '_' in file.stem:
            student_ids.add(file.stem.split('_')[0])
    
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
        total_students=len(student_ids),
        total_syllabi=len(syllabus_files),
        total_exams=len(exam_files),
        avg_learning_rate=0.15,  # Placeholder - calculate from data
        most_learned_concepts=sorted(concepts.items(), key=lambda x: x[1], reverse=True)[:5],
        most_challenging_concepts=sorted(weak_concepts.items(), key=lambda x: x[1], reverse=True)[:5],
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

# --- Serve Static Files (React Build) ---
# Uncomment if serving React build from same server
# app.mount("/", StaticFiles(directory="dashboard/dist", html=True), name="dashboard")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)