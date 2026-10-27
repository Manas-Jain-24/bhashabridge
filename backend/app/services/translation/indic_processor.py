"""Hindi/Marathi subset of IndicTrans2 text preparation for Windows installs.

The upstream IndicTransToolkit processor requires compiling a Cython extension.
This keeps the same language-tag, Indic normalization, tokenization, and
detokenization contract for the two Devanagari languages used by this app.
"""

from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
from indicnlp.tokenize import indic_tokenize, indic_detokenize
from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator


class HindiMarathiProcessor:
    CODES = {"hin_Deva": "hi", "mar_Deva": "mr"}

    def __init__(self, inference=True):
        self._normalizers = IndicNormalizerFactory()
        self._transliterator = UnicodeIndicTransliterator()

    def preprocess_batch(self, texts, src_lang, tgt_lang):
        if src_lang not in self.CODES or tgt_lang not in self.CODES:
            raise ValueError("Only Hindi and Marathi are supported")
        source = self.CODES[src_lang]
        normalizer = self._normalizers.get_normalizer(source)
        prepared = []
        for text in texts:
            normalized = normalizer.normalize(text.strip())
            tokens = indic_tokenize.trivial_tokenize(normalized, source)
            unified = self._transliterator.transliterate(" ".join(tokens), source, "hi")
            unified = unified.replace(" ् ", "्")
            prepared.append(f"{src_lang} {tgt_lang} {unified.strip()}")
        return prepared

    def postprocess_batch(self, texts, lang):
        if lang not in self.CODES:
            raise ValueError("Only Hindi and Marathi are supported")
        target = self.CODES[lang]
        results = []
        for text in texts:
            restored = self._transliterator.transliterate(text, "hi", target)
            results.append(indic_detokenize.trivial_detokenize(restored, target))
        return results
