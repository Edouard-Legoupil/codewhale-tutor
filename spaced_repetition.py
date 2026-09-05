# spaced_repetition.py

import json
from datetime import datetime, timedelta
from pathlib import Path

PROGRESS_DIR = Path.home() / ".codewhale" / "tutor_progress"

class SpacedRepetition:
    def __init__(self, student_id, syllabus_id):
        self.student_id = student_id
        self.syllabus_id = syllabus_id
        self.progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
        self.load_progress()
    
    def load_progress(self):
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                self.progress = json.load(f)
        else:
            self.progress = {}
        self.progress.setdefault("review_queue", [])
    
    def schedule_review(self, concept: str, mastery: float):
        """Schedule a review based on mastery level"""
        intervals = {
            0.0: timedelta(hours=1),
            0.1: timedelta(hours=4),
            0.2: timedelta(hours=8),
            0.3: timedelta(days=1),
            0.4: timedelta(days=2),
            0.5: timedelta(days=3),
            0.6: timedelta(days=5),
            0.7: timedelta(days=7),
            0.8: timedelta(days=10),
            0.9: timedelta(days=14)
        }
        
        # Determine interval
        interval = intervals.get(int(mastery * 10) / 10, timedelta(days=1))
        next_review = datetime.now() + interval
        
        self.progress["review_queue"].append({
            "concept": concept,
            "next_review": next_review.isoformat(),
            "mastery": mastery
        })
        
        self.save_progress()
    
    def get_due_reviews(self):
        """Get concepts due for review"""
        now = datetime.now()
        due = []
        
        for item in self.progress.get("review_queue", []):
            next_review = datetime.fromisoformat(item["next_review"])
            if next_review <= now:
                due.append(item)
        
        return due