from app.services.translation.indictrans2 import IndicTrans2Adapter
from app.services.translation.memory import lookup_reviewed
from app.services.translation.corpus import normalize_source
from app.models.entities import ReviewedTranslation


def test_case_sensitive_urls_do_not_share_a_translation_cache_entry(monkeypatch):
    from app.services.translation.translator import modular_translator
    from app.services.transliteration.service import transliteration_service
    service=IndicTrans2Adapter(); calls=[]
    monkeypatch.setattr(service,'_lazy_load_model',lambda:False)
    monkeypatch.setattr(transliteration_service,'transliterate',lambda text,**kwargs:text)
    def translate(**kwargs):
        calls.append(kwargs['text'])
        return {'translation_native':kwargs['text'],'translation':kwargs['text'],'model_source':'fixture'}
    monkeypatch.setattr(modular_translator,'translate',translate)
    first='यह https://example.org/Team है।'; second='यह https://example.org/team है।'
    assert service.translate(first,'hindi','marathi')['translation_native']==first
    assert service.translate(second,'hindi','marathi')['translation_native']==second
    assert service.translate(first,'hindi','marathi')['translation_native']==first
    assert calls==[first,second]


def test_reviewed_memory_does_not_case_fold_url_paths(db_session):
    source='यह https://example.org/Team है।'
    db_session.add(ReviewedTranslation(source_language='hindi',target_language='marathi',source_key=normalize_source(source),
        source_text=source,target_text='हे https://example.org/Team आहे.',target_roman='fixture',provenance='test'))
    db_session.flush()
    assert lookup_reviewed(db_session,source,'hindi','marathi','native')
    assert lookup_reviewed(db_session,source.replace('/Team','/team'),'hindi','marathi','native') is None
