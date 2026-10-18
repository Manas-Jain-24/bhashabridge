"""
BhashaBridge — Bilingual Word & Construction Aligner (M4)
Aligns Hindi and Marathi words/phrases and flags construction-based mappings
vs direct lexical equivalents as strictly required by Section 8 of the product spec.
"""

from typing import List
from app.schemas.analyze import VocabularyItem

# Lexicon of frequent grammatical and conversational alignments
ALIGNMENT_LEXICON = [
    # Pronouns & Case Markers (with Universal Dependencies Morphological Tags)
    {"hi": "मैं", "mr": "मी", "mr_rom": "Mi", "meaning": "I (1st person pronoun)", "pos": "pronoun", "is_construction": False, "morph": "Case=Nom | Person=1 | Number=Sing", "root": "मी (I)"},
    {"hi": "मै", "mr": "मी", "mr_rom": "Mi", "meaning": "I (1st person pronoun)", "pos": "pronoun", "is_construction": False, "morph": "Case=Nom | Person=1 | Number=Sing", "root": "मी (I)"},
    {"hi": "मुझे", "mr": "मला", "mr_rom": "Mala", "meaning": "to me / I (dative subject)", "pos": "pronoun", "is_construction": True, "morph": "Case=Dat | Suffix=-ला | Experiencer Subject", "root": "मी (I) ➔ मला (to me)"},
    {"hi": "तुझे", "mr": "तुला", "mr_rom": "Tula", "meaning": "to you (informal dative)", "pos": "pronoun", "is_construction": True, "morph": "Case=Dat | Suffix=-ला | Informal Dative", "root": "तू (you) ➔ तुला (to you)"},
    {"hi": "उसे", "mr": "त्याला / तिला", "mr_rom": "Tyala / Tila", "meaning": "to him / her (dative)", "pos": "pronoun", "is_construction": True, "morph": "Case=Dat | Gender=Masc/Fem | Suffix=-ला", "root": "तो/ती ➔ त्याला/तिला"},
    {"hi": "हमें", "mr": "आम्हाला", "mr_rom": "Aamhala", "meaning": "to us (exclusive dative)", "pos": "pronoun", "is_construction": True, "morph": "Case=Dat | Number=Plur | Exclusive 1P", "root": "आम्ही ➔ आम्हाला"},
    {"hi": "आप", "mr": "तुम्ही", "mr_rom": "Tumhi", "meaning": "you (respectful/formal)", "pos": "pronoun", "is_construction": False, "morph": "Case=Nom | Honorific=Yes | 2nd Person", "root": "तुम्ही"},
    {"hi": "तुम", "mr": "तू", "mr_rom": "Tu", "meaning": "you (informal singular)", "pos": "pronoun", "is_construction": False, "morph": "Case=Nom | Informal=Yes | 2nd Person Sing", "root": "तू"},
    {"hi": "मेरा", "mr": "माझा / माझं", "mr_rom": "Mazha", "meaning": "my / mine", "pos": "possessive", "is_construction": False, "gender": "Marathi: 3 Genders (माझा/माझी/माझं) | Hindi: 2 Genders (मेरा/मेरी)", "morph": "PronType=Prs | Poss=Yes", "root": "मी"},
    {"hi": "तुम्हारा", "mr": "तुझा / तुझं", "mr_rom": "Tuzha", "meaning": "your / yours", "pos": "possessive", "is_construction": False, "gender": "Marathi: 3 Genders (तुझा/तुझी/तुझं) | Hindi: 2 Genders (तुम्हारा/तुम्हारी)", "morph": "PronType=Prs | Poss=Yes", "root": "तू"},
    {"hi": "आपका", "mr": "तुमचा / तुमचं", "mr_rom": "Tumcha", "meaning": "your (honorific)", "pos": "possessive", "is_construction": False, "gender": "Marathi: 3 Genders (तुमचा/तुमची/तुमचं)", "morph": "PronType=Prs | Poss=Yes | Polite=Yes", "root": "तुम्ही"},
    {"hi": "नाम", "mr": "नाव", "mr_rom": "Naav", "meaning": "name (neuter noun in Marathi)", "pos": "noun", "is_construction": False, "gender": "Marathi: Neuter (नाव) ➔ माझं नाव | Hindi: Masculine (नाम) ➔ मेरा नाम", "morph": "Noun | Gender=Neut | Case=Nom", "root": "नाव"},

    # Spatial & Deictic Markers
    {"hi": "वहाँ", "mr": "तिथे", "mr_rom": "tithe", "meaning": "there (adverb of place)", "pos": "adverb", "is_construction": False, "morph": "AdvType=Loc | Distal Deictic", "root": "तिथे"},
    {"hi": "वहा", "mr": "तिथे", "mr_rom": "tithe", "meaning": "there (adverb of place)", "pos": "adverb", "is_construction": False, "morph": "AdvType=Loc | Distal Deictic", "root": "तिथे"},
    {"hi": "यहाँ", "mr": "इथे", "mr_rom": "ithe", "meaning": "here (adverb of place)", "pos": "adverb", "is_construction": False, "morph": "AdvType=Loc | Proximal Deictic", "root": "इथे"},
    {"hi": "यहा", "mr": "इथे", "mr_rom": "ithe", "meaning": "here (adverb of place)", "pos": "adverb", "is_construction": False, "morph": "AdvType=Loc | Proximal Deictic", "root": "इथे"},

    # Temporal Markers
    {"hi": "कल", "mr": "उद्या", "mr_rom": "udya", "meaning": "tomorrow (unambiguous future)", "pos": "adverb", "is_construction": True, "morph": "Tense=Fut | Hindi 'कल' is ambiguous, Marathi uses 'उद्या' exclusively", "root": "उद्या"},
    {"hi": "आज", "mr": "आज", "mr_rom": "aaj", "meaning": "today", "pos": "adverb", "is_construction": False, "morph": "Tense=Pres | Cognate Adverb", "root": "आज"},
    {"hi": "अब", "mr": "आता", "mr_rom": "aata", "meaning": "now", "pos": "adverb", "is_construction": False, "morph": "Tense=Pres | Temporal Deictic", "root": "आता"},
    {"hi": "सुबह", "mr": "सकाळी", "mr_rom": "sakaali", "meaning": "in the morning", "pos": "adverb", "is_construction": True, "morph": "Case=Loc | Suffix=-ी on सकाळ", "root": "सकाळ + -ी"},
    {"hi": "रात", "mr": "रात्री", "mr_rom": "raatri", "meaning": "at night", "pos": "adverb", "is_construction": True, "morph": "Case=Loc | Suffix=-ी on रात्र", "root": "रात्र + -ी"},

    # Destinations & Objects
    {"hi": "कॉलेज", "mr": "कॉलेजला", "mr_rom": "college-la", "meaning": "to college (dative -ला suffix)", "pos": "noun + postposition", "is_construction": True, "morph": "Case=Dat (Goal) | Suffix=-ला attached synthetically", "root": "कॉलेज + -ला"},
    {"hi": "ऑफिस", "mr": "ऑफिसला", "mr_rom": "office-la", "meaning": "to office (dative -ला suffix)", "pos": "noun + postposition", "is_construction": True, "morph": "Case=Dat (Goal) | Suffix=-ला attached synthetically", "root": "ऑफिस + -ला"},
    {"hi": "घर", "mr": "घरी", "mr_rom": "ghari", "meaning": "at home (locative -ी suffix)", "pos": "noun + postposition", "is_construction": True, "morph": "Case=Loc | Suffix=-ी attached directly", "root": "घर + -ी"},
    {"hi": "पानी", "mr": "पाणी", "mr_rom": "paani", "meaning": "water (neuter noun in Marathi)", "pos": "noun", "is_construction": False, "gender": "Marathi: Neuter (पाणी) | Hindi: Masculine (पानी)", "morph": "Noun | Gender=Neut | Sound shift: n ➔ ṇ (ण)", "root": "पाणी"},
    {"hi": "पाणी", "mr": "पाणी", "mr_rom": "paani", "meaning": "water (neuter noun in Marathi)", "pos": "noun", "is_construction": False, "gender": "Marathi: Neuter (पाणी) | Hindi: Masculine (पानी)", "morph": "Noun | Gender=Neut | Sound shift: n ➔ ṇ (ण)", "root": "पाणी"},
    {"hi": "खाना", "mr": "जेवण", "mr_rom": "jevan", "meaning": "meal / food (neuter in Marathi)", "pos": "noun", "is_construction": False, "gender": "Marathi: Neuter (जेवण)", "morph": "Noun | Gender=Neut | Case=Nom", "root": "जेवण"},
    {"hi": "चाय", "mr": "चहा", "mr_rom": "chaha", "meaning": "tea (masculine in Marathi)", "pos": "noun", "is_construction": False, "gender": "Marathi: Masculine (चहा) | Hindi: Feminine (चाय)", "morph": "Noun | Gender=Masc", "root": "चहा"},

    # Verb Phrases, Modals & Continuous Aspects
    {"hi": "जा रहा हूँ", "mr": "जात आहे", "mr_rom": "jaat aahe", "meaning": "am going (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp (-त participle) | Aux=Pres (आहे)", "root": "जा- + -त आहे"},
    {"hi": "जा रहा हु", "mr": "जात आहे", "mr_rom": "jaat aahe", "meaning": "am going (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp (-त participle) | Aux=Pres (आहे)", "root": "जा- + -त आहे"},
    {"hi": "जा रहे हैं", "mr": "जात आहेत", "mr_rom": "jaat ahet", "meaning": "are going (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp | Aux=Pres Plur (आहेत)", "root": "जा- + -त आहेत"},
    {"hi": "जा रहे हो", "mr": "जात आहेस", "mr_rom": "jaat aahes", "meaning": "are going (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp | Aux=Pres 2P (आहेस)", "root": "जा- + -त आहेस"},
    {"hi": "आ रहा हूँ", "mr": "येत आहे", "mr_rom": "yet aahe", "meaning": "am coming (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp (-त participle) | Aux=Pres (आहे)", "root": "ये- + -त आहे"},
    {"hi": "कर रहा हूँ", "mr": "करत आहे", "mr_rom": "karat aahe", "meaning": "am doing (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp (-त participle) | Aux=Pres (आहे)", "root": "कर- + -त आहे"},
    {"hi": "खा रहा हूँ", "mr": "खात आहे", "mr_rom": "khaat aahe", "meaning": "am eating (present continuous)", "pos": "verb phrase", "is_construction": True, "morph": "Aspect=Imp (-त participle) | Aux=Pres (आहे)", "root": "खा- + -त आहे"},
    {"hi": "जाना है", "mr": "जायचं आहे", "mr_rom": "jaycha aahe", "meaning": "have to go / must go (obligation modal)", "pos": "verb phrase", "is_construction": True, "morph": "Mood=Obligation | Neuter potential participle -चं | Aux=आहे", "root": "जा- + -चं आहे"},
    {"hi": "सीखनी है", "mr": "शिकायची आहे", "mr_rom": "shikaychi aahe", "meaning": "want to learn (feminine language agreement)", "pos": "verb phrase", "is_construction": True, "gender": "Feminine agreement: भाषा/मराठी is feminine, verb takes -ची", "morph": "Mood=Desiderative | Gender=Fem (-ची participle)", "root": "शिक- + -ची आहे"},
    {"hi": "करना है", "mr": "करायचं आहे", "mr_rom": "karaycha aahe", "meaning": "have to do (obligation modal)", "pos": "verb phrase", "is_construction": True, "morph": "Mood=Obligation | Participle=-चं | Aux=आहे", "root": "कर- + -चं आहे"},
    {"hi": "चाहिए", "mr": "हवे आहे", "mr_rom": "have aahe", "meaning": "want / need (inflecting modal)", "pos": "modal verb phrase", "is_construction": True, "gender": "Marathi: 'हवे' inflects to agree with neuter noun 'पाणी' (M: हवा, F: हवी, N: हवे). Hindi: 'चाहिए' is uninflected.", "morph": "Mood=Desiderative | Agreement=Neuter Sing | Suffix=-े", "root": "हवे असणे (to be wanted)"},
    {"hi": "चाहिए", "mr": "हवा आहे", "mr_rom": "hava aahe", "meaning": "want / need (masculine modal)", "pos": "modal verb phrase", "is_construction": True, "gender": "Marathi: Masculine agreement with object (उदा. चहा हवा आहे).", "morph": "Mood=Desiderative | Agreement=Masc Sing", "root": "हवा असणे"},
    {"hi": "चाहिए", "mr": "हवी आहे", "mr_rom": "havi aahe", "meaning": "want / need (feminine modal)", "pos": "modal verb phrase", "is_construction": True, "gender": "Marathi: Feminine agreement with object (उदा. कॉफी हवी आहे).", "morph": "Mood=Desiderative | Agreement=Fem Sing", "root": "हवी असणे"},
    {"hi": "चाहिए", "mr": "हवे", "mr_rom": "have", "meaning": "want / need (neuter modal)", "pos": "modal", "is_construction": True, "gender": "Marathi: Neuter agreement with 'पाणी' (उदा. पाणी हवे).", "morph": "Mood=Desiderative | Gender=Neut", "root": "हवे"},
    {"hi": "चाहिए", "mr": "पाहिजे", "mr_rom": "pahije", "meaning": "want / need (necessity modal)", "pos": "modal", "is_construction": True, "gender": "Invariable necessity modal; requires dative subject (मला).", "morph": "Mood=Necessity | Requires Dative subject (मला)", "root": "पाहिजे"},
    {"hi": "है", "mr": "आहे", "mr_rom": "aahe", "meaning": "is (present auxiliary)", "pos": "auxiliary", "is_construction": False, "morph": "VerbForm=Fin | Tense=Pres | Number=Sing", "root": "असणे"},
    {"hi": "हूँ", "mr": "आहे", "mr_rom": "aahe", "meaning": "am (present auxiliary)", "pos": "auxiliary", "is_construction": False, "morph": "VerbForm=Fin | Tense=Pres | Person=1", "root": "असणे"},
    {"hi": "हैं", "mr": "आहेत / आहात", "mr_rom": "ahet / aahat", "meaning": "are (plural / honorific auxiliary)", "pos": "auxiliary", "is_construction": False, "morph": "VerbForm=Fin | Tense=Pres | Number=Plur", "root": "असणे"},
    {"hi": "नहीं", "mr": "नाही", "mr_rom": "nahi", "meaning": "no / not", "pos": "negation", "is_construction": False, "morph": "Polarity=Neg", "root": "नाही"},

    # Interrogatives & Modifiers
    {"hi": "कहाँ", "mr": "कुठे", "mr_rom": "kuthe", "meaning": "where", "pos": "interrogative", "is_construction": False, "morph": "PronType=Int | Locative Adverb", "root": "कुठे"},
    {"hi": "कब", "mr": "कधी", "mr_rom": "kadhi", "meaning": "when", "pos": "interrogative", "is_construction": False, "morph": "PronType=Int | Temporal Adverb", "root": "कधी"},
    {"hi": "क्या", "mr": "काय", "mr_rom": "kay", "meaning": "what", "pos": "interrogative", "is_construction": False, "gender": "Marathi: Neuter interrogative (काय)", "morph": "PronType=Int | Neutral", "root": "काय"},
    {"hi": "कैसा", "mr": "कसा", "mr_rom": "kasa", "meaning": "how (masculine)", "pos": "interrogative", "is_construction": False, "gender": "Gender=Masc (कसा) vs Fem (कशी) vs Neut (कसं)", "morph": "PronType=Int | Gender=Masc", "root": "कसा"},
    {"hi": "कैसी", "mr": "कशी", "mr_rom": "kashi", "meaning": "how (feminine)", "pos": "interrogative", "is_construction": False, "gender": "Gender=Fem (कशी)", "morph": "PronType=Int | Gender=Fem", "root": "कशी"},
    {"hi": "कैसे", "mr": "कसे", "mr_rom": "kase", "meaning": "how (plural/honorific)", "pos": "interrogative", "is_construction": False, "morph": "PronType=Int | Number=Plur", "root": "कसे"},
    {"hi": "बहुत", "mr": "खूप", "mr_rom": "khoop", "meaning": "very / much", "pos": "adverb", "is_construction": False, "morph": "Degree=Sup | Intensifier", "root": "खूप"},
    {"hi": "अच्छा", "mr": "छान / चांगला", "mr_rom": "chan / changla", "meaning": "good / nice", "pos": "adjective", "is_construction": False, "gender": "चांगला (Masc) / चांगली (Fem) / चांगलं (Neut)", "morph": "Degree=Pos | Inflects for 3 genders", "root": "चांगला"}
]

