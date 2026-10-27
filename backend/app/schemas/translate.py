from typing import Optional, Literal
from pydantic import BaseModel, Field

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Source text to translate")
    source_language: Literal["hindi", "marathi"] = Field("hindi", description="hindi or marathi")
    target_language: Literal["marathi", "hindi"] = Field("marathi", description="marathi or hindi")
    script: Literal["both", "devanagari", "roman", "latin"] = Field("both", description="latin, devanagari, or both")

class TranslateResponse(BaseModel):
    source_text: str
    source_language: str
    target_language: str
    translation: str
    translation_native: str
    translation_roman: str
    english_meaning: str
    model_source: Optional[str] = None
    engine: Optional[str] = None
    fallback_used: Optional[bool] = False
