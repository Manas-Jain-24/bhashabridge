"""Regression cases for explanations that were attached to unrelated text."""
import re

import pytest

from app.services.explanation.engine import HybridExplanationEngine
from app.services.explanation.bilingual_aligner import align_sentence_vocabulary


@pytest.fixture
def engine():
    instance = HybridExplanationEngine()
    instance._dataset_cache = [{
        'id': 'greeting', 'topic': 'greeting',
        'hindi_devanagari': 'नमस्ते।', 'marathi_devanagari': 'नमस्कार।',
        'hindi_roman': 'namaste.', 'marathi_roman': 'namaskar.',
        'english_meaning': 'Hello.', 'grammar_note': 'Greeting pair only.',
        'vocabulary': [{'hindi': 'नमस्ते', 'marathi': 'नमस्कार', 'meaning': 'hello'}],
    }]
    instance._external_cache = []
    return instance


@pytest.mark.parametrize('source, target, source_lang, target_lang', [
    ('नमस्ते।', 'नमस्कार।', 'hindi', 'marathi'),
    ('नमस्कार।', 'नमस्ते।', 'marathi', 'hindi'),
])
def test_dataset_vocabulary_and_examples_follow_requested_direction(engine, source, target, source_lang, target_lang):
    result = engine.explain(source, source_lang, target, target_lang, use_tutor=False)
    word = result['word_explanations'][0]
    assert word['source_word'] == source.strip('।')
    assert word['target_word'] == target.strip('।')
    assert word['target_roman'] != word['meaning']
    assert re.search('[a-zA-Z]', word['target_roman'])
    point = result['grammar_points'][0]
    assert point['source_pattern'] == source
    assert point['target_pattern'] == target
    assert result['examples'][0]['source_sentence'] == source
    assert result['examples'][0]['target_sentence'] == target


@pytest.mark.parametrize('source, target', [('नम', 'नमस्कार।'), ('नमस्ते।', 'मला पाणी पाहिजे।')])
def test_dataset_notes_require_the_complete_source_and_target_pair(engine, source, target):
    result = engine.explain(source, 'hindi', target, 'marathi', use_tutor=False)
    assert all(note['explanation'] != 'Greeting pair only.' for note in result['grammar_points'])


def test_a_learning_trigger_does_not_invent_marathi_in_a_hindi_learning_sentence(engine):
    result = engine.explain('मुझे हिंदी सीखनी है।', 'hindi', 'मला हिंदी शिकायची आहे।',
                            'marathi', use_tutor=False)
    assert all(word['source_word'] != 'मराठी' for word in result['word_explanations'])


def test_dynamic_alignment_keeps_indic_vowel_marks_and_romanizes_the_target(monkeypatch):
    from app.services.explanation import bilingual_aligner
    monkeypatch.setattr(bilingual_aligner, 'ALIGNMENT_LEXICON', [])
    words = align_sentence_vocabulary('अनजाना', 'अपरिचित', source_lang='hindi')
    assert len(words) == 1
    assert words[0].source_word == 'अनजाना'
    assert words[0].target_word == 'अपरिचित'
    assert re.search('[a-zA-Z]', words[0].target_roman)
    assert not re.search('[\u0900-\u097f]', words[0].target_roman)


def test_lexicon_requires_terms_on_their_own_language_side(monkeypatch):
    from app.services.explanation import bilingual_aligner
    monkeypatch.setattr(bilingual_aligner, 'ALIGNMENT_LEXICON', [
        {'hi': 'मुझे', 'mr': 'मला', 'mr_rom': 'mala', 'meaning': 'to me'},
    ])
    words = align_sentence_vocabulary('मुझे मला', 'अपरिचित', source_lang='hindi')
    assert not any(word.meaning == 'to me' for word in words)


@pytest.mark.parametrize('source, target, matched', [
    ('चाहिए।', 'पाहिजे।', True), ('चाहिए!', 'पाहिजे?', True),
    ('चाहिए', 'पाहिजेत', False),
])
def test_term_boundaries_distinguish_indic_marks_from_punctuation(monkeypatch, source, target, matched):
    from app.services.explanation import bilingual_aligner
    monkeypatch.setattr(bilingual_aligner, 'ALIGNMENT_LEXICON', [
        {'hi': 'चाहिए', 'mr': 'पाहिजे', 'mr_rom': 'pahije', 'meaning': 'need'},
    ])
    words = align_sentence_vocabulary(source, target, source_lang='hindi')
    assert any(word.meaning == 'need' for word in words) == matched
