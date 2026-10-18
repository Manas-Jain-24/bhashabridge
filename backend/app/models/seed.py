"""
BhashaBridge — Database Seeder & Initializer (M5)
Initializes default user, language profiles, milestones (Levels 0–5),
and populates the vocabulary bank from the educational corpus.
"""

import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.entities import (
    User, LanguageProfile, Milestone, Progress, VocabularyWord, PracticeQuestion,
    LearningExample, GrammarConcept, UserGamification
)

def _find_learning_dataset() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "learning" / "bhashabridge_learning.json",
        Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "learning" / "bhashabridge_learning.json",
        Path("data/processed/learning/bhashabridge_learning.json").resolve(),
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

LEARNING_DATASET = _find_learning_dataset()


DEFAULT_MILESTONES = [
    {
        "id": 1,
        "level": 0,
        "title": "Level 0 — Survival Marathi & Greetings",
        "description": "Greetings, introductions, yes/no responses, and numbers.",
        "total_exercises": 10,
        "required_topic": "greetings"
    },
    {
        "id": 2,
        "level": 1,
        "title": "Level 1 — Basic Sentences & Requests",
        "description": "I want, I need, where is, what is, everyday requests.",
        "total_exercises": 10,
        "required_topic": "requests"
    },
    {
        "id": 3,
        "level": 2,
        "title": "Level 2 — College & Daily Life Sentences",
        "description": "Campus lectures, travel, food, friends, and daily routine.",
        "total_exercises": 10,
        "required_topic": "college"
    },
    {
        "id": 4,
        "level": 3,
        "title": "Level 3 — Scenario-Based Conversations",
        "description": "Restaurant ordering, street market bargaining, railway station navigation.",
        "total_exercises": 12,
        "required_topic": "conversation"
    },
    {
        "id": 5,
        "level": 4,
        "title": "Level 4 — Grammar & Postposition Mastery",
        "description": "Tenses, dative case (-ला), neuter gender agreement, modal forms.",
        "total_exercises": 15,
        "required_topic": "grammar"
    },
    {
        "id": 6,
        "level": 5,
        "title": "Level 5 — Script Mastery (Devanagari Transition)",
        "description": "Gradual Roman to mixed to pure Devanagari reading and writing.",
        "total_exercises": 20,
        "required_topic": "script"
    }
]

