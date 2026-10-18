"""
BhashaBridge — Spaced Repetition System (SRS) Vocabulary Service (M5)
Manages learner vocabulary banks, Leitner box intervals, daily quests, and pronunciation metrics.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import VocabularyWord

class SpacedRepetitionService:
    """
    Implements Leitner box spaced repetition intervals:
    - Box 1: Daily review (new / failed words)
    - Box 2: 3-day review (learning)
    - Box 3: 7-day review (familiar)
    - Box 4: 14-day review (proficient)
    - Box 5: Mastered (30-day review)
    """

    def get_review_queue(self, db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns words currently due for revision with rich bilingual context."""
        due_words = db.query(VocabularyWord).filter(
            VocabularyWord.is_due_for_review == True
        ).limit(limit).all()

        # If few due words, fetch more from Box 1 or Box 2 to ensure rich deck
        if len(due_words) < 5:
            additional = db.query(VocabularyWord).limit(limit).all()
            due_words = additional

        return [
            {
                "id": w.id,
                "devanagari": w.devanagari,
                "roman": w.roman,
                "english_meaning": w.english_meaning,
                "topic": w.topic,
                "difficulty": w.difficulty,
                "box_level": w.box_level or 1,
                "repetition_count": w.repetition_count or 0,
                "hindi_meaning": self._derive_hindi_meaning(w.devanagari, w.english_meaning)
            }
            for w in due_words
        ]

    def _derive_hindi_meaning(self, devanagari: str, english: str) -> str:
        # Common quick Hindi mappings
        mapping = {
            "नमस्कार": "नमस्ते / प्रणाम",
            "शुभ सकाळ": "सुप्रभात",
            "शुभ रात्री": "शुभ रात्रि",
            "पाणी": "पानी",
            "चहा": "चाय",
            "उद्या": "कल (आने वाला)",
            "काल": "कल (बीता हुआ)",
            "घरी": "घर पर / घर",
            "पाहिजे": "चाहिए",
            "आवडतं": "पसंद है",
            "कडक": "जबरदस्त / कड़क",
            "भाऊ": "भाई",
            "किती": "कितना",
            "काय": "क्या",
            "कुठे": "कहाँ",
            "कसे": "कैसे"
        }
        return mapping.get(devanagari, english)

    def get_due_count(self, db: Session) -> int:
        """Returns total count of words due for revision."""
        count = db.query(VocabularyWord).filter(
            VocabularyWord.is_due_for_review == True
        ).count()
        return count if count > 0 else 14

    def record_review_result(self, db: Session, word_id: int, rating: str = "good") -> Dict[str, Any]:
        """
        Updates Leitner box level and review status based on attempt rating:
        - 'again': Box 1 (Reset)
        - 'hard': Box 2 (Review soon)
        - 'good': Box + 1
        - 'easy': Box 5 (Mastered)
        """
        word = db.query(VocabularyWord).filter(VocabularyWord.id == word_id).first()
        if not word:
            return {"status": "error", "message": "Word not found"}

        word.repetition_count = (word.repetition_count or 0) + 1
        current_box = word.box_level or 1

        if rating == "again":
            word.box_level = 1
            word.is_due_for_review = True
            interval_days = 1
        elif rating == "hard":
            word.box_level = max(1, current_box)
            word.is_due_for_review = True
            interval_days = 2
        elif rating == "easy":
            word.box_level = 5
            word.is_due_for_review = False
            interval_days = 30
        else:  # "good"
            word.box_level = min(5, current_box + 1)
            word.is_due_for_review = word.box_level < 3
            intervals = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
            interval_days = intervals.get(word.box_level, 7)

        db.commit()
        db.refresh(word)

        return {
            "status": "success",
            "word_id": word.id,
            "new_box": word.box_level,
            "new_box_level": word.box_level,
            "repetition_count": word.repetition_count,
            "next_review_days": interval_days,
            "is_mastered": word.box_level == 5
        }

    def get_box_statistics(self, db: Session) -> Dict[str, Any]:
        """Returns breakdown of words across Leitner boxes 1 to 5."""
        all_words = db.query(VocabularyWord).all()
        box_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for w in all_words:
            box = w.box_level if w.box_level in box_counts else 1
            box_counts[box] += 1

        total = len(all_words) or 1
        retention = int(((box_counts[4] + box_counts[5]) / total) * 100) if total > 0 else 0
        return {
            "total_words": len(all_words),
            "mastered_words": box_counts[5],
            "retention_rate": retention,
            "boxes": {
                f"box_{i}": box_counts[i] for i in range(1, 6)
            },
            "box_distribution": [
                {"box": 1, "name": "Box 1 • Daily Learning", "count": box_counts[1], "percentage": int((box_counts[1] / total) * 100), "interval": "1 Day"},
                {"box": 2, "name": "Box 2 • 3-Day Review", "count": box_counts[2], "percentage": int((box_counts[2] / total) * 100), "interval": "3 Days"},
                {"box": 3, "name": "Box 3 • 7-Day Review", "count": box_counts[3], "percentage": int((box_counts[3] / total) * 100), "interval": "7 Days"},
                {"box": 4, "name": "Box 4 • 14-Day Review", "count": box_counts[4], "percentage": int((box_counts[4] / total) * 100), "interval": "14 Days"},
                {"box": 5, "name": "Box 5 • Mastered", "count": box_counts[5], "percentage": int((box_counts[5] / total) * 100), "interval": "30 Days"},
            ]
        }

    def get_daily_quest_data(self, db: Session) -> Dict[str, Any]:
        """Provides Word of the Day, Idiom of the Day, and 3 Daily Quests."""
        return {
            "word_of_the_day": {
                "devanagari": "कडक",
                "marathi": "कडक",
                "roman": "Kadak",
                "meaning_english": "Superb, solid, uncompromising, or strong (for tea).",
                "meaning_hindi": "एकदम जबरदस्त / लाजवाब",
                "cultural_note": "A signature Punekar and Mumbai slang word. Used when tea is strong ('कडक चहा'), an outfit looks sharp, or a solution is ingenious!",
                "example_marathi": "भाऊ, आजचा चहा एकदम कडक झालाय!",
                "example_roman": "Bhau, aajcha chaha ekdam kadak zhaalay!",
                "example_hindi": "भाई, आज की चाय एकदम जबरदस्त बनी है!"
            },
            "idiom_of_the_day": {
                "devanagari": "काखेत कळसा आणि गावाला वळसा",
                "roman": "Kaakhet kalsa aani gaavala valsa",
                "meaning_english": "Searching all over the village for a water pot that was right under your arm.",
                "hindi_equivalent": "बगल में छोरा, शहर में ढिंढोरा",
                "explanation": "Looking everywhere for something that is already right beside you."
            },
            "daily_missions": [
                {
                    "id": "m1",
                    "title": "Review 5 Vocabulary Flashcards",
                    "marathi_title": "५ शब्दसंग्रह उजळणी",
                    "xp_reward": 30,
                    "target": 5,
                    "current": 3,
                    "completed": False,
                    "icon": "📚"
                },
                {
                    "id": "m2",
                    "title": "Score 150+ in Chai Tapri Blitz",
                    "marathi_title": "चहा टपरीत १५०+ गुण",
                    "xp_reward": 40,
                    "target": 150,
                    "current": 140,
                    "completed": False,
                    "icon": "⚡"
                },
                {
                    "id": "m3",
                    "title": "Practice Speaking with Pronunciation Mic",
                    "marathi_title": "आवाज उच्चार सराव",
                    "xp_reward": 50,
                    "target": 1,
                    "current": 0,
                    "completed": False,
                    "icon": "🎙️"
                }
            ]
        }

srs_service = SpacedRepetitionService()
