from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

class PracticeGenerateRequest(BaseModel):
    language: Literal["marathi", "hindi"] = Field("marathi", description="marathi or hindi")
    difficulty: Literal["level_0", "level_1", "level_2", "level_3", "level_4", "level_5"] = Field("level_1", description="level_0 to level_5")
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
    question_id: str = Field(..., min_length=1, description="Question ID")
    user_answer: str = Field(..., min_length=1, description="Learner answer")
    user_script: Optional[Literal["roman", "devanagari"]] = "roman"
    selected_option_id: Optional[str] = None

    @field_validator("user_answer")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_answer cannot be empty or blank")
        return v

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
    rating: Literal["again", "hard", "good", "easy"] = Field("good", description="again, hard, good, or easy")

class PronunciationEvaluateRequest(BaseModel):
    spoken_text: str = Field(max_length=500)
    target_phrase: str = Field(min_length=1, max_length=500)

class PronunciationEvaluateResponse(BaseModel):
    xp_awarded: int = 0
    accuracy_score: float
    spoken_text: str
    target_phrase: str
    matched_words: List[str] = []
    missing_words: List[str] = []
    feedback: str
    phonetic_stress_guide: str
    is_native_pass: bool
