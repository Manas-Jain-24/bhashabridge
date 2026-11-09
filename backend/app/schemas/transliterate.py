from app.core.languages import InputText
from app.core.languages import Language, AutoLanguage
from typing import Optional, Literal
from pydantic import BaseModel, Field

class TransliterateRequest(BaseModel):
    text: InputText = Field(..., min_length=1, max_length=2000, description="Text to transliterate")
    language: Language = Field("marathi", description="Registered target language")
    direction: Literal["latin_to_native", "native_to_latin", "latin_to_devanagari", "devanagari_to_latin"] = Field("latin_to_devanagari", description="latin_to_devanagari or devanagari_to_latin")

class TransliterateResponse(BaseModel):
    input: str
    output: str
    language: str
    direction: str
    detected_script: Optional[str] = None
