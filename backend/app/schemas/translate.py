from app.core.languages import InputText
from app.core.languages import Language, AutoLanguage
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, model_validator

EnglishMeaningSource = Literal['reviewed_database','translation_engine','ai_generated','unavailable']

class MeaningAlternative(BaseModel):
    label: str
    source_text: str

class TranslateRequest(BaseModel):
    text: InputText = Field(..., min_length=1, max_length=2000, description="Source text to translate")
    source_language: Language = Field("hindi", description="Registered source language")
    target_language: Language = Field("marathi", description="Registered target language")
    script: Literal["both", "native", "devanagari", "roman", "latin"] = Field("both", description="latin, devanagari, or both")
    translation_mode: Optional[Literal['local', 'hybrid']] = None

    @model_validator(mode="after")
    def distinct_languages(self):
        if self.source_language == self.target_language:
            raise ValueError("Choose different source and target languages")
        return self

class TranslateResponse(BaseModel):
    source_text: str
    source_language: str
    target_language: str
    translation: str
    translation_native: str
    translation_roman: str
    english_meaning: str
    english_meaning_source: EnglishMeaningSource = 'unavailable'
    model_source: Optional[str] = None
    engine: Optional[str] = None
    fallback_used: Optional[bool] = False
    meaning_note: Optional[str] = None
    meaning_alternatives: List[MeaningAlternative] = Field(default_factory=list)
    source_native: Optional[str] = None
    context_status: Optional[Literal['reviewed', 'assisted', 'unavailable', 'local_only']] = None
    context_assessment: Optional[Literal['equivalent', 'corrected', 'ambiguous']] = None
    context_issue: Optional[str] = None
    quality_note: Optional[str] = None
    local_model_source: Optional[str] = None