import json
from pathlib import Path

# Automatically augment with the 1,500+ extended lexicon if present
_EXT_LEXICON_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "data" / "processed" / "learning" / "marathi_hindi_vocab_1500.json"
if _EXT_LEXICON_PATH.exists():
    try:
        with open(_EXT_LEXICON_PATH, "r", encoding="utf-8") as _f:
            _ext_items = json.load(_f)
            _seen_hi_mr = {(item.get("hi", "").lower(), item.get("mr", "").lower()) for item in ALIGNMENT_LEXICON}
            for item in _ext_items:
                hi_w = item.get("hindi_devanagari", "").strip()
                mr_w = item.get("marathi_devanagari", "").strip()
                if hi_w and mr_w:
                    pair_key = (hi_w.lower(), mr_w.lower())
                    if pair_key not in _seen_hi_mr:
                        _seen_hi_mr.add(pair_key)
                        ALIGNMENT_LEXICON.append({
                            "hi": hi_w,
                            "mr": mr_w,
                            "mr_rom": item.get("marathi_roman", mr_w),
                            "meaning": item.get("english_meaning", ""),
                            "pos": item.get("part_of_speech", "word"),
                            "is_construction": "construction" in item.get("part_of_speech", "").lower() or "dative" in item.get("gender_info", "").lower(),
                            "morph": item.get("bridge_note") or f"POS={item.get('part_of_speech', 'word')} | Topic={item.get('topic', 'general')}",
                            "gender": item.get("gender_info") if item.get("gender_info") and ("M:" in item.get("gender_info") or "Neuter" in item.get("gender_info")) else None,
                            "root": f"{mr_w} ({item.get('topic', 'word')})"
                        })
    except Exception:
        pass

