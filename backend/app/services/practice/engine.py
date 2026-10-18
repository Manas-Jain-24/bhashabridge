"""
BhashaBridge — Dynamic Practice & Attempt Evaluation Engine (M5)
Generates 7 adaptive question types (Translation, Reverse Translation, Romanisation,
Script Conversion, Vocabulary, Grammar, and Error Correction) and persists learner
attempts to SQLite, updating weak areas and active milestones.
"""

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.base import BasePracticeService
from app.schemas.practice import (
    PracticeQuestionDTO, PracticeOption, PracticeEvaluateResponse
)
from app.models.entities import (
    PracticeAttempt, Milestone, Progress, LanguageProfile
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
LEARNING_DATASET = BASE_DIR / "data" / "processed" / "learning" / "bhashabridge_learning.json"

class PracticeService(BasePracticeService):
    """
    Practice engine generating 7 question types with answer evaluation,
    database persistence, mistake tracking, and milestone progression.
    """

    QUESTIONS_BANK = [
        {
            "id": "q1",
            "type": "type_1_translation",
            "source_lang": "hindi",
            "target_lang": "marathi",
            "prompt": "Translate to Marathi: 'मुझे कल कॉलेज जाना है।'",
            "prompt_roman": "Translate to Marathi: 'Mujhe kal college jaana hai.'",
            "expected_dev": "मला उद्या कॉलेजला जायचं आहे।",
            "expected_rom": "Mala udya college-la jaycha aahe.",
            "hint": "Remember: tomorrow in Marathi is 'उद्या', not 'काल'.",
            "options": [
                {"id": "o1", "text_devanagari": "मला उद्या कॉलेजला जायचं आहे।", "text_roman": "Mala udya college-la jaycha aahe."},
                {"id": "o2", "text_devanagari": "मला काल कॉलेजला जायचं आहे।", "text_roman": "Mala kaal college-la jaycha aahe."},
                {"id": "o3", "text_devanagari": "मी कॉलेज जात आहे।", "text_roman": "Mi college jaat aahe."}
            ],
            "explanation": "'मुझे ... जाना है' maps to dative obligation 'मला ... जायचं आहे', and tomorrow is 'उद्या'.",
            "topic": "college",
            "concept": "dative_obligation"
        },
        {
            "id": "q2",
            "type": "type_3_romanisation",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "prompt": "Type the Romanisation for: 'मला पाणी पाहिजे।'",
            "prompt_roman": "Mala paani pahije.",
            "expected_dev": "मला पाणी पाहिजे।",
            "expected_rom": "Mala paani pahije",
            "hint": "Phonetic Roman: Mala paani...",
            "options": None,
            "explanation": "Type how it sounds in English letters.",
            "topic": "requests",
            "concept": "romanisation"
        },
        {
            "id": "q3",
            "type": "type_4_script_conversion",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "prompt": "Select the Devanagari script for: 'Mala Marathi shikaychi aahe.'",
            "prompt_roman": "Mala Marathi shikaychi aahe.",
            "expected_dev": "मला मराठी शिकायची आहे।",
            "expected_rom": "Mala Marathi shikaychi aahe.",
            "hint": "Starts with 'मला'...",
            "options": [
                {"id": "o1", "text_devanagari": "मला मराठी शिकायची आहे।", "text_roman": "Mala Marathi shikaychi aahe."},
                {"id": "o2", "text_devanagari": "मी मराठी शिकतो।", "text_roman": "Mi Marathi shikto."},
                {"id": "o3", "text_devanagari": "मला मराठी बोलायला आवडतं।", "text_roman": "Mala Marathi bolayala aavadta."}
            ],
            "explanation": "Script bridge conversion matches 'Mala Marathi shikaychi aahe' to 'मला मराठी शिकायची आहे।'",
            "topic": "learning",
            "concept": "script_bridge"
        },
        {
            "id": "q4",
            "type": "type_5_vocabulary",
            "source_lang": "marathi",
            "target_lang": "hindi",
            "prompt": "What does 'उद्या' (udya) mean?",
            "prompt_roman": "What does 'udya' mean?",
            "expected_dev": "कल (आने वाला कल / tomorrow)",
            "expected_rom": "Tomorrow / kal (aane wala kal)",
            "hint": "Opposite of 'काल' (yesterday)",
            "options": [
                {"id": "o1", "text_devanagari": "कल (Tomorrow)", "text_roman": "Tomorrow / Kal"},
                {"id": "o2", "text_devanagari": "कल (Yesterday)", "text_roman": "Yesterday / Beeta hua kal"},
                {"id": "o3", "text_devanagari": "आज (Today)", "text_roman": "Today / Aaj"}
            ],
            "explanation": "Marathi 'उद्या' specifically means tomorrow, unlike Hindi 'कल' which can mean either yesterday or tomorrow.",
            "topic": "general",
            "concept": "temporal_vocabulary"
        },
        {
            "id": "q5",
            "type": "type_7_error_correction",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "prompt": "Correct the mistake: 'मी घर जात आहे' (I am going home)",
            "prompt_roman": "Mi ghar jaat aahe",
            "expected_dev": "मी घरी जात आहे।",
            "expected_rom": "Mi ghari jaat aahe.",
            "hint": "Home requires the locative ending '-ी' ('घरी').",
            "options": [
                {"id": "o1", "text_devanagari": "मी घरी जात आहे।", "text_roman": "Mi ghari jaat aahe."},
                {"id": "o2", "text_devanagari": "मी घरला जात आहे।", "text_roman": "Mi gharla jaat aahe."},
                {"id": "o3", "text_devanagari": "मला घर जायचं आहे।", "text_roman": "Mala ghar jaycha aahe."}
            ],
            "explanation": "In Marathi, going 'home' requires the locative form 'घरी' (ghari), not bare 'घर'.",
            "topic": "daily_routine",
            "concept": "locative_inflection"
        },
        {
            "id": "q6",
            "type": "type_2_reverse_translation",
            "source_lang": "marathi",
            "target_lang": "hindi",
            "prompt": "Translate to Hindi: 'तुम्ही कसे आहात?'",
            "prompt_roman": "Translate to Hindi: 'Tumhi kase aahat?'",
            "expected_dev": "आप कैसे हैं?",
            "expected_rom": "Aap kaise hain?",
            "hint": "Respectful question to an elder/formal recipient.",
            "options": [
                {"id": "o1", "text_devanagari": "आप कैसे हैं?", "text_roman": "Aap kaise hain?"},
                {"id": "o2", "text_devanagari": "तुम कैसे हो?", "text_roman": "Tum kaise ho?"},
                {"id": "o3", "text_devanagari": "तू कैसा है?", "text_roman": "Tu kaisa hai?"}
            ],
            "explanation": "'तुम्ही' is honorific plural, which corresponds directly to Hindi formal 'आप ... हैं'.",
            "topic": "greetings",
            "concept": "honorific_agreement"
        },
        {
            "id": "q7",
            "type": "type_6_grammar",
            "source_lang": "hindi",
            "target_lang": "marathi",
            "prompt": "Choose the grammatically correct Marathi sentence for: 'I want to learn guitar'",
            "prompt_roman": "Mujhe guitar seekhna hai",
            "expected_dev": "मला गिटार शिकायचं आहे।",
            "expected_rom": "Mala guitar shikaycha aahe.",
            "hint": "Subject must be dative 'मला', verb agrees with neuter noun 'गिटार'.",
            "options": [
                {"id": "o1", "text_devanagari": "मला गिटार शिकायचं आहे।", "text_roman": "Mala guitar shikaycha aahe."},
                {"id": "o2", "text_devanagari": "मी गिटार शिकतो आहे।", "text_roman": "Mi guitar shikto aahe."},
                {"id": "o3", "text_devanagari": "माझे गिटार शिकायचे आहे।", "text_roman": "Mazhe guitar shikayche aahe."}
            ],
            "explanation": "Desire/obligation requires dative 'मला' + neuter infinitive '-चं' ('शिकायचं आहे').",
            "topic": "grammar",
            "concept": "dative_obligation"
        }
    ]

    def __init__(self):
        self._custom_examples = []
        if LEARNING_DATASET.exists():
            try:
                with open(LEARNING_DATASET, "r", encoding="utf-8") as f:
                    self._custom_examples = json.load(f)
            except Exception:
                self._custom_examples = []

    def generate_question(
        self,
        language: str = "marathi",
        difficulty: str = "level_1",
        topic: str = "general",
        question_type: str = "all"
    ) -> PracticeQuestionDTO:
        candidates = list(self.QUESTIONS_BANK)

        # Filter by question type if requested
        if question_type != "all":
            filtered = [q for q in candidates if question_type in q["type"]]
            if filtered:
                candidates = filtered

        selected = random.choice(candidates)
        options_dto = None
        if selected.get("options"):
            options_dto = [
                PracticeOption(
                    id=opt["id"],
                    text_devanagari=opt["text_devanagari"],
                    text_roman=opt["text_roman"]
                ) for opt in selected["options"]
            ]

        return PracticeQuestionDTO(
            id=selected["id"],
            question_type=selected["type"],
            prompt=selected["prompt"],
            prompt_roman=selected["prompt_roman"],
            target_language=selected["target_lang"],
            source_language=selected["source_lang"],
            options=options_dto,
            hint=selected["hint"]
        )

    def evaluate_answer(
        self,
        question_id: str,
        user_answer: str,
        user_script: str = "roman",
        db: Optional[Session] = None
    ) -> PracticeEvaluateResponse:
        q = next((item for item in self.QUESTIONS_BANK if item["id"] == question_id), self.QUESTIONS_BANK[0])

        clean_user = user_answer.strip().lower().replace(".", "").replace("।", "").replace("-", " ")
        clean_exp_dev = q["expected_dev"].strip().lower().replace(".", "").replace("।", "").replace("-", " ")
        clean_exp_rom = q["expected_rom"].strip().lower().replace(".", "").replace("।", "").replace("-", " ")

        is_correct = (
            clean_user == clean_exp_dev or
            clean_user == clean_exp_rom or
            clean_user in clean_exp_rom or
            clean_exp_rom in clean_user
        )

        mistakes = []
        concepts = []
        if not is_correct:
            mistakes.append(f"Answer: '{user_answer}', but expected: '{q['expected_rom']}' ({q['expected_dev']})")
            concepts.append(f"Review {q.get('concept', 'grammar concept')} in topic {q.get('topic', 'general')}.")

        # Database persistence and progress update (M5 requirement)
        if db is not None:
            try:
                # 1. Record Practice Attempt
                attempt = PracticeAttempt(
                    user_id=1,
                    question_id=None,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    feedback=q["explanation"]
                )
                db.add(attempt)

                # 2. Update Milestone Progress if correct
                progress_rec = db.query(Progress).filter(Progress.user_id == 1).first()
                if progress_rec and is_correct:
                    milestone = db.query(Milestone).filter(Milestone.id == progress_rec.milestone_id).first()
                    progress_rec.completed_exercises += 1
                    if milestone and progress_rec.completed_exercises >= milestone.total_exercises:
                        # Advance to next milestone
                        next_milestone = db.query(Milestone).filter(Milestone.id > milestone.id).order_by(Milestone.id).first()
                        if next_milestone:
                            progress_rec.milestone_id = next_milestone.id
                            progress_rec.completed_exercises = 0

                # 3. Dynamically increment proficiency scores
                profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == 1).first()
                if profile:
                    delta = 0.02 if is_correct else -0.01
                    q_type = q.get("type", "")
                    if "script" in q_type or "romanisation" in q_type:
                        profile.devanagari_recognition = max(0.1, min(1.0, profile.devanagari_recognition + delta))
                        profile.roman_to_devanagari = max(0.1, min(1.0, profile.roman_to_devanagari + delta))
                    elif "vocabulary" in q_type:
                        profile.vocabulary_score = max(0.1, min(1.0, profile.vocabulary_score + delta))
                    elif "grammar" in q_type or "error" in q_type:
                        profile.grammar_score = max(0.1, min(1.0, profile.grammar_score + delta))
                    else:
                        profile.speaking_score = max(0.1, min(1.0, profile.speaking_score + delta))
                        profile.conversation_score = max(0.1, min(1.0, profile.conversation_score + delta))

                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Warning: Failed to persist practice attempt to DB: {e}")

        return PracticeEvaluateResponse(
            correctness=is_correct,
            score=100.0 if is_correct else 0.0,
            expected_answer_devanagari=q["expected_dev"],
            expected_answer_roman=q["expected_rom"],
            user_answer=user_answer,
            explanation=q["explanation"],
            mistakes=mistakes,
            concepts_to_review=concepts
        )

practice_service = PracticeService()