def seed_database(db: Session):
    # 1. Ensure Default User exists
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(id=1, username="learner")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Ensure Language Profile exists
    profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == 1).first()
    if not profile:
        profile = LanguageProfile(
            user_id=1,
            native_language="hindi",
            target_language="marathi",
            preferred_script="both",
            bridge_mode_level="intermediate",
            speaking_score=0.75,
            vocabulary_score=0.60,
            grammar_score=0.50,
            reading_score=0.40,
            conversation_score=0.55,
            devanagari_recognition=0.30,
            devanagari_reading=0.20,
            devanagari_writing=0.15,
            roman_to_devanagari=0.35,
            devanagari_to_roman=0.50
        )
        db.add(profile)
        db.commit()

    # 3. Ensure Milestones exist
    for m in DEFAULT_MILESTONES:
        existing = db.query(Milestone).filter(Milestone.id == m["id"]).first()
        if not existing:
            milestone = Milestone(
                id=m["id"],
                level=m["level"],
                title=m["title"],
                description=m["description"],
                total_exercises=m["total_exercises"],
                required_topic=m["required_topic"]
            )
            db.add(milestone)
    db.commit()

    # 4. Ensure Progress record exists
    progress_rec = db.query(Progress).filter(Progress.user_id == 1).first()
    if not progress_rec:
        progress_rec = Progress(
            user_id=1,
            milestone_id=3,  # Level 2 by default
            completed_exercises=7,
            status="in_progress"
        )
        db.add(progress_rec)
        db.commit()

    # 4b. Ensure User Gamification record exists
    gamification = db.query(UserGamification).filter(UserGamification.user_id == 1).first()
    if not gamification:
        gamification = UserGamification(
            user_id=1,
            xp=320,
            streak_days=5,
            hearts=3,
            max_hearts=3,
            rank_title="चहा मित्र (Chaha Mitra)",
            unlocked_badges_json=json.dumps(["first_step", "tapri_regular"], ensure_ascii=False),
            blitz_high_score=140,
            completed_scrambles=3,
            completed_scenarios_json=json.dumps(["fc_road_auto"], ensure_ascii=False)
        )
        db.add(gamification)
        db.commit()

    # 5. Populate Educational & Vocabulary Tables from dataset
    if LEARNING_DATASET.exists():
        try:
            with open(LEARNING_DATASET, "r", encoding="utf-8") as f:
                dataset = json.load(f)

            if db.query(VocabularyWord).count() == 0:
                seen_words = set()
                # 1. First add from 1500+ word lexicon if available
                vocab_1500_path = LEARNING_DATASET.parent / "marathi_hindi_vocab_1500.json"
                if vocab_1500_path.exists():
                    try:
                        with open(vocab_1500_path, "r", encoding="utf-8") as vf:
                            vocab_1500_data = json.load(vf)
                            for v in vocab_1500_data:
                                mr_word = v.get("marathi_devanagari", "").strip()
                                if mr_word and mr_word not in seen_words:
                                    seen_words.add(mr_word)
                                    word_entry = VocabularyWord(
                                        language="marathi",
                                        devanagari=mr_word,
                                        roman=v.get("marathi_roman", mr_word),
                                        english_meaning=v.get("english_meaning", "Meaning"),
                                        topic=v.get("topic", "general"),
                                        difficulty="beginner",
                                        notes=f"{v.get('gender_info', '')} | {v.get('bridge_note', '')}"
                                    )
                                    db.add(word_entry)
                    except Exception as e:
                        print(f"Warning: Failed to seed 1500 vocab lexicon: {e}")

                # 2. Add words from learning dataset
                for item in dataset:
                    for v in item.get("vocabulary", []):
                        mr_word = v.get("marathi", "").strip()
                        if mr_word and mr_word not in seen_words:
                            seen_words.add(mr_word)
                            word_entry = VocabularyWord(
                                language="marathi",
                                devanagari=mr_word,
                                roman=v.get("meaning", "").split()[0] if v.get("meaning") else mr_word,
                                english_meaning=v.get("meaning", "Meaning"),
                                topic=item.get("topic", "general"),
                                difficulty=item.get("difficulty", "beginner")
                            )
                            db.add(word_entry)
                db.commit()


            # Seed Learning Examples
            if db.query(LearningExample).count() == 0:
                for item in dataset:
                    example_entry = LearningExample(
                        hindi_devanagari=item.get("hindi_devanagari", ""),
                        hindi_roman=item.get("hindi_roman", ""),
                        marathi_devanagari=item.get("marathi_devanagari", ""),
                        marathi_roman=item.get("marathi_roman", ""),
                        english_meaning=item.get("english_meaning", ""),
                        topic=item.get("topic", "daily_life"),
                        difficulty=item.get("difficulty", "level_1"),
                        formality=item.get("formality", "informal"),
                        vocabulary_json=json.dumps(item.get("vocabulary", []), ensure_ascii=False),
                        grammar_concepts_json=json.dumps([item.get("grammar_note")] if item.get("grammar_note") else [], ensure_ascii=False),
                        explanation=item.get("context_note", "") or item.get("grammar_note", "")
                    )
                    db.add(example_entry)
                db.commit()

            # Seed Grammar Concepts from dataset topics and grammar notes
            if db.query(GrammarConcept).count() == 0:
                seen_topics = set()
                for item in dataset:
                    topic = item.get("topic", "general").strip()
                    note = item.get("grammar_note", "").strip()
                    mistakes = item.get("common_mistakes", [])
                    mistake_str = "; ".join(mistakes) if isinstance(mistakes, list) else str(mistakes)
                    if topic and note and topic not in seen_topics:
                        seen_topics.add(topic)
                        title = topic.replace("_", " ").title() + " Grammar & Structure"
                        slug = topic.lower().replace(" ", "_")
                        concept = GrammarConcept(
                            title=title,
                            slug=slug,
                            language="marathi",
                            source_construction="Hindi syntax / usage",
                            target_construction="Marathi marker / construction",
                            explanation=note,
                            common_mistake=mistake_str if mistake_str else None,
                            difficulty=item.get("difficulty", "beginner")
                        )
                        db.add(concept)
                db.commit()
        except Exception as e:
            print(f"Warning: Failed to seed dataset: {e}")
            db.rollback()