import re

def _norm_dev(t: str) -> str:
    """Normalize common cross-language/transliteration Devanagari character variants."""
    if not t:
        return ""
    return (
        t.replace("ण", "न")
        .replace("ळ", "ल")
        .replace("ष", "श")
        .replace("\u093c", "")  # nukta
        .replace("ँ", "ं")
        .strip(".,!?:;\"'()[]{}।")
        .lower()
    )

def align_sentence_vocabulary(source_text: str, target_text: str, source_lang: str = "hindi") -> List[VocabularyItem]:
    """
    Scans source and target texts to produce comprehensive aligned vocabulary pairs.
    Uses multi-word expression matching, phonetic normalization, and dynamic token fallback
    so that 100% of the sentence is accounted for and explained.
    """
    clean_src = source_text.lower()
    clean_tgt = target_text.lower()
    norm_src = _norm_dev(clean_src)
    norm_tgt = _norm_dev(clean_tgt)

    aligned: List[VocabularyItem] = []
    seen_mr = set()

    # Sort lexicon so multi-word expressions (e.g. 'हवे आहे', 'जा रहा हूँ') match before single words
    sorted_lexicon = sorted(
        ALIGNMENT_LEXICON,
        key=lambda x: len(x["hi"] if source_lang == "hindi" else x["mr"]),
        reverse=True
    )

    for entry in sorted_lexicon:
        hi_term = entry["hi"].lower()
        mr_term = entry["mr"].lower()
        norm_hi = _norm_dev(hi_term)
        norm_mr = _norm_dev(mr_term)

        # Check direct or phonetically normalized match
        hi_match = (
            (hi_term in clean_src or norm_hi in norm_src) or
            (hi_term in clean_tgt or norm_hi in norm_tgt)
        )
        mr_match = (
            (mr_term in clean_src or norm_mr in norm_src) or
            (mr_term in clean_tgt or norm_mr in norm_tgt) or
            (entry.get("mr_rom", "").lower() in clean_tgt)
        )

        if hi_match and mr_match:
            key = entry["mr"].strip()
            src_word = entry["hi"] if source_lang == "hindi" else entry["mr"]
            tgt_word = entry["mr"] if source_lang == "hindi" else entry["hi"]

            # Avoid adding a sub-phrase if a longer phrase already covers this
            if any(prev.source_word == src_word and tgt_word != prev.target_word and tgt_word in prev.target_word for prev in aligned):
                continue

            if key not in seen_mr:
                seen_mr.add(key)
                tgt_rom = entry.get("mr_rom", entry["mr"]) if source_lang == "hindi" else entry["hi"]

                aligned.append(VocabularyItem(
                    source_word=src_word,
                    target_word=tgt_word,
                    target_roman=tgt_rom,
                    meaning=entry["meaning"],
                    part_of_speech=entry.get("pos", "word"),
                    is_construction_based=entry.get("is_construction", False),
                    morph_analysis=entry.get("morph"),
                    gender_contrast=entry.get("gender"),
                    root_lemma=entry.get("root")
                ))

    # Dynamic Token Fallback: Ensure unaligned content tokens in the sentence are matched
    src_tokens = [w.strip(".,!?:;\"'()[]{}।") for w in re.findall(r"[\w]+", source_text) if len(w) > 0]
    tgt_tokens = [w.strip(".,!?:;\"'()[]{}।") for w in re.findall(r"[\w]+", target_text) if len(w) > 0]

    matched_src = set()
    matched_tgt = set()
    for item in aligned:
        for sw in re.findall(r"[\w]+", item.source_word):
            matched_src.add(_norm_dev(sw))
        for tw in re.findall(r"[\w]+", item.target_word):
            matched_tgt.add(_norm_dev(tw))

    unmatched_src = [w for w in src_tokens if _norm_dev(w) not in matched_src]
    unmatched_tgt = [w for w in tgt_tokens if _norm_dev(w) not in matched_tgt]

    # 1. Align cognates / shared content words
    for sw in list(unmatched_src):
        for tw in list(unmatched_tgt):
            if _norm_dev(sw) == _norm_dev(tw):
                aligned.append(VocabularyItem(
                    source_word=sw,
                    target_word=tw,
                    target_roman=tw,
                    meaning=f"Content noun / Cognate word ({sw})",
                    part_of_speech="noun",
                    is_construction_based=False,
                    morph_analysis="Direct lexical cognate",
                    gender_contrast=None,
                    root_lemma=tw
                ))
                unmatched_src.remove(sw)
                unmatched_tgt.remove(tw)
                break

    # 2. Residual predicate pairing (e.g. residual verb particle)
    if unmatched_src and unmatched_tgt:
        aligned.append(VocabularyItem(
            source_word=" ".join(unmatched_src),
            target_word=" ".join(unmatched_tgt),
            target_roman=" ".join(unmatched_tgt),
            meaning="Predicate expression / Verbal construction",
            part_of_speech="verb phrase",
            is_construction_based=True,
            morph_analysis="Syntactic clause alignment",
            gender_contrast=None,
            root_lemma=" ".join(unmatched_tgt)
        ))

    # Sort aligned items in natural order of appearance in source_text
    def _order_key(item: VocabularyItem) -> int:
        idx = source_text.find(item.source_word)
        if idx >= 0:
            return idx
        norm_sw = _norm_dev(item.source_word)
        norm_st = _norm_dev(source_text)
        idx_norm = norm_st.find(norm_sw)
        return idx_norm if idx_norm >= 0 else 999

    aligned.sort(key=_order_key)

    # Safe fallback if nothing matched
    if not aligned:
        aligned.append(VocabularyItem(
            source_word=source_text.strip("।."),
            target_word=target_text.strip("।."),
            target_roman=target_text.strip("।."),
            meaning="Sentence-level equivalent expression",
            part_of_speech="phrase",
            is_construction_based=True,
            morph_analysis="Clause alignment",
            gender_contrast=None,
            root_lemma=None
        ))

    return aligned
