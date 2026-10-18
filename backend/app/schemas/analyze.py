from typing import List, Optional
from pydantic import BaseModel, Field

class VocabularyItem(BaseModel):
    source_word: str
    target_word: str
    target_roman: Optional[str] = None
    meaning: str
    part_of_speech: Optional[str] = "noun"
    is_construction_based: bool = False
    morph_analysis: Optional[str] = None
    gender_contrast: Optional[str] = None
    root_lemma: Optional[str] = None

class GrammarPoint(BaseModel):
    title: str
    concept: str
    source_pattern: Optional[str] = None
    target_pattern: Optional[str] = None
    explanation: str

class ExampleItem(BaseModel):
    source_sentence: str
    target_sentence: str
    target_roman: str
    english_translation: str

class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Sentence or phrase to analyze")
    source_language: str = Field("auto", description="auto, hindi, or marathi")
    target_language: str = Field("marathi", description="marathi or hindi")
    preferred_script: str = Field("both", description="devanagari, roman, or both")

class AnalyzeResponse(BaseModel):
    detected_language: str
    detected_script: str
    normalized_text: str
    native_text: str
    roman_text: str
    translation: str
    translation_native: str
    translation_roman: str
    english_meaning: str
    vocabulary: List[VocabularyItem] = []
    grammar_explanation: List[GrammarPoint] = []
    differences: List[str] = []
    common_mistakes: List[str] = []
    examples: List[ExampleItem] = []
    model_source: Optional[str] = None
    explanation_source: Optional[str] = "local_rules"
    cultural_mnemonic: Optional[str] = None
