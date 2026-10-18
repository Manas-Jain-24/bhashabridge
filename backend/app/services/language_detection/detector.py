import re
from typing import Optional
from app.services.base import BaseLanguageDetector

class RuleBasedLanguageDetector(BaseLanguageDetector):
    """
    Lightweight rule and morphological marker detector for Hindi and Marathi
    in both Latin and Devanagari scripts. Easily swappable with IndicLID later.
    """

    DEVANAGARI_RANGE = re.compile(r'[\u0900-\u097F]')
    LATIN_RANGE = re.compile(r'[a-zA-Z]')

    # Distinctive Marathi lexical & affix cues (both scripts)
    MARATHI_CUES = {
        # Devanagari
        "आहे", "आहोत", "आहेत", "नाही", "मला", "तुला", "त्याला", "तिला", "आम्हाला",
        "जायचं", "शिकायची", "शिकायचं", "करायचं", "पाहिजे", "उद्या", "काल", "कसा",
        "कशी", "कसे", "कुठे", "कधी", "काय", "माझं", "तुझं", "माझा", "माझी", "माझे", "नाव", "नावं", "घर",
        "पाणी", "जेवण", "भाऊ", "बहीण", "करायला", "जायला", "गेलो", "गेली", "झाला",
        # Latin / Roman
        "aahe", "ahe", "ahet", "aahot", "nahi", "mala", "tula", "tyala", "tila", "aamhala",
        "mi", "tithe", "teethe", "ithe", "eethe",
        "jaycha", "shikaychi", "shikaycha", "karaycha", "pahije", "udya", "kasa",
        "kashi", "kase", "kuthe", "kadhi", "kay", "maza", "mazha", "mazhi", "mazhe", "tuzha",
        "naav", "nav", "karayala", "jayala", "gelo", "geli", "jhala", "paani"
    }

    # Distinctive Hindi lexical & affix cues (both scripts)
    HINDI_CUES = {
        # Devanagari
        "है", "हैं", "हूँ", "था", "थी", "थे", "मुझे", "तुझे", "उसे", "हमें",
        "मैं", "वहाँ", "यहाँ",
        "जाना", "सीखना", "सीखनी", "करना", "चाहिए", "कल", "कैसा", "कैसी", "कैसे",
        "कहाँ", "कब", "क्या", "मेरा", "मेरी", "मेरे", "तेरा", "तेरी", "पानी",
        "खाना", "गया", "गई", "गए", "रहा", "रही", "रहे", "सकता", "सकती", "सकते",
        # Latin / Roman
        "hai", "hain", "hoon", "hu", "mai", "main", "vaha", "waha", "vahan", "wahan", "yaha", "yahan",
        "tha", "thi", "the", "mujhe", "tujhe", "use", "hume",
        "jaana", "seekhna", "seekhni", "karna", "chahiye", "kaisa", "kaisi", "kaise",
        "kaha", "kahan", "kab", "kya", "mera", "meri", "mere", "tera", "teri",
        "gaya", "gayi", "raha", "rahi", "sakta", "sakti"
    }

    def detect_script(self, text: str) -> str:
        if not text or not text.strip():
            return "latin"

        clean = text.strip()
        devanagari_count = len(self.DEVANAGARI_RANGE.findall(clean))
        latin_count = len(self.LATIN_RANGE.findall(clean))

        if devanagari_count > 0 and latin_count > 0:
            # Check predominant script
            if devanagari_count > latin_count * 2:
                return "devanagari"
            elif latin_count > devanagari_count * 2:
                return "latin"
            return "mixed"
        elif devanagari_count > 0:
            return "devanagari"
        elif latin_count > 0:
            return "latin"
        return "latin"

    def detect_language(self, text: str, hint_script: Optional[str] = None) -> str:
        if not text or not text.strip():
            return "hindi"

        norm_words = [w.lower().strip(".,!?:;\"'()[]{}") for w in text.split()]
        marathi_hits = sum(1 for w in norm_words if w in self.MARATHI_CUES)
        hindi_hits = sum(1 for w in norm_words if w in self.HINDI_CUES)

        # Check for Marathi suffixes like -ला, -na, -ch, -la
        for w in norm_words:
            if w.endswith("ला") or w.endswith("-la") or w.endswith("la") or w.endswith("ycha") or w.endswith("ychi"):
                marathi_hits += 1
            if w.endswith("को") or w.endswith("-ko") or w.endswith("na") or w.endswith("enge"):
                hindi_hits += 1

        if marathi_hits > hindi_hits:
            return "marathi"
        elif hindi_hits > marathi_hits:
            return "hindi"

        # Default fallback
        return "hindi"

    COLLOQUIAL_SLANG_MAP = {
        "meko": "mujhe",
        "mereko": "mujhe",
        "teko": "tujhe",
        "tereko": "tujhe",
        "apanko": "humein",
        "jana": "jaana",
        "nhi": "nahi",
        "clg": "college",
    }

    def normalize(self, text: str) -> str:
        if not text:
            return ""
        # Collapse multiple whitespace
        clean = re.sub(r'\s+', ' ', text.strip())
        # Clean stray double quotes or unneeded artifacts
        clean = clean.replace('“', '"').replace('”', '"')
        
        # Normalize informal chat tokens so standard translation models understand them
        tokens = clean.split()
        normalized_tokens = []
        for t in tokens:
            lower_t = t.lower()
            if lower_t in self.COLLOQUIAL_SLANG_MAP:
                replacement = self.COLLOQUIAL_SLANG_MAP[lower_t]
                # preserve casing if uppercase
                normalized_tokens.append(replacement.capitalize() if t.istitle() else replacement)
            else:
                normalized_tokens.append(t)
        return ' '.join(normalized_tokens)

language_detector = RuleBasedLanguageDetector()
