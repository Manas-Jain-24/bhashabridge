import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.translation.contextual import (
    ContextualCandidate, ContextualTranslator, protected_values, validate_candidate,
)
from app.services.translation import service
from app.services.explanation.llm_tutor import GeminiLinguisticTutor, llm_tutor


def candidate(**changes):
    return ContextualCandidate.model_validate({
        'source_native': 'मुझे बंगाली सीखनी है',
        'translation_native': 'আমি বাংলা শিখতে চাই।',
        'translation_roman': 'ami bangla shikhte chai.',
        'english_meaning': 'I want to learn Bengali.',
        'assessment': 'ambiguous', 'meaning_note': 'This can express a wish or an obligation.',
        'meaning_alternatives': [
            {'label': 'Want to learn', 'source_text': 'मैं बंगाली सीखना चाहता हूँ।'},
            {'label': 'Have to learn', 'source_text': 'मुझे बंगाली सीखनी होगी।'},
        ],
        'contrasts': [{'source_quote': 'सीखनी है', 'target_quote': 'শিখতে চাই',
                       'explanation': 'The target expresses a wish to learn.'}],
        **changes,
    })


def draft(**changes):
    return {'source_text': 'मुझे बंगाली सीखनी है', 'source_language': 'hindi', 'target_language': 'bengali',
            'translation': 'আমাকে বাংলা শিখতে হবে।', 'translation_native': 'আমাকে বাংলা শিখতে হবে।',
            'translation_roman': 'amake bangla shikhte hobe.', 'english_meaning': '',
            'model_source': 'indictrans2-320m-neural', **changes}


def fake_cloud(monkeypatch, value=None, error=None):
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(text=(value or candidate()).model_dump_json())
    monkeypatch.setattr(GeminiLinguisticTutor, 'is_available', property(lambda self: True))
    monkeypatch.setattr(llm_tutor, '_client', SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    return calls


def prepare_service(monkeypatch, answer=None):
    monkeypatch.setattr(service, 'lookup_reviewed', lambda *args: None)
    monkeypatch.setattr(service.indictrans2_adapter, 'translate', lambda **kwargs: draft())
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: (answer or candidate(), 'assisted'))


def test_raw_input_and_local_draft_reach_context_model_without_replacing_original(monkeypatch):
    calls = fake_cloud(monkeypatch)
    translator = ContextualTranslator()
    result, status = translator.refine('Mujhe bengali seekhni hai', 'मुझे बेंगली सीखनी है', 'hindi', 'bengali', draft())
    assert status == 'assisted' and result.translation_native == 'আমি বাংলা শিখতে চাই।'
    data = json.loads(calls[0]['contents'])
    assert data['original_input'] == 'Mujhe bengali seekhni hai'
    assert data['native_spelling_guess'] == 'मुझे बेंगली सीखनी है'
    assert data['local_translation_draft'] == 'আমাকে বাংলা শিখতে হবে।'
    assert calls[0]['config']['response_json_schema'] == ContextualCandidate.model_json_schema()


def test_both_routes_use_one_context_result_for_translation_and_explanation(client, monkeypatch):
    from app.api.routes import analyze
    prepare_service(monkeypatch)
    monkeypatch.setattr(analyze.explanation_engine, 'explain', lambda **kwargs: pytest.fail('Second explanation call'))
    body = {'text': 'Mujhe bengali seekhni hai', 'source_language': 'hindi', 'target_language': 'bengali',
            'translation_mode': 'hybrid'}
    analyzed = client.post('/api/analyze', json=body)
    direct = client.post('/api/translate', json=body)
    assert analyzed.status_code == direct.status_code == 200
    for result in (analyzed.json(), direct.json()):
        assert result['translation_native'] == 'আমি বাংলা শিখতে চাই।'
        assert result['context_status'] == 'assisted' and result['model_source'] == 'gemini-contextual'
        assert result['english_meaning_source'] == 'ai_generated'
        assert len(result['meaning_alternatives']) == 2
    assert direct.json()['source_text'] == body['text']
    assert analyzed.json()['native_text'] == 'मुझे बंगाली सीखनी है'
    assert analyzed.json()['grammar_explanation'][0]['source_pattern'] == 'सीखनी है'


