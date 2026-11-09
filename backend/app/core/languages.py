"""Shared language metadata and API validation. No implicit language defaults."""
import json
import unicodedata
from pathlib import Path
from typing import Annotated
from pydantic import AfterValidator, StringConstraints

LANGUAGES = json.loads((Path(__file__).resolve().parents[3] / "shared/languages.json").read_text(encoding="utf-8"))

def validate_language(value: str) -> str:
    if value not in LANGUAGES:
        raise ValueError("Unsupported language: " + value)
    return value

Language = Annotated[str, AfterValidator(validate_language)]
AutoLanguage = Annotated[str, AfterValidator(lambda value: value if value == "auto" else validate_language(value))]

def has_native(text: str, language: str) -> bool:
    spec = LANGUAGES[validate_language(language)]
    return any(spec["unicode_start"] <= ord(char) <= spec["unicode_end"] and unicodedata.category(char)[0] in "LM" for char in text)

def rule_pair(source: str, target: str) -> bool:
    return {source, target} == {"hindi", "marathi"}

InputText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]

def check_source_script(text: str, language: str):
    """Reject incompatible native scripts instead of translating under a wrong tag."""
    from fastapi import HTTPException
    expected = LANGUAGES[validate_language(language)]["script"]
    for other, spec in LANGUAGES.items():
        if spec["script"] != expected and has_native(text, other):
            raise HTTPException(422, f"The input script does not match {language}. Select the source language that matches your text.")
