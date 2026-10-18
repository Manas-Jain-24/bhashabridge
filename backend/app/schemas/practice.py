from typing import List, Optional
from pydantic import BaseModel, Field

class PracticeGenerateRequest(BaseModel):
    language: str = Field("marathi", description="marathi or hindi")
    difficulty: str = Field("level_1", description="level_0 to level_5")
    topic: Optional[str] = Field("general", description="Topic like daily_life, food, college")
    question_type: Optional[str] = Field("all", description="Type 1 to 7 or all")

class PracticeOption(BaseModel):
    id: str
    text_devanagari: str
    text_roman: str

class PracticeQuestionDTO(BaseModel):
    id: str
    question_type: str
    prompt: str
    prompt_roman: Optional[str] = None
    target_language: str
    source_language: str
    options: Optional[List[PracticeOption]] = None
    hint: Optional[str] = None

class PracticeEvaluateRequest(BaseModel):
    question_id: str
    user_answer: str
    user_script: Optional[str] = "roman"  # roman, devanagari

class PracticeEvaluateResponse(BaseModel):
    correctness: bool
    score: float
    expected_answer_devanagari: str
    expected_answer_roman: str
    user_answer: str
    explanation: str
    mistakes: List[str] = []
    concepts_to_review: List[str] = []

class VocabularyReviewRequest(BaseModel):
    rating: str = Field("good", description="again, hard, good, or easy")

class PronunciationEvaluateRequest(BaseModel):
    spoken_text: str
    target_phrase: str

class PronunciationEvaluateResponse(BaseModel):
    accuracy_score: float
    spoken_text: str
    target_phrase: str
    matched_words: List[str] = []
    missing_words: List[str] = []
    feedback: str
    phonetic_stress_guide: str
    is_native_pass: bool
