from app.core.languages import rule_pair, check_source_script
from fastapi import HTTPException
import os
from app.core.config import settings
from app.services.base import BaseTranslationService
from app.services.translation.indictrans2 import indictrans2_adapter
from app.services.translation.neural_transformer import neural_transformer_translator
from app.services.translation.translator import modular_translator
from app.services.translation.memory import lookup_reviewed
from app.services.translation.contextual import contextual_translator, candidate_explanation
from app.services.transliteration.service import transliteration_service
from app.services.language_detection.detector import language_detector
from app.services.runtime import stage

def get_translation_service() -> BaseTranslationService:
    """
    Returns the configured translation service instance.
    Defaults to IndicTrans2 (AI4Bharat IndicTrans2 state-of-the-art neural model).
    """
    engine_type = settings.TRANSLATION_ENGINE
    if engine_type == "indictrans2":
        return indictrans2_adapter
    elif engine_type == "modular":
        return modular_translator
    return neural_transformer_translator

translation_service = get_translation_service()


def translate_with_memory(db, text: str, source_language: str, target_language: str,
                          script: str = "both", native_text=None, translation_mode=None):
    """Keep raw text available throughout normalization, local inference and assistance."""
    check_source_script(text, source_language)
    mode = translation_mode or settings.TRANSLATION_MODE
    if mode not in ('local', 'hybrid'):
        raise ValueError('Unsupported translation mode')
    with stage('memory'):
        reviewed = lookup_reviewed(db, text, source_language, target_language, script)
    if reviewed is not None:
        return {**reviewed, 'context_status': 'reviewed', '_skip_tutor': mode == 'local'}
    if native_text is None:
        normalized = ' '.join(text.split()) if source_language == 'bengali' else language_detector.normalize(text)
        with stage('transliteration'):
            native_text = transliteration_service.transliterate(normalized, language=source_language, direction='latin_to_native')
    engine = translation_service if rule_pair(source_language, target_language) else indictrans2_adapter
    draft = None
    local_error = None
    try:
        with stage('local_translation'):
            draft = engine.translate(text=native_text, source_language=source_language,
                                 target_language=target_language, script=script)
    except HTTPException as exc:
        if exc.status_code != 503 or mode == 'local':
            raise
        local_error = exc
    if mode == 'hybrid':
        with stage('context'):
            candidate, status = contextual_translator.refine(text, native_text, source_language, target_language, draft)
        if candidate is not None:
            return {
                'source_text': text, 'source_language': source_language, 'target_language': target_language,
                'source_native': candidate.source_native,
                'translation': candidate.translation_roman if script in ('roman', 'latin') else candidate.translation_native,
                'translation_native': candidate.translation_native, 'translation_roman': candidate.translation_roman,
                'english_meaning': candidate.english_meaning, 'english_meaning_source': 'ai_generated',
                'model_source': 'gemini-contextual', 'engine': 'gemini-contextual',
                'local_model_source': (draft or {}).get('model_source'),
                'fallback_used': draft is None, 'context_status': 'assisted',
                'context_assessment': candidate.assessment,
                'meaning_note': candidate.meaning_note,
                'meaning_alternatives': [choice.model_dump() for choice in candidate.meaning_alternatives],
                '_explanation': candidate_explanation(candidate),
            }
    else:
        status = 'local_only'
    issue = status if mode == 'hybrid' else None
    if mode == 'hybrid':
        status = 'unavailable'
    if draft is None:
        raise HTTPException(503, 'Local translation and Gemini assistance are unavailable. Retry later or check model setup.') from local_error
    note = ('Gemini assistance is unavailable. Showing the local translation without contextual interpretation.'
            if status == 'unavailable' else None)
    result = {**draft, 'source_text': text, 'source_native': native_text,
              'context_status': status, 'context_issue': issue, 'quality_note': note}
    if status in ('unavailable', 'local_only'):
        # A failed context call must not trigger another cloud call that merely
        # rationalizes the same local draft or doubles the timeout.
        result['_skip_tutor'] = True
    return result
