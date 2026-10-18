import os
from app.services.base import BaseTranslationService
from app.services.translation.indictrans2 import indictrans2_adapter
from app.services.translation.neural_transformer import neural_transformer_translator
from app.services.translation.translator import modular_translator

def get_translation_service() -> BaseTranslationService:
    """
    Returns the configured translation service instance.
    Defaults to IndicTrans2 (AI4Bharat IndicTrans2 state-of-the-art neural model).
    """
    engine_type = os.getenv("TRANSLATION_ENGINE", "indictrans2").lower()
    if engine_type == "indictrans2":
        return indictrans2_adapter
    elif engine_type == "modular":
        return modular_translator
    return neural_transformer_translator

translation_service = get_translation_service()
