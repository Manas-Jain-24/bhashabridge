from typing import Optional
from pydantic import BaseModel, Field

class TransliterateRequest(BaseModel):
    text: str = Field(..., description="Text to transliterate")
    language: str = Field("marathi", description="marathi or hindi")
    direction: str = Field("latin_to_devanagari", description="latin_to_devanagari or devanagari_to_latin")

class TransliterateResponse(BaseModel):
    input: str
    output: str
    language: str
    direction: str
    detected_script: Optional[str] = None
