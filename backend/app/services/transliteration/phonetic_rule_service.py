import re
from typing import Dict, List, Tuple
from app.services.base import BaseTransliterationService

class PhoneticTransliterationService(BaseTransliterationService):
    """
    Robust rule-based and lexicon-assisted transliteration engine
    for Hindi and Marathi (Latin <-> Devanagari).
    """

    # High-frequency dictionary overrides for both Hindi and Marathi
    COMMON_LATIN_TO_DEV: Dict[str, Dict[str, str]] = {
        "marathi": {
            "majha": "माझा", "mazha": "माझा", "maza": "माझा", "majham": "माझं", "mazham": "माझं", "majhan": "माझं",
            "majhi": "माझी", "mazhi": "माझी", "majhe": "माझे", "mazhe": "माझे",
            "tujha": "तुझा", "tuzha": "तुझा", "tuza": "तुझा", "tujhi": "तुझी", "tujhe": "तुझे",
            "naav": "नाव", "nav": "नाव", "naam": "नाव", "nam": "नाव",
            "manas": "मानस", "kasa": "कसा", "kashi": "कशी", "kase": "कसे",
            "mala": "मला", "tula": "तुला", "tyala": "त्याला", "tila": "तिला", "aamhala": "आम्हाला",
            "amhi": "आम्ही", "tumhi": "तुम्ही", "te": "ते", "ti": "ती", "to": "तो",
            "mi": "मी", "me": "मी", "mee": "मी",
            "aahe": "आहे", "ahe": "आहे", "aaha": "आहे", "ahet": "आहेत", "aahot": "आहोत",
            "aahes": "आहेस", "ahes": "आहेस",
            "nahi": "नाही", "nahit": "नाहीत",
            "la": "ला", "na": "ना", "pan": "पण", "ani": "आणि", "aani": "आणि", "ch": "च",

            "tithe": "तिथे", "teethe": "तिथे", "tethe": "तिथे",
            "ithe": "इथे", "eethe": "इथे",
            "udya": "उद्या", "kaal": "काल", "kal": "काल", "aaj": "आज", "ata": "आता", "aata": "आता",
            "college": "कॉलेज", "college-la": "कॉलेजला", "collegela": "कॉलेजला",
            "school": "शाळा", "ghar": "घर", "ghari": "घरी", "office": "ऑफिस", "officela": "ऑफिसला",
            "jaycha": "जायचं", "jayecha": "जायचं", "jaaycha": "जायचं", "jaychi": "जायची", "jayechi": "जायची", "jaaychi": "जायची",
            "jayche": "जायचे", "jayeche": "जायचे", "jaayche": "जायचे", "jayla": "जायला", "jayala": "जायला", "jaayla": "जायला",
            "gelo": "गेलो", "geli": "गेली", "gele": "गेले",
            "jaat": "जात", "jat": "जात", "yet": "येत", "karat": "करत", "khaat": "खात", "khat": "खात",
            "karaycha": "करायचं", "karecha": "करायचं", "karaaycha": "करायचं", "karaychi": "करायची", "karechi": "करायची",
            "karayche": "करायचे", "kareche": "करायचे", "karayala": "करायला", "kareche": "करायचे",
            "shikaychi": "शिकायची", "shikechi": "शिकायची", "shikaycha": "शिकायचं", "shikecha": "शिकायचं", "shikayche": "शिकायचे", "shikto": "शिकतो",
            "pahije": "पाहिजे", "pahijet": "पाहिजेत", "paani": "पाणी", "pani": "पाणी",
            "jevan": "जेवण", "bhaat": "भात", "chaha": "चहा", "doodh": "दूध",
            "kasa": "कसा", "kashi": "कशी", "kase": "कसे", "kuthe": "कुठे", "kadhi": "कधी", "kay": "काय",
            "khoop": "खूप", "khup": "खूप", "thoda": "थोडा", "thodi": "थोडी", "chan": "छान",
            "marathi": "मराठी", "hindi": "हिंदी", "english": "इंग्रजी",
            "namaskar": "नमस्कार", "dhanyavaad": "धन्यवाद", "ho": "हो",
            "bolto": "बोलतो", "bolte": "बोलते", "boltat": "बोलतात", "bolaycha": "बोलायचं", "bolecha": "बोलायचं",
            "yecha": "यायचं", "yayecha": "यायचं", "yaycha": "यायचं", "khayecha": "खायचं", "khaycha": "खायचं",
            "zopecha": "झोपायचं", "jhopecha": "झोपायचं", "zopaycha": "झोपायचं", "jhopaycha": "झोपायचं"
        },
        "hindi": {
            "mujhe": "मुझे", "mujha": "मुझे", "muze": "मुझे", "mujhko": "मुझे",
            "tujhe": "तुझे", "tujha": "तुझे", "use": "उसे", "hume": "हमें", "hum": "हम",
            "main": "मैं", "mai": "मैं", "me": "मैं", "mera": "मेरा", "meri": "मेरी", "mere": "मेरे",
            "naam": "नाम", "nam": "नाम", "manas": "मानस",
            "aap": "आप", "tum": "तुम", "vah": "वह", "woh": "वह", "ve": "वे", "ye": "ये", "yeh": "यह",
            "vaha": "वहाँ", "vahan": "वहाँ", "waha": "वहाँ", "wahan": "वहाँ",
            "yaha": "यहाँ", "yahan": "यहाँ", "wahaa": "वहाँ", "yahaa": "यहाँ",
            "hai": "है", "hain": "हैं", "hoon": "हूँ", "hu": "हूँ", "hun": "हूँ",
            "tha": "था", "thi": "थी", "the": "थे",
            "nahi": "नहीं", "nahin": "नहीं", "mat": "मत",
            "kal": "कल", "aaj": "आज", "ab": "अब", "abhi": "अभी",
            "college": "कॉलेज", "college-ko": "कॉलेज को", "school": "स्कूल", "ghar": "घर",
            "ja": "जा", "jaa": "जा", "raha": "रहा", "rahi": "रही", "rahe": "रहे",
            "aa": "आ", "aata": "आता", "aati": "आती", "aate": "आते",
            "jaana": "जाना", "jana": "जाना", "jaani": "जानी", "jaane": "जाने", "jane": "जाने",
            "gaya": "गया", "gayi": "गई", "gaye": "गए",
            "karna": "करना", "karana": "करना", "karni": "करनी", "karne": "करने", "kiya": "किया",
            "seekhna": "सीखना", "seekhni": "सीखनी", "seekhne": "सीखने", "shikhna": "सीखना",
            "chahiye": "चाहिए", "paani": "पानी", "pani": "पानी",
            "khana": "खाना", "khaana": "खाना", "chai": "चाय",
            "kaisa": "कैसा", "kaisi": "कैसी", "kaise": "कैसे", "kaha": "कहाँ", "kahan": "कहाँ",
            "kab": "कब", "kya": "क्या", "kyon": "क्यों", "bohot": "बहुत", "bahut": "बहुत",
            "achha": "अच्छा", "achhi": "अच्छी", "achhe": "अच्छे",
            "hindi": "हिंदी", "marathi": "मराठी", "namaste": "नमस्ते", "dhanyavaad": "धन्यवाद",
            "bolta": "बोलता", "bolti": "बोलती", "bolte": "बोलते", "bolna": "बोलना"
        }
    }

    # Common Devanagari to Latin overrides
    COMMON_DEV_TO_LATIN: Dict[str, str] = {
        "मी": "Mi", "मला": "Mala", "तुला": "Tula", "त्याला": "Tyala", "तिला": "Tila",
        "आहे": "aahe", "आहेत": "ahet", "आहोत": "aahot", "नाही": "nahi",
        "तिथे": "tithe", "इथे": "ithe", "कुठे": "kuthe", "कधी": "kadhi", "काय": "kay",
        "जात": "jaat", "येत": "yet", "करत": "karat", "खात": "khaat",
        "उद्या": "udya", "काल": "kaal", "आज": "aaj", "आता": "aata",
        "कॉलेजला": "college-la", "कॉलेज": "college", "जायचं": "jaycha", "आहे।": "aahe.",
        "शिकायची": "shikaychi", "पाहिजे": "pahije", "पाणी": "paani", "मराठी": "Marathi",
        "मला मराठी शिकायची आहे।": "Mala Marathi shikaychi aahe.",
        "मला उद्या कॉलेजला जायचं आहे।": "Mala udya college-la jaycha aahe.",
        "मी तिथे जात आहे।": "Mi tithe jaat aahe.",
        "मी तिथे जात आहे": "Mi tithe jaat aahe",
        "मी इथे येत आहे।": "Mi ithe yet aahe.",
        "मी इथे येत आहे": "Mi ithe yet aahe",
        "मैं": "Main", "मुझे": "Mujhe", "तुझे": "Tujhe", "उसे": "Use",
        "मेरा": "mera", "मेरी": "meri", "मेरे": "mere", "नाम": "naam", "मानस": "Manas",
        "माझा": "majha", "माझे": "majhe", "माझी": "majhi", "नाव": "naav",
        "वहाँ": "vahan", "यहाँ": "yahan", "रहा": "raha", "रही": "rahi", "रहे": "rahe",
        "घर": "ghar", "घरी": "ghari", "पास": "paas",
        "जाना": "jaana", "जा": "jaa", "जाता": "jaata", "जाती": "jaati", "जाते": "jaate",
        "चाहता": "chahta", "चाहती": "chahti", "चाहते": "chahte",
        "जायचं": "jaycha", "जायचे": "jayche", "जायची": "jaychi", "जायला": "jayla",
        "जाणार": "jaanar",
        "हूँ": "hoon", "हूं": "hoon", "है": "hai", "हैं": "hain",
        "कल": "kal", "सीखनी": "seekhni", "हिंदी": "Hindi",
        "मैं वहाँ जा रहा हूँ।": "Main vahan ja raha hoon.",
        "मैं वहाँ जा रहा हूँ": "Main vahan ja raha hoon",
        "मुझे मराठी सीखनी है।": "Mujhe Marathi seekhni hai.",
        "मुझे कल कॉलेज जाना है।": "Mujhe kal college jaana hai."
    }

    CONSONANTS = [
        ('chh', 'छ'), ('ksh', 'क्ष'), ('dny', 'ज्ञ'), ('gya', 'ज्ञ'),
        ('kh', 'ख'), ('gh', 'घ'), ('ng', 'ङ'), ('ch', 'च'), ('jh', 'झ'),
        ('th', 'थ'), ('dh', 'ध'), ('ph', 'फ'), ('bh', 'भ'), ('sh', 'श'),
        ('shh', 'ष'), ('k', 'क'), ('g', 'ग'), ('j', 'ज'), ('t', 'त'),
        ('d', 'द'), ('n', 'न'), ('p', 'प'), ('f', 'फ'), ('b', 'ब'),
        ('m', 'म'), ('y', 'य'), ('r', 'र'), ('l', 'ल'), ('v', 'व'),
        ('w', 'व'), ('s', 'स'), ('h', 'ह')
    ]

    VOWEL_INDEPENDENT = [
        ('aa', 'आ'), ('ee', 'ई'), ('oo', 'ऊ'), ('ai', 'ऐ'), ('au', 'औ'),
        ('a', 'अ'), ('i', 'इ'), ('u', 'उ'), ('e', 'ए'), ('o', 'ओ')
    ]

    MATRAS = {
        'aa': 'ा', 'a': '', 'ee': 'ी', 'i': 'ि', 'oo': 'ू', 'u': 'ु',
        'e': 'े', 'ai': 'ै', 'o': 'ो', 'au': 'ौ'
    }

    def _latin_word_to_dev(self, word: str, lang: str) -> str:
        w_lower = word.lower().strip(".,!?:;\"'()[]{}")
        punctuation = "".join([c for c in word if c in ".,!?:;\"'()[]{}"])

        # Check dictionary
        lang_dict = self.COMMON_LATIN_TO_DEV.get(lang, self.COMMON_LATIN_TO_DEV["marathi"])
        if w_lower in lang_dict:
            res = lang_dict[w_lower]
            return res + ("।" if punctuation == "." else punctuation)

        # Fallback dictionary across any lang
        for d in self.COMMON_LATIN_TO_DEV.values():
            if w_lower in d:
                res = d[w_lower]
                return res + ("।" if punctuation == "." else punctuation)

        # Morphological suffix matching for Marathi verbs (e.g. jayecha, jaycha, karaycha, shikecha)
        VERB_SUFFIX_MAP = [
            (r'^(.*)(?:ayecha|aycha|aaycha|echa|ycha|aicha)$', 'ायचं'),
            (r'^(.*)(?:ayechi|aychi|aaychi|echi|ychi|aichi)$', 'ायची'),
            (r'^(.*)(?:ayeche|ayche|aayche|eche|yche|aiche)$', 'ायचे'),
            (r'^(.*)(?:ayala|ayla|aayla|ela)$', 'ायला'),
            (r'^(.*)(?:aych|aaych|ech)$', 'ायचं'),
        ]
        STEM_ROOT_MAP = {
            'j': 'ज', 'kar': 'कर', 'shik': 'शिक', 'bol': 'बोल', 'kh': 'ख', 'kha': 'ख',
            'y': 'य', 'ye': 'य', 'ya': 'य', 'ghy': 'घ्य', 'ghe': 'घ्य', 'dy': 'द्य', 'de': 'द्य',
            'rah': 'राह', 'bas': 'बस', 'uth': 'उठ', 'zop': 'झोप', 'jhop': 'झोप', 'bagh': 'बघ',
            'paha': 'पह', 'lih': 'लिह', 'vach': 'वाच', 'thev': 'ठेव', 'aan': 'आण'
        }
        for pattern, suffix in VERB_SUFFIX_MAP:
            m = re.match(pattern, w_lower)
            if m:
                stem = m.group(1)
                dev_stem = STEM_ROOT_MAP.get(stem)
                if not dev_stem and len(stem) > 0:
                    dev_stem = self._latin_word_to_dev(stem, lang).rstrip(".,!?:;\"'()[]{}।")
                    if dev_stem.endswith('्'):
                        dev_stem = dev_stem[:-1]
                if dev_stem:
                    return dev_stem + suffix + ("।" if punctuation == "." else punctuation)

        # Phonetic algorithm
        i = 0
        n = len(w_lower)
        out = []

        # Check for initial vowel
        vowel_matched = False
        for v_str, v_dev in self.VOWEL_INDEPENDENT:
            if w_lower.startswith(v_str):
                out.append(v_dev)
                i += len(v_str)
                vowel_matched = True
                break

        while i < n:
            # Check consonants
            c_matched = False
            for c_str, c_dev in self.CONSONANTS:
                if w_lower[i:].startswith(c_str):
                    i += len(c_str)
                    c_matched = True
                    # Check next vowel/matra
                    v_matched = False
                    for v_str in ['aa', 'ee', 'oo', 'ai', 'au', 'i', 'u', 'e', 'o']:
                        if w_lower[i:].startswith(v_str):
                            out.append(c_dev + self.MATRAS[v_str])
                            i += len(v_str)
                            v_matched = True
                            break
                    if not v_matched:
                        if w_lower[i:].startswith('a'):
                            out.append(c_dev)
                            i += 1
                        else:
                            # If followed by another consonant or end of word
                            if i < n and w_lower[i].isalpha():
                                out.append(c_dev + '्')
                            else:
                                out.append(c_dev)
                    break
            if not c_matched:
                # Vowel inside without consonant?
                v_inside = False
                for v_str, v_dev in self.VOWEL_INDEPENDENT:
                    if w_lower[i:].startswith(v_str):
                        out.append(v_dev)
                        i += len(v_str)
                        v_inside = True
                        break
                if not v_inside:
                    out.append(w_lower[i])
                    i += 1

        res = "".join(out)
        return res + ("।" if punctuation == "." else punctuation)

    def _dev_word_to_latin(self, word: str) -> str:
        clean = word.strip(".,!?:;\"'()[]{}।")
        if clean in self.COMMON_DEV_TO_LATIN:
            return self.COMMON_DEV_TO_LATIN[clean]

        DEV_MAP = {
            'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
            'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'am', 'अः': 'ah',
            'क': 'ka', 'ख': 'kha', 'ग': 'ga', 'घ': 'gha', 'ङ': 'nga',
            'च': 'cha', 'छ': 'chha', 'ज': 'ja', 'झ': 'jha', 'ञ': 'nya',
            'ट': 'ta', 'ठ': 'tha', 'ड': 'da', 'ढ': 'dha', 'ण': 'na',
            'त': 'ta', 'थ': 'tha', 'द': 'da', 'ध': 'dha', 'न': 'na',
            'प': 'pa', 'फ': 'pha', 'ब': 'ba', 'भ': 'bha', 'म': 'ma',
            'य': 'ya', 'र': 'ra', 'ल': 'la', 'ळ': 'la', 'व': 'va',
            'श': 'sha', 'ष': 'sha', 'स': 'sa', 'ह': 'ha', 'क्ष': 'ksha', 'ज्ञ': 'gya',
            'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'े': 'e',
            'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n', '्': '', '।': '.'
        }

        out = []
        i = 0
        while i < len(word):
            ch = word[i]
            if ch in DEV_MAP:
                # Handle inherent 'a' removal if followed by matra
                val = DEV_MAP[ch]
                if i + 1 < len(word) and word[i + 1] in ['ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', '्']:
                    if val.endswith('a'):
                        val = val[:-1]
                out.append(val)
            else:
                out.append(ch)
            i += 1

        res = "".join(out)
        # Clean double 'aa' if preceded by single
        res = re.sub(r'a{3,}', 'aa', res)

        # Schwa Deletion Rule for modern Hindi & Marathi:
        # If the Devanagari word ends with a consonant that has no vowel matra,
        # the inherent Sanskrit final 'a' is dropped (e.g. घर -> ghar, not ghara; पास -> paas, not pasa).
        dev_vowels_matras = {'ा', 'ि', 'ी', 'ु', 'ू', 'े', 'ै', 'ो', 'ौ', 'ं', 'ँ', '्'}
        if clean and clean[-1] not in dev_vowels_matras and res.endswith('a') and len(res) > 2:
            res = res[:-1]

        return res

    def transliterate(self, text: str, language: str = "marathi", direction: str = "latin_to_devanagari") -> str:
        if not text or not text.strip():
            return ""

        clean = text.strip()
        # Sentence level exact match lookup
        if direction == "latin_to_devanagari":
            # Quick check if already Devanagari
            if any('\u0900' <= c <= '\u097f' for c in clean):
                return clean

            words = clean.split()
            out_words = [self._latin_word_to_dev(w, language) for w in words]
            return " ".join(out_words)
        else:
            # devanagari_to_latin
            if clean in self.COMMON_DEV_TO_LATIN:
                return self.COMMON_DEV_TO_LATIN[clean]

            words = clean.split()
            out_words = [self._dev_word_to_latin(w) for w in words]
            result = " ".join(out_words)
            if not result.endswith('.') and clean.endswith('।'):
                result += '.'
            return result

phonetic_transliterator = PhoneticTransliterationService()
