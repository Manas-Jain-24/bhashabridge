"""Experimental Bengali bridge with common words, lexicon, and a validated word model.

Common conversational spellings are covered explicitly. Other Roman words use
our phonetic rules followed by Indic script mapping; results need user review.
"""
import re
import unicodedata
from app.services.transliteration.phonetic_rule_service import phonetic_transliterator

WORDS = {"ami": "আমি", "tumi": "তুমি", "apni": "আপনি", "amar": "আমার", "tomar": "তোমার", "bhalo": "ভালো", "bhalobashi": "ভালোবাসি", "achi": "আছি", "acho": "আছো", "achen": "আছেন", "kemon": "কেমন", "namaskar": "নমস্কার", "dhonnobad": "ধন্যবাদ", "bangla": "বাংলা", "shikhte": "শিখতে", "chai": "চাই", "jol": "জল", "pani": "পানি", "ki": "কি", "kothay": "কোথায়"}
REVERSE = {native: roman for roman, native in WORDS.items()}
WORDS.update({'amake':'আমাকে','hobe':'হবে'})
REVERSE.update({'আমাকে':'amake','হবে':'hobe'})

# These Devanagari sounds have no letter at the equivalent Bengali offset.
SCRIPT_EXCEPTIONS = {"व": "ব", "ळ": "ল", "ऴ": "ল", "ऱ": "র", "ऩ": "ন", "ऍ": "এ", "ऎ": "এ", "ऑ": "অ", "ऒ": "ও"}

def transliterate_bengali(text: str, direction: str, use_neural: bool = True) -> str:
    text = unicodedata.normalize("NFC", text)
    def convert(match):
        word = match.group()
        if direction == "latin_to_devanagari":
            if word.lower() in WORDS:
                return WORDS[word.lower()]
            from app.services.transliteration.lexicon import lookup
            attested = lookup(word, "bengali", direction)
            if attested: return attested
            if use_neural:
                from app.services.transliteration.bengali_neural import predict_word
                predicted=predict_word(word)
                if predicted: return predicted
            dev = phonetic_transliterator._latin_word_to_dev(word, lang="hindi")
            mapped = "".join(SCRIPT_EXCEPTIONS.get(c, chr(ord(c) + 128) if "\u0900" <= c <= "\u0963" else c) for c in dev)
            # Keep an unsupported Roman token readable rather than emit invalid Unicode.
            return word if any(unicodedata.category(c) == "Cn" for c in mapped) else mapped
        if word in REVERSE:
            return REVERSE[word]
        from app.services.transliteration.lexicon import lookup
        attested = lookup(word, "bengali", direction)
        if attested: return attested
        dev = "".join(chr(ord(c) - 128) if "\u0980" <= c <= "\u09e3" else c for c in word)
        return phonetic_transliterator._dev_word_to_latin(dev)
    pattern = r"[a-zA-Z]+" if direction == "latin_to_devanagari" else r"[\u0980-\u09ff]+"
    return re.sub(pattern, convert, text)
