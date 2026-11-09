"""Registry-driven IndicTrans2 text preparation for Indic scripts on Windows.

The upstream IndicTransToolkit processor requires compiling a Cython extension.
This implements language tags, Indic normalization and a deterministic entity
roundtrip for the registered languages; it is not the complete upstream toolkit.
"""

from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from indicnlp.tokenize import indic_tokenize, indic_detokenize
from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
import re
import unicodedata


from app.core.languages import LANGUAGES
from app.services.text_entities import ENTITY_PATTERN


class EntityPreservationError(ValueError):
    pass


class IndicScriptProcessor:
    VERSION = 'windows-entities-v2'
    CODES = {spec["flores"]: spec["iso"] for spec in LANGUAGES.values()}
    ENTITY = ENTITY_PATTERN
    MARKER = re.compile(r'[<\[]\s*(?:id|आई\s*\.?\s*डी\.?|आयडी|आइडी)\s*(\d+)\s*[>\]]', re.IGNORECASE)

    def __init__(self, inference=True):
        self.inference = inference
        self._entity_maps = []
        self._normalizers = IndicNormalizerFactory()
        self._transliterator = UnicodeIndicTransliterator()

    @staticmethod
    def _normalize(text):
        text = text.translate(str.maketrans({'“':'"','”':'"','‘':"'",'’':"'",'–':'-','—':'-','\r':''}))
        return ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)

    def preprocess_batch(self, texts, src_lang, tgt_lang=None, is_target=False):
        if src_lang not in self.CODES or (not is_target and tgt_lang not in self.CODES):
            raise ValueError("Unsupported model language tag")
        source = self.CODES[src_lang]
        normalizer = self._normalizers.get_normalizer(source)
        prepared = []
        # Each call replaces pending state. A failed generation cannot leak maps
        # into the next request; the adapter holds its inference lock throughout.
        self._entity_maps = []
        for text in texts:
            text = self._normalize(text.strip())
            entities = {}
            reserved = {int(m.group(1)) for m in self.MARKER.finditer(text)}
            serial = 0
            def protect(match):
                nonlocal serial
                value = match.group(0)
                if match.lastgroup=='number' and len(re.sub(r'[ .:]', '', value))<4: return value
                serial += 1
                while serial in reserved: serial += 1
                # Sentence punctuation is not part of an URL.
                suffix = ''
                if match.lastgroup=='url':
                    value = value.rstrip('.,;!?।)')
                    suffix = match.group(0)[len(value):]
                entities[serial] = value
                return f'<ID{serial}>'+suffix
            if self.inference: text = self.ENTITY.sub(protect, text)
            self._entity_maps.append(entities)
            normalized = normalizer.normalize(text.strip())
            tokens = indic_tokenize.trivial_tokenize(normalized, source)
            unified = self._transliterator.transliterate(" ".join(tokens), source, "hi")
            unified = unified.replace(" ् ", "्")
            prepared.append(unified.strip() if is_target else f"{src_lang} {tgt_lang} {unified.strip()}")
        return prepared

    def postprocess_batch(self, texts, lang):
        if lang not in self.CODES:
            raise ValueError("Unsupported model language tag")
        target = self.CODES[lang]
        maps = self._entity_maps
        self._entity_maps = []
        if maps and len(maps)!=len(texts): raise ValueError('Entity map/output batch mismatch')
        results = []
        for index,text in enumerate(texts):
            entities = maps[index] if maps else {}
            # Canonicalize known vernacular marker variants before changing script.
            text = self.MARKER.sub(lambda m:f'<ID{int(m.group(1))}>' if int(m.group(1)) in entities else m.group(0),text)
            restored = self._transliterator.transliterate(text, "hi", target)
            restored = indic_detokenize.trivial_detokenize(restored, target)
            # One pass prevents a literal <IDn> from being restored a second time.
            restored = self.MARKER.sub(lambda m:entities.get(int(m.group(1)),m.group(0)),restored)
            if any(value not in restored for value in entities.values()):
                raise EntityPreservationError('Translation omitted a protected number, URL or identifier')
            results.append(restored)
        return results

# Compatibility for existing imports.
HindiMarathiProcessor = IndicScriptProcessor
