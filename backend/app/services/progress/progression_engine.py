"""
BhashaBridge — Script Progression & Milestone Engine (M6)
Implements:
1. Automatic script progression recommendations (Roman -> Mixed -> Devanagari)
   based on the learner's independent script proficiency score.
2. Level 0–5 Milestones progression roadmap (Survival -> Script Mastery).
3. Targeted weak-topic identification.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    LanguageProfile, Milestone, Progress, PracticeAttempt
)

class ScriptProgressionEngine:
    """
    Evaluates script proficiency scores independently from language proficiency
    to recommend gradual transition from Roman script to Devanagari.
    """

    # Recommendation thresholds
    INTERMEDIATE_THRESHOLD = 0.35  # 35% script proficiency triggers Bridge recommendation
    ADVANCED_THRESHOLD = 0.70      # 70% script proficiency triggers Devanagari recommendation

    def evaluate_script_progression(self, profile: LanguageProfile) -> Dict[str, Any]:
        """
        Calculates composite script proficiency and recommends next Bridge Mode step.
        """
        rec = profile.devanagari_recognition or 0.3
        read = profile.devanagari_reading or 0.2
        bridge = profile.roman_to_devanagari or 0.35

        # Weighted script mastery score (Principle 2)
        composite_script_score = round((0.4 * rec + 0.3 * read + 0.3 * bridge) * 100, 1)

        current_mode = profile.bridge_mode_level or "intermediate"

        if composite_script_score < (self.INTERMEDIATE_THRESHOLD * 100):
            recommended_mode = "beginner"
            message = "Focus on Roman script while building your spoken confidence. Devanagari recognition is emerging."
            action_label = "Stay in Roman Mode"
            ready_to_advance = False
        elif composite_script_score < (self.ADVANCED_THRESHOLD * 100):
            recommended_mode = "intermediate"
            message = f"Great progress! You've achieved {composite_script_score}% script recognition. Bridge Mode (Roman + Devanagari) will help you naturally absorb letter shapes."
            action_label = "Switch to Bridge Mode"
            ready_to_advance = current_mode == "beginner"
        else:
            recommended_mode = "advanced"
            message = f"Mastery unlocked! Your script score is {composite_script_score}%. You are ready to read directly in Devanagari."
            action_label = "Switch to Devanagari Mode"
            ready_to_advance = current_mode != "advanced"

        return {
            "current_mode": current_mode,
            "recommended_mode": recommended_mode,
            "composite_script_score": composite_script_score,
            "ready_to_advance": ready_to_advance,
            "recommendation_message": message,
            "action_label": action_label,
            "script_breakdown": {
                "recognition": int(rec * 100),
                "reading": int(read * 100),
                "bridge_transliteration": int(bridge * 100)
            }
        }

    def get_milestones_roadmap(self, db: Session, user_id: int = 1) -> List[Dict[str, Any]]:
        """
        Returns full Level 0 through Level 5 milestones with user completion status.
        """
        milestones = db.query(Milestone).order_by(Milestone.level).all()
        user_progress = db.query(Progress).filter(Progress.user_id == user_id).first()
        active_id = user_progress.milestone_id if user_progress else 3
        active_completed = user_progress.completed_exercises if user_progress else 7

        roadmap = []
        for m in milestones:
            if m.id < active_id:
                status = "completed"
                completed = m.total_exercises
            elif m.id == active_id:
                status = "in_progress"
                completed = min(active_completed, m.total_exercises)
            else:
                status = "locked"
                completed = 0

            pct = int((completed / max(1, m.total_exercises)) * 100)

            roadmap.append({
                "id": m.id,
                "level": f"Level {m.level}",
                "level_number": m.level,
                "title": m.title,
                "description": m.description,
                "total_exercises": m.total_exercises,
                "completed_exercises": completed,
                "progress_percentage": pct,
                "status": status,
                "is_active": m.id == active_id
            })

        return roadmap

    def update_bridge_mode(self, db: Session, user_id: int, new_mode: str) -> Dict[str, Any]:
        """Allows learner to manually or automatically update their Bridge Mode level."""
        profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == user_id).first()
        if not profile:
            return {"status": "error", "message": "Profile not found"}

        clean_mode = new_mode.lower().strip()
        if clean_mode not in ["beginner", "intermediate", "advanced"]:
            clean_mode = "intermediate"

        profile.bridge_mode_level = clean_mode
        db.commit()
        return {
            "status": "success",
            "updated_mode": clean_mode,
            "message": f"Bridge mode updated to {clean_mode.capitalize()}."
        }

script_progression_engine = ScriptProgressionEngine()
