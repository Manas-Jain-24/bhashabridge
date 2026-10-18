from pydantic import BaseModel, Field

class TranslateRequest(BaseModel):
    text: str = Field(..., description="Source text to translate")
    source_language: str = Field("hindi", description="hindi or marathi")
    target_language: str = Field("marathi", description="marathi or hindi")
    script: str = Field("both", description="latin, devanagari, or both")

class TranslateResponse(BaseModel):
    source_text: str
    source_language: str
    target_language: str
    translation: str
    translation_native: str
    translation_roman: str
    english_meaning: str
