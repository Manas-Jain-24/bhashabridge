import json
from types import SimpleNamespace
import pytest
from app.services.explanation.llm_tutor import GeminiLinguisticTutor,EnglishGloss
from app.services.translation.english import with_english_meaning


def translation(**changes):
    return {'source_text':'मुझे घर जाना होगा।','source_language':'hindi','target_language':'bengali',
        'translation':'আমাকে বাড়ি যেতে হবে।','translation_native':'আমাকে বাড়ি যেতে হবে।',
        'translation_roman':'amake bari jete hobe','english_meaning':'','model_source':'indictrans2-320m-neural',**changes}


def test_reviewed_gloss_wins_and_cached_translation_is_not_mutated(monkeypatch):
    from app.services.translation.english import llm_tutor
    monkeypatch.setattr(llm_tutor,'english_gloss',lambda *a:pytest.fail('Reviewed gloss requested generation'))
    original=translation(english_meaning='I have to go home.',model_source='reviewed_database')
    result=with_english_meaning(original,{'english_meaning':'Different generated guess'})
    assert result['english_meaning']=='I have to go home.' and result['english_meaning_source']=='reviewed_database'
    assert 'english_meaning_source' not in original


def test_combined_tutor_gloss_does_not_make_another_request(monkeypatch):
    from app.services.translation.english import llm_tutor
    monkeypatch.setattr(llm_tutor,'english_gloss',lambda *a:pytest.fail('Duplicate Gemini request'))
    result=with_english_meaning(translation(),{'english_meaning':'I have to go home.','tutor_attempted':True})
    assert result['english_meaning']=='I have to go home.' and result['english_meaning_source']=='ai_generated'


@pytest.mark.parametrize('enrichment',[{}, {'english_meaning':None}, {'english_meaning':{'wrong':'shape'}}])
def test_failed_tutor_attempt_is_not_retried_for_gloss(monkeypatch,enrichment):
    from app.services.translation.english import llm_tutor
    monkeypatch.setattr(llm_tutor,'english_gloss',lambda *a:pytest.fail('Failed tutor was retried'))
    result=with_english_meaning(translation(),{**enrichment,'tutor_attempted':True})
    assert result['english_meaning']=='' and result['english_meaning_source']=='unavailable'
    assert result['translation_native']=='আমাকে বাড়ি যেতে হবে।'


def test_standalone_gloss_receives_target_not_source(monkeypatch):
    from app.services.translation.english import llm_tutor
    calls=[]
    def gloss(text,language): calls.append((text,language)); return 'I have to go home.'
    monkeypatch.setattr(llm_tutor,'english_gloss',gloss)
    result=with_english_meaning(translation())
    assert calls==[('আমাকে বাড়ি যেতে হবে।','bengali')] and result['english_meaning_source']=='ai_generated'


@pytest.mark.parametrize('value',['', '   ', 'আমাকে বাড়ি যেতে হবে।','मुझे घर जाना है।'])
def test_non_english_or_blank_gloss_is_not_displayed(value):
    assert EnglishGloss(english_meaning=value).english_meaning is None


def test_tutor_combines_english_and_grammar_in_one_response(monkeypatch):
    tutor=GeminiLinguisticTutor(); calls=[]
    monkeypatch.setattr(GeminiLinguisticTutor,'is_available',property(lambda s:True))
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({'summary':'An obligation.','differences':[], 'english_meaning':'I have to go home.'}))
    tutor._client=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    result=tutor.explain('मुझे घर जाना होगा।','hindi','আমাকে বাড়ি যেতে হবে।','bengali')
    assert result['english_meaning']=='I have to go home.' and len(calls)==1


def test_standalone_gloss_failure_is_optional_and_one_attempt(monkeypatch):
    tutor=GeminiLinguisticTutor(); calls=[]
    monkeypatch.setattr(GeminiLinguisticTutor,'is_available',property(lambda s:True))
    def timeout(**kwargs): calls.append(kwargs); raise TimeoutError()
    tutor._client=SimpleNamespace(models=SimpleNamespace(generate_content=timeout))
    assert tutor.english_gloss('আমাকে বাড়ি যেতে হবে।','bengali') is None and len(calls)==1


def test_bengali_analysis_returns_generated_gloss(client,monkeypatch):
    from app.api.routes import analyze
    from app.services.explanation.llm_tutor import llm_tutor
    monkeypatch.setattr(analyze,'translate_with_memory',lambda *a,**k:translation())
    monkeypatch.setattr(llm_tutor,'explain',lambda *a,**k:{'summary':'Obligation','differences':[],'english_meaning':'I have to go home.'})
    response=client.post('/api/analyze',json={'text':'मुझे घर जाना होगा।','source_language':'hindi','target_language':'bengali'})
    assert response.status_code==200,response.text
    assert response.json()['english_meaning']=='I have to go home.' and response.json()['english_meaning_source']=='ai_generated'


def test_translate_endpoint_adds_gloss_without_changing_translation(client,monkeypatch):
    from app.api.routes import translate
    from app.services.translation.english import llm_tutor
    monkeypatch.setattr(translate,'translate_with_memory',lambda *a,**k:translation())
    monkeypatch.setattr(llm_tutor,'english_gloss',lambda *a:'I have to go home.')
    response=client.post('/api/translate',json={'text':'मुझे घर जाना होगा।','source_language':'hindi','target_language':'bengali'})
    assert response.status_code==200,response.text
    assert response.json()['translation_native']=='আমাকে বাড়ি যেতে হবে।' and response.json()['english_meaning']=='I have to go home.'
