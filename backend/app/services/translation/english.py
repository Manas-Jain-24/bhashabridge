"""Optional English glosses; never mutate model caches or reviewed memory."""
from app.services.explanation.llm_tutor import llm_tutor,EnglishGloss
from pydantic import ValidationError


def with_english_meaning(translation, explanation=None):
    result=dict(translation)
    existing=(result.get('english_meaning') or '').strip()
    if existing:
        result['english_meaning']=existing
        result['english_meaning_source']=('reviewed_database' if result.get('model_source')=='reviewed_database'
                                          else 'ai_generated' if result.get('model_source')=='gemini-contextual'
                                          else 'translation_engine')
        return result
    explanation=explanation or {}
    try:
        meaning=EnglishGloss(english_meaning=explanation.get('english_meaning')).english_meaning
    except ValidationError:
        meaning=None
    # The analysis tutor already had its one attempt; do not double its timeout.
    if not meaning and not explanation.get('tutor_attempted') and not result.get('_skip_tutor'):
        meaning=llm_tutor.english_gloss(result['translation_native'],result['target_language'])
    result['english_meaning']=meaning or ''
    result['english_meaning_source']='ai_generated' if meaning else 'unavailable'
    return result