def test_context_stage_is_not_specific_to_learning_phrases(monkeypatch):
    result = candidate(source_native='मैं कल घर नहीं जाऊँगा।', translation_native='আমি কাল বাড়ি যাব না।',
                       translation_roman='ami kal bari jabo na.', english_meaning='I will not go home tomorrow.',
                       assessment='corrected', meaning_note=None, meaning_alternatives=[], contrasts=[])
    prepare_service(monkeypatch, result)
    actual = service.translate_with_memory(None, 'Main kal ghar nahi jaunga', 'hindi', 'bengali')
    assert actual['translation_native'].endswith('যাব না।')
    assert actual['context_assessment'] == 'corrected'


@pytest.mark.parametrize('changes', [
    {'translation_native': 'मैं बंगाली सीखना चाहता हूँ।'},
    {'translation_roman': 'আমি বাংলা'},
    {'english_meaning': 'আমি বাংলা শিখতে চাই।'},
    {'meaning_alternatives': []},
    {'meaning_note': None},
    {'translation_native': 'আমি 7টি বই চাই।'},
])
def test_invalid_cloud_output_cannot_replace_the_local_draft(changes):
    with pytest.raises((ValueError, HTTPException)):
        validate_candidate(candidate(**changes), 'Mujhe bengali seekhni hai', 'hindi', 'bengali')


def test_contrasts_must_quote_the_actual_source_and_target():
    result = candidate(contrasts=[{'source_quote': 'चाहिए', 'target_quote': 'চাই',
                                  'explanation': 'An invented source word.'}])
    assert validate_candidate(result, 'Mujhe bengali seekhni hai', 'hindi', 'bengali').contrasts == []


def test_protected_tokens_preserve_case_and_indic_numeral_equivalence():
    assert protected_values('৭ https://example.org/Team @User') == protected_values('7 https://example.org/Team @User')
    assert protected_values('7 https://example.org/Team') != protected_values('7 https://example.org/team')


@pytest.mark.parametrize('changed', ['मैं 8 किताबें चाहता हूँ।', 'मैं 7 किताबें चाहता हूँ। https://example.org/team'])
def test_identifiers_and_numbers_cannot_be_lost_or_changed(changed):
    value = candidate(source_native=changed)
    with pytest.raises(ValueError):
        validate_candidate(value, 'Main 7 kitabein chahta hoon https://example.org/Team', 'hindi', 'bengali')


def test_cloud_cache_is_copy_safe_and_keyed_by_original_case(monkeypatch):
    calls = fake_cloud(monkeypatch)
    translator = ContextualTranslator()
    first, _ = translator.refine('Mujhe bengali seekhni hai', 'मुझे बंगाली सीखनी है', 'hindi', 'bengali')
    first.meaning_alternatives.clear()
    second, _ = translator.refine('Mujhe bengali seekhni hai', 'मुझे बंगाली सीखनी है', 'hindi', 'bengali')
    assert len(second.meaning_alternatives) == 2 and len(calls) == 1
    translator.refine('mujhe bengali seekhni hai', 'मुझे बंगाली सीखनी है', 'hindi', 'bengali')
    assert len(calls) == 2


def test_provider_failure_is_bounded_and_has_a_cooldown(monkeypatch):
    calls = fake_cloud(monkeypatch, error=TimeoutError())
    translator = ContextualTranslator()
    assert translator.refine('text', 'पाठ', 'hindi', 'bengali') == (None, 'provider_error')
    assert translator.refine('text', 'पाठ', 'hindi', 'bengali') == (None, 'cooldown')
    assert len(calls) == 1


def test_rejected_response_does_not_disable_assistance_for_unrelated_inputs(monkeypatch):
    calls = fake_cloud(monkeypatch, value=candidate(source_native='wrong script'))
    translator = ContextualTranslator()
    for text in ('first input', 'different input'):
        assert translator.refine(text, 'पाठ', 'hindi', 'bengali') == (None, 'rejected')
    assert len(calls) == 2


