# learning_style_analyzer.py

def analyze_learning_style(student_id: str, syllabus_id: str) -> dict:
    """Analyze student's learning style from their responses"""
    
    progress_file = PROGRESS_DIR / f"{student_id}_{syllabus_id}.json"
    if not progress_file.exists():
        return {"style": "balanced", "recommendations": []}
    
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    history = progress.get("history", [])
    
    # Count indicators
    visual = 0
    auditory = 0
    kinesthetic = 0
    reading = 0
    
    for entry in history:
        response = entry.get("response", "").lower()
        
        if any(word in response for word in ["see", "look", "visual", "diagram", "draw"]):
            visual += 1
        if any(word in response for word in ["hear", "listen", "sound", "say", "speak"]):
            auditory += 1
        if any(word in response for word in ["feel", "build", "create", "practice", "hands"]):
            kinesthetic += 1
        if any(word in response for word in ["write", "read", "list", "note", "book"]):
            reading += 1
    
    styles = {
        "visual": visual,
        "auditory": auditory,
        "kinesthetic": kinesthetic,
        "reading": reading
    }
    
    dominant = max(styles, key=styles.get)
    
    # Recommendations based on style
    recommendations = {
        "visual": [
            "Use diagrams and mind maps",
            "Color-code your notes",
            "Visualize concepts",
            "Watch video explanations"
        ],
        "auditory": [
            "Explain concepts out loud",
            "Record and listen to summaries",
            "Discuss topics with others",
            "Use mnemonics with rhythm"
        ],
        "kinesthetic": [
            "Build models or prototypes",
            "Practice with hands-on exercises",
            "Use physical flashcards",
            "Take frequent movement breaks"
        ],
        "reading": [
            "Take detailed notes",
            "Read multiple sources",
            "Summarize in your own words",
            "Create study guides"
        ]
    }
    
    return {
        "dominant_style": dominant,
        "style_scores": styles,
        "recommendations": recommendations.get(dominant, [])
    }