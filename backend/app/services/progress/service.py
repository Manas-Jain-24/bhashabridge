"""
BhashaBridge — Dynamic Progress Tracker & Milestone Engine (M5 & M6)
Strictly enforces Principle 2: Language Proficiency vs Script Mastery tracked independently.
Dynamically computes learner skill scores, active milestones, weak concepts,
and revision counts directly from SQLite persistence.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.services.base import BaseProgressService
from app.models.entities import LanguageProfile, Milestone, Progress, PracticeAttempt
from app.services.vocabulary.srs_service import srs_service
from app.services.progress.progression_engine import script_progression_engine
from app.schemas.progress import (
    ProgressResponse, SkillScore, MilestoneItem, ScriptRecommendationDTO
)

class ProgressTrackerService(BaseProgressService):
    """
    Computes real-time learner progress, independent language vs script proficiencies,
    and weak topics from database records.
    """

    def get_user_progress(self, user_id: int = 1, db: Optional[Session] = None) -> ProgressResponse:
        # Default baseline values if DB session not provided or user empty
        target_lang = "Marathi"
        overall_pct = 0
        speaking = 0
        vocab = 0
        grammar = 0
        reading = 0
        conv = 0
        rom_mr = 0
        dev_rec = 0
        dev_read = 0
        dev_write = 0
        rom_to_dev = 0
        milestone_title = "Level 0 — Survival Marathi & Greetings"
        milestone_lvl = "Level 0"
        milestone_id = 1
        completed = 0
        total = 10
        status = "in_progress"
        weak_areas = []
        due_count = 0
        bridge_level = "intermediate"
        script_rec_dto = None

        if db is not None:
            # 1. Fetch Profile
            profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == user_id).first()
            if profile:
                target_lang = profile.target_language.capitalize()
                speaking = int(profile.speaking_score * 100)
                vocab = int(profile.vocabulary_score * 100)
                grammar = int(profile.grammar_score * 100)
                reading = int(profile.reading_score * 100)
                conv = int(profile.conversation_score * 100)
                rom_mr = int(profile.devanagari_to_roman * 100)
                dev_rec = int(profile.devanagari_recognition * 100)
                dev_read = int(profile.devanagari_reading * 100)
                dev_write = int(profile.devanagari_writing * 100)
                rom_to_dev = int(profile.roman_to_devanagari * 100)
                # Keep this as the persisted API value rather than presentation text.
                # The frontend uses it as a BridgeLevel enum when restoring state.
                bridge_level = profile.bridge_mode_level or "intermediate"

                # Compute script recommendation
                rec_data = script_progression_engine.evaluate_script_progression(profile)
                script_rec_dto = ScriptRecommendationDTO(**rec_data)

            # 2. Fetch Active Milestone & Progress
            progress_rec = db.query(Progress).filter(Progress.user_id == user_id).first()
            if progress_rec:
                milestone = db.query(Milestone).filter(Milestone.id == progress_rec.milestone_id).first()
                if milestone:
                    milestone_title = milestone.title
                    milestone_lvl = f"Level {milestone.level}"
                    milestone_id = milestone.id
                    completed = progress_rec.completed_exercises
                    total = milestone.total_exercises
                    status = progress_rec.status

            # 3. Dynamic Weak Areas from recent failed attempts
            failed_attempts = db.query(PracticeAttempt).filter(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.is_correct == False
            ).order_by(PracticeAttempt.created_at.desc()).limit(5).all()

            if failed_attempts:
                detected_weak = []
                for fa in failed_attempts:
                    if fa.feedback and len(detected_weak) < 3:
                        cleaned = fa.feedback.split(".")[0]
                        if cleaned not in detected_weak:
                            detected_weak.append(cleaned)
                if detected_weak:
                    weak_areas = detected_weak

            # 4. Spaced Repetition Due Count
            due_count = srs_service.get_due_count(db)

            # Compute overall composite percentage
            overall_pct = int((speaking + vocab + grammar + dev_rec + (completed / max(1, total) * 100)) / 5)

        return ProgressResponse(
            target_language=target_lang,
            overall_percentage=overall_pct,
            language_skills=[
                SkillScore(name="Speaking / Expression", percentage=speaking, level="Proficient" if speaking >= 70 else "Learning"),
                SkillScore(name="Vocabulary", percentage=vocab, level="Intermediate" if vocab >= 50 else "Novice"),
                SkillScore(name="Grammar", percentage=grammar, level="Intermediate" if grammar >= 50 else "Novice"),
                SkillScore(name="Reading", percentage=reading, level="Basic" if reading >= 30 else "Novice"),
                SkillScore(name="Conversation", percentage=conv, level="Conversational" if conv >= 50 else "Basic"),
            ],
            script_skills=[
                SkillScore(name="Roman Marathi", percentage=rom_mr, level="Fluent" if rom_mr >= 75 else "Good"),
                SkillScore(name="Devanagari Recognition", percentage=dev_rec, level="Emerging" if dev_rec >= 30 else "Beginner"),
                SkillScore(name="Devanagari Reading", percentage=dev_read, level="Emerging" if dev_read >= 25 else "Beginner"),
                SkillScore(name="Devanagari Writing", percentage=dev_write, level="Novice" if dev_write >= 20 else "Beginner"),
                SkillScore(name="Roman → Devanagari Bridge", percentage=rom_to_dev, level="Bridging" if rom_to_dev >= 35 else "Learning"),
            ],
            current_milestone=MilestoneItem(
                id=milestone_id,
                title=milestone_title,
                level=milestone_lvl,
                completed_exercises=completed,
                total_exercises=total,
                status=status
            ),
            weak_areas=weak_areas,
            review_due_count=due_count,
            bridge_mode_level=bridge_level,
            script_recommendation=script_rec_dto
        )

progress_service = ProgressTrackerService()