def test_local_choice_does_not_call_cloud_translation(monkeypatch):
    prepare_service(monkeypatch)
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: pytest.fail('Cloud translation in local mode'))
    value = service.translate_with_memory(None, 'Mujhe bengali seekhni hai', 'hindi', 'bengali', translation_mode='local')
    assert value['context_status'] == 'local_only'
    assert value['translation_native'] == draft()['translation_native']
    assert value['source_text'] == 'Mujhe bengali seekhni hai'


@pytest.mark.parametrize('mode', ['local', 'hybrid'])
def test_translate_does_not_request_a_cloud_gloss_after_local_choice_or_context_failure(client, monkeypatch, mode):
    prepare_service(monkeypatch)
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: (None, 'unavailable'))
    monkeypatch.setattr(llm_tutor, 'english_gloss', lambda *args: pytest.fail('Unexpected second cloud call'))
    response = client.post('/api/translate', json={'text': 'Mujhe bengali seekhni hai',
                                                 'source_language': 'hindi', 'target_language': 'bengali',
                                                 'translation_mode': mode})
    assert response.status_code == 200
    assert response.json()['english_meaning_source'] == 'unavailable'


def test_unavailable_assistance_preserves_and_labels_the_local_output(monkeypatch):
    prepare_service(monkeypatch)
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: (None, 'unavailable'))
    value = service.translate_with_memory(None, 'Mujhe bengali seekhni hai', 'hindi', 'bengali')
    assert value['translation_native'] == draft()['translation_native']
    assert value['context_status'] == 'unavailable' and value['quality_note']
    assert value['model_source'] == 'indictrans2-320m-neural'
    assert value['_skip_tutor'] is True


def test_offline_hybrid_keeps_local_grammar_without_a_second_cloud_call(client, monkeypatch):
    prepare_service(monkeypatch)
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: (None, 'unavailable'))
    monkeypatch.setattr(llm_tutor, 'explain', lambda *args, **kwargs: pytest.fail('Cloud explanation after context failure'))
    response = client.post('/api/analyze', json={'text': 'Mujhe bengali seekhni hai',
                                               'source_language': 'hindi', 'target_language': 'bengali'})
    assert response.status_code == 200
    assert response.json()['explanation_source'] == 'unavailable'


def test_cloud_can_work_when_local_pair_is_unavailable_but_not_mask_programming_errors(monkeypatch):
    prepare_service(monkeypatch)
    def fail(**kwargs):
        raise HTTPException(503, 'Model unavailable')
    monkeypatch.setattr(service.indictrans2_adapter, 'translate', fail)
    value = service.translate_with_memory(None, 'text', 'hindi', 'bengali')
    assert value['local_model_source'] is None and value['fallback_used']
    monkeypatch.setattr(service.contextual_translator, 'refine', lambda *args: (None, 'unavailable'))
    with pytest.raises(HTTPException) as error:
        service.translate_with_memory(None, 'text', 'hindi', 'bengali')
    assert error.value.status_code == 503
    def bug(**kwargs):
        raise RuntimeError('Programming error')
    monkeypatch.setattr(service.indictrans2_adapter, 'translate', bug)
    with pytest.raises(RuntimeError):
        service.translate_with_memory(None, 'text', 'hindi', 'bengali')


def test_known_hindi_spelling_does_not_invoke_a_neural_guess(monkeypatch):
    from app.services.transliteration.service import NeuralTransliterationService
    translator = NeuralTransliterationService()
    monkeypatch.setattr(translator, '_ensure_neural_model_loaded', lambda: pytest.fail('Known word guessed'))
    assert translator.transliterate('Mujhe bengali seekhni hai', 'hindi') == 'मुझे बंगाली सीखनी है'


@pytest.mark.parametrize('text', ['घर', 'nahi'])
def test_shared_words_do_not_override_an_explicit_source_language(client, monkeypatch, text):
    from app.api.routes import analyze
    def translate(db, **kwargs):
        assert kwargs['source_language'] == 'hindi'
        return draft(target_language='marathi', translation_native='घर')
    monkeypatch.setattr(analyze, 'translate_with_memory', translate)
    response = client.post('/api/analyze', json={'text': text, 'source_language': 'hindi', 'target_language': 'marathi'})
    assert response.status_code == 200
    assert response.json()['detected_language'] == 'hindi'
