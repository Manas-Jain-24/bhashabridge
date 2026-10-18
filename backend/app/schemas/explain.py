from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.analyze import VocabularyItem, GrammarPoint, ExampleItem

class ExplainRequest(BaseModel):
    source_text: str = Field(..., description="Source sentence")
    source_language: str = Field("hindi", description="hindi or marathi")
    target_text: str = Field(..., description="Target sentence")
    target_language: str = Field("marathi", description="marathi or hindi")

class ExplainResponse(BaseModel):
    summary: str
    word_explanations: List[VocabularyItem] = []
    grammar_points: List[GrammarPoint] = []
    differences: List[str] = []
    common_mistakes: List[str] = []
    examples: List[ExampleItem] = []
    explanation_source: Optional[str] = "local_rules"
    cultural_mnemonic: Optional[str] = None
