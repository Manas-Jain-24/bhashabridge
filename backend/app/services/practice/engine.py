"""
BhashaBridge — Dynamic Practice & Attempt Evaluation Engine (M5)
Generates 7 adaptive question types (Translation, Reverse Translation, Romanisation,
Script Conversion, Vocabulary, Grammar, and Error Correction) and persists learner
attempts to SQLite, updating weak areas and active milestones.
"""

import json
import random
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.base import BasePracticeService
from app.services.activity import record_activity, now_utc
from app.schemas.practice import (
    PracticeQuestionDTO, PracticeOption, PracticeEvaluateResponse
)
from app.models.entities import (
    PracticeAttempt, PracticeQuestion, Milestone, Progress, LanguageProfile
)

BASE_DIR = Path(__file__).resolve().parents[4]
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
            "difficulty": "level_1",
            "topic": "college",
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
            "concept": "dative_obligation"
        },
        {
            "id": "q2",
            "type": "type_3_romanisation",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "difficulty": "level_1",
            "topic": "requests",
            "prompt": "Type the Romanisation for: 'मला पाणी पाहिजे।'",
            "prompt_roman": "Mala paani pahije.",
            "expected_dev": "मला पाणी पाहिजे।",
            "expected_rom": "Mala paani pahije",
            "hint": "Phonetic Roman: Mala paani...",
            "options": None,
            "explanation": "Type how it sounds in English letters.",
            "concept": "romanisation"
        },
        {
            "id": "q3",
            "type": "type_4_script_conversion",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "difficulty": "level_1",
            "topic": "learning",
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
            "concept": "script_bridge"
        },
        {
            "id": "q4",
            "type": "type_5_vocabulary",
            "source_lang": "marathi",
            "target_lang": "hindi",
            "difficulty": "level_1",
            "topic": "general",
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
            "concept": "temporal_vocabulary"
        },
        {
            "id": "q5",
            "type": "type_7_error_correction",
            "source_lang": "marathi",
            "target_lang": "marathi",
            "difficulty": "level_1",
            "topic": "daily_routine",
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
            "concept": "locative_inflection"
        },
        {
            "id": "q6",
            "type": "type_2_reverse_translation",
            "source_lang": "marathi",
            "target_lang": "hindi",
            "difficulty": "level_1",
            "topic": "greetings",
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
            "concept": "honorific_agreement"
        },
        {
            "id": "q7",
            "type": "type_6_grammar",
            "source_lang": "hindi",
            "target_lang": "marathi",
            "difficulty": "level_1",
            "topic": "grammar",
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
            "concept": "dative_obligation"
        },
        {
            "id": "q8",
            "type": "type_1_translation",
            "source_lang": "hindi",
            "target_lang": "marathi",
            "difficulty": "level_1",
            "topic": "general",
            "prompt": "Translate to Marathi: 'मुझे पानी चाहिए।'",
            "prompt_roman": "Translate to Marathi: 'Mujhe paani chahiye.'",
            "expected_dev": "मला पाणी पाहिजे।",
            "expected_rom": "Mala paani pahije.",
            "hint": "Hindi 'पानी चाहिए' maps to Marathi 'पाणी पाहिजे'.",
            "options": [
                {"id": "o1", "text_devanagari": "मला पाणी पाहिजे।", "text_roman": "Mala paani pahije."},
                {"id": "o2", "text_devanagari": "मला चहा पाहिजे।", "text_roman": "Mala chaha pahije."},
                {"id": "o3", "text_devanagari": "मी पाणी पितो।", "text_roman": "Mi paani pito."}
            ],
            "explanation": "'मुझे ... चाहिए' maps to 'मला ... पाहिजे'.",
            "concept": "requests_vocabulary"
        }
    ]

    def __init__(self):
        self.QUESTIONS_BANK = [dict(q, correct_option_id="o1") if q.get("options") else dict(q) for q in type(self).QUESTIONS_BANK]
        self._custom_examples = []
        if LEARNING_DATASET.exists():
            try:
                with open(LEARNING_DATASET, "r", encoding="utf-8") as f:
                    self._custom_examples = json.load(f)
            except Exception:
                self._custom_examples = []
        # Extend the curated bank so every roadmap level has enough distinct work.
        groups = [
            (0, "greetings", {"greetings", "introductions"}),
            (1, "requests", {"requests", "food", "feelings", "questions"}),
            (2, "college", {"college", "classroom", "daily_routine"}),
            (3, "conversation", {"shopping", "travel", "directions", "friends", "family", "common_informal_conversation", "politeness_formality"}),
            (4, "grammar", None),
            (5, "script", None),
        ]
        for level, topic, source_topics in groups:
            seen = set()
            for index, item in enumerate(self._custom_examples):
                if source_topics and item.get("topic") not in source_topics:
                    continue
                native = item.get("marathi_devanagari", "").strip()
                roman = item.get("marathi_roman", "").strip()
                source = item.get("hindi_devanagari", "").strip()
                if not native or not roman or not source or native in seen:
                    continue
                seen.add(native)
                script_question = level == 5
                self.QUESTIONS_BANK.append({
                    "id": f"q{1000 + level * 10000 + index}",
                    "type": "type_4_script_conversion" if script_question else ("type_6_grammar" if level == 4 else "type_1_translation"),
                    "source_lang": "marathi" if script_question else "hindi",
                    "target_lang": "marathi", "difficulty": f"level_{level}", "topic": topic,
                    "prompt": f"Write in Devanagari: {roman}" if script_question else f"Translate to Marathi: {source}",
                    "prompt_roman": roman if script_question else item.get("hindi_roman", ""),
                    "expected_dev": native, "expected_rom": roman,
                    "required_script": "devanagari" if script_question else None,
                    "hint": "Use Devanagari letters." if script_question else "Use the meaning of the complete sentence.",
                    "options": None, "explanation": item.get("explanation") or item.get("english_meaning") or "Compare your answer with the complete Marathi sentence.",
                    "concept": topic,
                })

    def generate_question(
        self,
        language: str = "marathi",
        difficulty: str = "level_1",
        topic: str = "general",
        question_type: str = "all",
        db: Optional[Session] = None
    ) -> Optional[PracticeQuestionDTO]:
        """
        Generates an adaptive practice question adhering strictly to requested filters.
        Returns None if no questions match the criteria, allowing route to raise 404.
        """
        candidates = list(self.QUESTIONS_BANK)

        # 1. Filter by language (either target or source matches requested language)
        if language and language != "all":
            candidates = [q for q in candidates if q.get("target_lang") == language or q.get("source_lang") == language]

        # 2. Filter by difficulty
        if difficulty and difficulty != "all":
            candidates = [q for q in candidates if q.get("difficulty") == difficulty]

        # 3. Filter by topic
        if topic and topic != "all":
            candidates = [q for q in candidates if q.get("topic") == topic]

        # 4. Filter by question type
        if question_type and question_type != "all":
            candidates = [q for q in candidates if question_type in q.get("type", "")]

        if db is not None:
            from app.models.entities import LearningActivity
            events = db.query(LearningActivity).filter(
                LearningActivity.user_id == 1, LearningActivity.kind == "practice",
                LearningActivity.created_at >= now_utc().replace(hour=0, minute=0, second=0, microsecond=0)).all()
            credited_ids = {event.event_key.split(":")[1] for event in events}
            candidates = [q for q in candidates if q["id"] not in credited_ids]

        if not candidates:
            return None

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
        db: Optional[Session] = None,
        selected_option_id: Optional[str] = None
    ) -> Optional[PracticeEvaluateResponse]:
        """
        Evaluates a learner's answer against the question bank with strict normalized equality.
        Partial matches receive documented partial score (< 100) and are marked incorrect.
        Stores real question IDs in PracticeAttempt table.
        """
        q = next((item for item in self.QUESTIONS_BANK if item["id"] == question_id), None)
        if not q:
            return None

        def normalize(text):
            return " ".join(unicodedata.normalize("NFC", text).strip().lower()
                            .replace(".", "").replace("।", "").replace("-", " ").split())
        clean_user = normalize(user_answer)
        clean_exp_dev = normalize(q["expected_dev"])
        clean_exp_rom = normalize(q["expected_rom"])
        accepted = {clean_exp_dev, clean_exp_rom}
        if q.get("required_script") == "devanagari":
            accepted = {clean_exp_dev}
        correct_option = next((o for o in q.get("options") or [] if o["id"] == q.get("correct_option_id")), None)
        if correct_option:
            accepted.update(normalize(correct_option[k]) for k in ("text_roman", "text_devanagari"))
        is_correct = (selected_option_id == q.get("correct_option_id")) if selected_option_id is not None else clean_user in accepted

        # Documented partial-credit behavior for incomplete answers
        is_partial = False
        score = 0.0
        if is_correct:
            score = 100.0
        else:
            if clean_user and (clean_user in clean_exp_rom or clean_exp_rom in clean_user or clean_user in clean_exp_dev):
                score = 40.0
                is_partial = True

        mistakes = []
        concepts = []
        if not is_correct:
            if is_partial:
                mistakes.append(f"Partial match: '{user_answer}', but complete expected answer is: '{q['expected_rom']}' ({q['expected_dev']})")
            else:
                mistakes.append(f"Answer: '{user_answer}', but expected: '{q['expected_rom']}' ({q['expected_dev']})")
            concepts.append(f"Review {q.get('concept', 'grammar concept')} in topic {q.get('topic', 'general')}.")

        # Database persistence and progress update (M5 requirement)
        if db is not None:
            try:
                # Store a real question ID in PracticeAttempt when possible
                numeric_id = None
                digits = "".join([c for c in str(question_id) if c.isdigit()])
                if digits:
                    numeric_id = int(digits)

                # Ensure question exists in practice_questions table so FK is satisfied
                if numeric_id is not None:
                    existing_q = db.query(PracticeQuestion).filter(PracticeQuestion.id == numeric_id).first()
                    if not existing_q:
                        db_q = PracticeQuestion(
                            id=numeric_id,
                            question_type=q.get("type", "general"),
                            prompt=q.get("prompt", ""),
                            source_language=q.get("source_lang", "hindi"),
                            target_language=q.get("target_lang", "marathi"),
                            expected_answer_devanagari=q.get("expected_dev", ""),
                            expected_answer_roman=q.get("expected_rom", ""),
                            explanation=q.get("explanation", ""),
                            difficulty=q.get("difficulty", "level_1"),
                            topic=q.get("topic", "general")
                        )
                        db.add(db_q)
                        db.flush()

                # 1. Record Practice Attempt with real question_id
                attempt = PracticeAttempt(
                    user_id=1,
                    question_id=numeric_id,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    feedback=q["explanation"]
                )
                db.add(attempt)

                # Reward and proficiency credit only once per question per UTC day.
                credited = is_correct and record_activity(
                    db, f"practice:{question_id}:{now_utc().date()}", "practice", 10)
                progress_rec = db.query(Progress).filter(Progress.user_id == 1).with_for_update().first()
                if progress_rec and credited and progress_rec.status != "completed":
                    milestone = db.query(Milestone).filter(Milestone.id == progress_rec.milestone_id).first()
                    matches = (milestone and q.get("topic") == milestone.required_topic
                               and q.get("difficulty") == f"level_{milestone.level}")
                    if matches:
                        progress_rec.completed_exercises = min(milestone.total_exercises, progress_rec.completed_exercises + 1)
                        progress_rec.updated_at = now_utc()
                        if progress_rec.completed_exercises >= milestone.total_exercises:
                            next_milestone = db.query(Milestone).filter(Milestone.level > milestone.level).order_by(Milestone.level).first()
                            if next_milestone:
                                progress_rec.milestone_id = next_milestone.id
                                progress_rec.completed_exercises = 0
                            else:
                                progress_rec.status = "completed"

                # 3. Dynamically increment proficiency scores
                profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == 1).first()
                if profile and (not is_correct or credited):
                    delta = 0.02 if is_correct else -0.01
                    q_type = q.get("type", "")
                    if "script" in q_type or "romanisation" in q_type:
                        profile.devanagari_recognition = max(0.0, min(1.0, profile.devanagari_recognition + delta))
                        profile.roman_to_devanagari = max(0.0, min(1.0, profile.roman_to_devanagari + delta))
                    elif "vocabulary" in q_type:
                        profile.vocabulary_score = max(0.0, min(1.0, profile.vocabulary_score + delta))
                    elif "grammar" in q_type or "error" in q_type:
                        profile.grammar_score = max(0.0, min(1.0, profile.grammar_score + delta))
                    else:
                        profile.speaking_score = max(0.0, min(1.0, profile.speaking_score + delta))
                        profile.conversation_score = max(0.0, min(1.0, profile.conversation_score + delta))

                db.commit()
            except Exception as e:
                db.rollback()
                raise

        return PracticeEvaluateResponse(
            correctness=is_correct,
            score=score,
            expected_answer_devanagari=q["expected_dev"],
            expected_answer_roman=q["expected_rom"],
            user_answer=user_answer,
            explanation=q["explanation"],
            mistakes=mistakes,
            concepts_to_review=concepts
        )

practice_service = PracticeService()
