import pytest
from app.services.translation.learning_phrases import translate_learning_phrase
from app.services.transliteration.service import NeuralTransliterationService


def test_known_hindi_words_are_not_overwritten_by_neural_guesses(monkeypatch):
    service=NeuralTransliterationService()
    monkeypatch.setattr(service,'_ensure_neural_model_loaded',lambda:pytest.fail('Known words should not invoke a guessed spelling'))
    assert service.transliterate('Mujhe bengali seekhni hai','hindi','latin_to_native')=='मुझे बंगाली सीखनी है'


def test_reported_ambiguous_phrase_defaults_to_wish_and_exposes_other_meaning():
    result=translate_learning_phrase('मुझे बंगाली सीखनी है।','hindi','bengali')
    assert result['translation_native']=='আমি বাংলা শিখতে চাই।'
    assert result['english_meaning']=='I want to learn Bengali.'
    assert result['translation_roman']=='ami bangla shikhte chai.'
    assert result['meaning_note'] and len(result['meaning_alternatives'])==2
    obligation=translate_learning_phrase(result['meaning_alternatives'][1]['source_text'],'hindi','bengali')
    assert obligation['translation_native']=='আমাকে বাংলা শিখতে হবে।'
    assert obligation['translation_roman']=='amake bangla shikhte hobe.'
    assert 'have to' in obligation['english_meaning']


@pytest.mark.parametrize('source',['मैं बंगाली सीखना चाहता हूँ।','मैं बंगाली सीखना चाहती हूं।','मुझे बंगाली सीखने की इच्छा है।'])
def test_explicit_desire_never_becomes_obligation(source):
    result=translate_learning_phrase(source,'hindi','bengali')
    assert result['translation_native']=='আমি বাংলা শিখতে চাই।'
    assert not result['meaning_note']


def test_explicit_negative_desire_is_preserved():
    result=translate_learning_phrase('मैं बंगाली सीखना नहीं चाहती हूँ।','hindi','bengali')
    assert result['translation_native']=='আমি বাংলা শিখতে চাই না।'
    assert result['english_meaning']=='I do not want to learn Bengali.'


@pytest.mark.parametrize('source',['मुझे बंगाली नहीं सीखनी है।','मुझे बंगाली सीखनी थी।',
                                 'मुझे बंगाली सीखनी है?','मुझे कल बंगाली सीखनी है।',
                                 'मुझे बंगाली सीखनी है और मुझे घर जाना है।','मुझे गणित सीखना है।'])
def test_unhandled_context_is_left_to_the_translation_engine(source):
    assert translate_learning_phrase(source,'hindi','bengali') is None


def test_language_names_are_composed_and_other_directions_are_unchanged():
    assert translate_learning_phrase('मुझे मराठी सीखनी है।','hindi','bengali')['translation_native']=='আমি মারাঠি শিখতে চাই।'
    assert translate_learning_phrase('मुझे बंगाली सीखनी है।','hindi','marathi') is None


@pytest.mark.parametrize('route,script_key',[('/api/analyze','preferred_script'),('/api/translate','script')])
def test_real_routes_preserve_learning_intent_without_neural_or_reviewed_overrides(client,route,script_key):
    response=client.post(route,json={'text':'Mujhe bengali seekhni hai','source_language':'hindi',
                                     'target_language':'bengali',script_key:'both'})
    assert response.status_code==200
    result=response.json()
    assert result['model_source']=='learning_construction'
    assert result['translation_native']=='আমি বাংলা শিখতে চাই।'
    assert result['english_meaning_source']=='translation_engine'
    assert len(result['meaning_alternatives'])==2
    if route.endswith('analyze'):
        assert result['native_text']=='मुझे बंगाली सीखनी है'
        assert result['explanation_source']=='local_rules'
        assert result['grammar_explanation'][0]['source_pattern']=='मुझे बंगाली सीखनी है'
    else:
        assert result['source_text']=='Mujhe bengali seekhni hai'


@pytest.mark.parametrize('source', ['मुझे बंगाली सीखनी है।', 'मुझे बंगाली सीखनी होगी।',
                                  'मैं बंगाली सीखना नहीं चाहती हूँ।'])
def test_explanation_matches_selected_intent_without_generated_grammar(monkeypatch, source):
    from app.services.explanation.engine import explanation_engine, llm_tutor
    monkeypatch.setattr(llm_tutor, 'explain', lambda *args, **kwargs: pytest.fail('Supported constructions use local explanations'))
    translation = translate_learning_phrase(source, 'hindi', 'bengali')
    result = explanation_engine.explain(source, 'hindi', translation['translation_native'], 'bengali')
    assert result['english_meaning'] == translation['english_meaning']
    assert result['grammar_points'][0]['source_pattern'] == source
    assert result['grammar_points'][0]['target_pattern'] == translation['translation_native']
    assert result['explanation_source'] == 'local_rules'


def test_construction_explanation_does_not_explain_a_different_target():
    from app.services.translation.learning_phrases import explain_learning_phrase
    assert explain_learning_phrase('मुझे बंगाली सीखनी है।', 'hindi', 'আমাকে বাংলা শিখতে হবে।', 'bengali') is None
