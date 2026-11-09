from app.core.languages import InputText
from app.core.languages import Language
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.analyze import VocabularyItem, GrammarPoint, ExampleItem

class ExplainRequest(BaseModel):
    source_text: InputText = Field(..., description="Source sentence")
    source_language: Language = Field("hindi", description="Registered source language")
    target_text: InputText = Field(..., description="Target sentence")
    target_language: Language = Field("marathi", description="Registered target language")

class ExplainResponse(BaseModel):
    summary: str
    english_meaning: Optional[str] = None
    word_explanations: List[VocabularyItem] = []
    grammar_points: List[GrammarPoint] = []
    differences: List[str] = []
    common_mistakes: List[str] = []
    examples: List[ExampleItem] = []
    explanation_source: Optional[str] = "local_rules"
    cultural_mnemonic: Optional[str] = None
