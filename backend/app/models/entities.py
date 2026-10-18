import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("LanguageProfile", back_populates="user", cascade="all, delete-orphan")
    attempts = relationship("PracticeAttempt", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("LearningSession", back_populates="user", cascade="all, delete-orphan")


class LanguageProfile(Base):
    __tablename__ = "language_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    native_language = Column(String(50), default="hindi")  # hindi or marathi
    target_language = Column(String(50), default="marathi")  # marathi or hindi
    preferred_script = Column(String(50), default="both")  # roman, devanagari, both
    bridge_mode_level = Column(String(50), default="intermediate")  # beginner, intermediate, advanced

    # Separate Language Proficiency (Principle 2)
    speaking_score = Column(Float, default=0.7)
    vocabulary_score = Column(Float, default=0.6)
    grammar_score = Column(Float, default=0.5)
    reading_score = Column(Float, default=0.4)
    conversation_score = Column(Float, default=0.5)

    # Separate Script Proficiency (Principle 2)
    devanagari_recognition = Column(Float, default=0.3)
    devanagari_reading = Column(Float, default=0.25)
    devanagari_writing = Column(Float, default=0.2)
    roman_to_devanagari = Column(Float, default=0.35)
    devanagari_to_roman = Column(Float, default=0.5)

    user = relationship("User", back_populates="profiles")


class VocabularyWord(Base):
    __tablename__ = "vocabulary_words"

    id = Column(Integer, primary_key=True, index=True)
    language = Column(String(50), index=True)  # marathi, hindi
    devanagari = Column(String(100), nullable=False)
    roman = Column(String(100), nullable=False)
    english_meaning = Column(String(255), nullable=False)
    part_of_speech = Column(String(50), default="noun")
    difficulty = Column(String(50), default="beginner")
    topic = Column(String(100), default="general")
    notes = Column(Text, nullable=True)
    box_level = Column(Integer, default=1)
    repetition_count = Column(Integer, default=0)
    is_due_for_review = Column(Boolean, default=True)


class GrammarConcept(Base):
    __tablename__ = "grammar_concepts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    slug = Column(String(150), unique=True, index=True)
    language = Column(String(50), index=True)
    source_construction = Column(String(200), nullable=True)
    target_construction = Column(String(200), nullable=True)
    explanation = Column(Text, nullable=False)
    common_mistake = Column(Text, nullable=True)
    difficulty = Column(String(50), default="beginner")


class LearningExample(Base):
    __tablename__ = "learning_examples"

    id = Column(Integer, primary_key=True, index=True)
    hindi_devanagari = Column(String(500), nullable=False)
    hindi_roman = Column(String(500), nullable=False)
    marathi_devanagari = Column(String(500), nullable=False)
    marathi_roman = Column(String(500), nullable=False)
    english_meaning = Column(String(500), nullable=False)
    topic = Column(String(100), default="daily_life")
    difficulty = Column(String(50), default="level_1")
    formality = Column(String(50), default="informal")
    vocabulary_json = Column(Text, default="[]")
    grammar_concepts_json = Column(Text, default="[]")
    explanation = Column(Text, nullable=True)


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id = Column(Integer, primary_key=True, index=True)
    question_type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    prompt_script = Column(String(50), default="both")
    source_language = Column(String(50), default="hindi")
    target_language = Column(String(50), default="marathi")
    expected_answer_devanagari = Column(Text, nullable=False)
    expected_answer_roman = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    difficulty = Column(String(50), default="level_1")
    topic = Column(String(100), default="general")


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("practice_questions.id"), nullable=True)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="attempts")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(Integer, default=0)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    total_exercises = Column(Integer, default=10)
    required_topic = Column(String(100), default="basics")


class Progress(Base):
    __tablename__ = "progress_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=False)
    completed_exercises = Column(Integer, default=0)
    status = Column(String(50), default="in_progress")
    updated_at = Column(DateTime, default=datetime.utcnow)


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    actions_count = Column(Integer, default=0)

    user = relationship("User", back_populates="sessions")


class UserGamification(Base):
    __tablename__ = "user_gamification"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    xp = Column(Integer, default=280)
    streak_days = Column(Integer, default=5)
    hearts = Column(Integer, default=3)
    max_hearts = Column(Integer, default=3)
    rank_title = Column(String(100), default="चहा मित्र (Chaha Mitra)")
    unlocked_badges_json = Column(Text, default='["first_step"]')
    blitz_high_score = Column(Integer, default=140)
    completed_scrambles = Column(Integer, default=3)
    completed_scenarios_json = Column(Text, default='[]')
    updated_at = Column(DateTime, default=datetime.utcnow)
