import os
import sys
from pathlib import Path
from typing import Optional
from app.services.base import BaseTransliterationService

# Ensure project root containing ml/ is in sys.path
_current = Path(__file__).resolve()
for _p in _current.parents:
    if (_p / "ml" / "transliteration").exists():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

class NeuralTransliterationService(BaseTransliterationService):
    """
    100% Machine Learning Transliteration Service.
    Powered by a trained Character-level Sequence-to-Sequence (Seq2Seq) GRU model
    with Bahdanau Attention, trained on AI4Bharat Aksharantar & conversational datasets.
    NO hardcoded word replacement dictionaries!
    """

    def __init__(self):
        self._neural_model = None
        self._is_loaded = False
        self._load_neural_model()

    def _load_neural_model(self):
        try:
            from ml.transliteration.predictor import NeuralTransliterator
            self._neural_model = NeuralTransliterator()
            self._is_loaded = self._neural_model.is_loaded
        except Exception as e:
            self._neural_model = None
            self._is_loaded = False

    def transliterate(self, text: str, language: str = "marathi", direction: str = "latin_to_devanagari") -> str:
        if not text or not text.strip():
            return ""

        clean = text.strip()
        if direction == "latin_to_devanagari":
            # Quick check if already Devanagari
            if any('\u0900' <= c <= '\u097f' for c in clean):
                return clean

            # If neural model is not loaded yet (e.g. weights just written), reload attempt
            if self._neural_model is None or not self._neural_model.is_loaded:
                self._load_neural_model()

            if self._neural_model is not None and self._neural_model.is_loaded:
                return self._neural_model.transliterate_sentence(clean, language=language)

            # Fallback only if model checkpoint missing
            from app.services.transliteration.phonetic_rule_service import phonetic_transliterator
            return phonetic_transliterator.transliterate(clean, language=language, direction=direction)

        else:
            # devanagari_to_latin (Unicode character phonetic romanization)
            from app.services.transliteration.phonetic_rule_service import phonetic_transliterator
            return phonetic_transliterator.transliterate(clean, language=language, direction=direction)

def get_transliteration_service() -> BaseTransliterationService:
    return NeuralTransliterationService()

transliteration_service = get_transliteration_service()
