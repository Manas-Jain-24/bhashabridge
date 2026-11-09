"""Small compositional Hindi→Bengali learning constructions, with explicit ambiguity."""
import re
import unicodedata

# Language names are lexical items, not memorized whole-sentence translations.
LANGUAGES={
    'बंगाली':('বাংলা','bangla','Bengali'), 'बांग्ला':('বাংলা','bangla','Bengali'),
    'बेंगली':('বাংলা','bangla','Bengali'),
    'हिंदी':('হিন্দি','hindi','Hindi'), 'हिन्दी':('হিন্দি','hindi','Hindi'),
    'मराठी':('মারাঠি','marathi','Marathi'),
    'अंग्रेजी':('ইংরেজি','ingreji','English'), 'अंग्रेज़ी':('ইংরেজি','ingreji','English'),
}
LANGUAGES={unicodedata.normalize('NFC',name):value for name,value in LANGUAGES.items()}
NOUN='(?P<language>'+ '|'.join(re.escape(word) for word in sorted(LANGUAGES,key=len,reverse=True))+')'
PATTERNS=[
    ('ambiguous',re.compile(r'मुझे '+NOUN+r' सीखनी है')),
    ('want',re.compile(r'मैं '+NOUN+r' सीखना चाह(?:ता|ती) (?:हूँ|हूं)')),
    ('want',re.compile(r'मुझे '+NOUN+r' सीखने की इच्छा है')),
    ('not_want',re.compile(r'मैं '+NOUN+r' (?:सीखना नहीं|नहीं सीखना) चाह(?:ता|ती) (?:हूँ|हूं)')),
    ('need',re.compile(r'मुझे '+NOUN+r' (?:सीखनी होगी|सीखना होगा|सीखनी पड़ेगी|सीखना पड़ेगा)')),
]


def translate_learning_phrase(text,source_language,target_language,script='both'):
    if (source_language,target_language)!=('hindi','bengali'): return None
    normalized=' '.join(unicodedata.normalize('NFC',text).split()).rstrip('।.!')
    # Do not reinterpret questions, past tense, extra clauses or ambiguous negation.
    for intent,pattern in PATTERNS:
        matched=pattern.fullmatch(normalized)
        if not matched: continue
        name=matched['language']; native,roman,english=LANGUAGES[name]
        if intent=='need':
            target=f'আমাকে {native} শিখতে হবে।'; latin=f'amake {roman} shikhte hobe.'
            meaning=f'I will have to learn {english}.'
        elif intent=='not_want':
            target=f'আমি {native} শিখতে চাই না।'; latin=f'ami {roman} shikhte chai na.'
            meaning=f'I do not want to learn {english}.'
        else:
            target=f'আমি {native} শিখতে চাই।'; latin=f'ami {roman} shikhte chai.'
            meaning=f'I want to learn {english}.'
        alternatives=[]; note=None
        if intent=='ambiguous':
            note='This Hindi wording can express a wish or an obligation. Showing the wish to learn; choose the other meaning if needed.'
            alternatives=[{'label':'I mean “I want to learn”','source_text':f'मुझे {name} सीखने की इच्छा है।'},
                          {'label':'I mean “I have to learn”','source_text':f'मुझे {name} सीखनी होगी।'}]
        return {'source_text':text,'source_language':source_language,'target_language':target_language,
                'translation':latin if script in ('roman','latin') else target,
                'translation_native':target,'translation_roman':latin,'english_meaning':meaning,
                'model_source':'learning_construction','engine':'learning_construction','fallback_used':False,
                'meaning_note':note,'meaning_alternatives':alternatives}
    return None


def explain_learning_phrase(source_text, source_language, target_text, target_language):
    """Explain only a supported construction whose target matches the selected intent."""
    result = translate_learning_phrase(source_text, source_language, target_language)
    if result is None or target_text.strip() != result['translation_native']:
        return None
    if target_text.endswith('হবে।'):
        detail = 'Bengali আমাকে ... শিখতে হবে expresses an obligation to learn.'
    elif target_text.endswith('চাই না।'):
        detail = 'Bengali আমি ... শিখতে চাই না expresses not wanting to learn; না preserves the negative meaning.'
    else:
        detail = 'Bengali আমি ... শিখতে চাই expresses a wish to learn: আমি means I, শিখতে means to learn, and চাই means want.'
    differences = [detail]
    if result['meaning_note']:
        differences.append(result['meaning_note'])
    return {
        'summary': result['english_meaning'],
        'word_explanations': [],
        'grammar_points': [{
            'title': 'Learning intent', 'concept': 'learning_intent',
            'source_pattern': source_text, 'target_pattern': target_text,
            'explanation': detail,
        }],
        'differences': differences,
        'common_mistakes': ['Use চাই for wanting and শিখতে হবে for an obligation to learn.'],
        'examples': [], 'explanation_source': 'local_rules',
        'english_meaning': result['english_meaning'], 'tutor_attempted': False,
    }
