from typing import Optional, Literal
from pydantic import BaseModel, Field

class TransliterateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to transliterate")
    language: Literal["marathi", "hindi"] = Field("marathi", description="marathi or hindi")
    direction: Literal["latin_to_devanagari", "devanagari_to_latin"] = Field("latin_to_devanagari", description="latin_to_devanagari or devanagari_to_latin")

class TransliterateResponse(BaseModel):
    input: str
    output: str
    language: str
    direction: str
    detected_script: Optional[str] = None
