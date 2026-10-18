"""
BhashaBridge — Bilingual Word & Construction Aligner (M4)
Aligns Hindi and Marathi words/phrases and flags construction-based mappings
vs direct lexical equivalents as strictly required by Section 8 of the product spec.
"""

from typing import List
from app.schemas.analyze import VocabularyItem

# Lexicon of frequent grammatical and conversational alignments
ALIGNMENT_LEXICON = [
    # Pronouns & Case Markers
    {"hi": "मैं", "mr": "मी", "mr_rom": "Mi", "meaning": "I (1st person pronoun)", "pos": "pronoun", "is_construction": False},
    {"hi": "मै", "mr": "मी", "mr_rom": "Mi", "meaning": "I (1st person pronoun)", "pos": "pronoun", "is_construction": False},
    {"hi": "मुझे", "mr": "मला", "mr_rom": "Mala", "meaning": "to me / I (dative subject)", "pos": "pronoun", "is_construction": True},
    {"hi": "तुझे", "mr": "तुला", "mr_rom": "Tula", "meaning": "to you (informal dative)", "pos": "pronoun", "is_construction": True},
    {"hi": "उसे", "mr": "त्याला / तिला", "mr_rom": "Tyala / Tila", "meaning": "to him / her (dative)", "pos": "pronoun", "is_construction": True},
    {"hi": "हमें", "mr": "आम्हाला", "mr_rom": "Aamhala", "meaning": "to us (exclusive dative)", "pos": "pronoun", "is_construction": True},
    {"hi": "आप", "mr": "तुम्ही", "mr_rom": "Tumhi", "meaning": "you (respectful/formal)", "pos": "pronoun", "is_construction": False},
    {"hi": "तुम", "mr": "तू", "mr_rom": "Tu", "meaning": "you (informal singular)", "pos": "pronoun", "is_construction": False},
    {"hi": "मेरा", "mr": "माझा / माझं", "mr_rom": "Mazha", "meaning": "my / mine", "pos": "possessive", "is_construction": False},
    {"hi": "तुम्हारा", "mr": "तुझा / तुझं", "mr_rom": "Tuzha", "meaning": "your / yours", "pos": "possessive", "is_construction": False},
    {"hi": "आपका", "mr": "तुमचा / तुमचं", "mr_rom": "Tumcha", "meaning": "your (honorific)", "pos": "possessive", "is_construction": False},
    {"hi": "नाम", "mr": "नाव", "mr_rom": "Naav", "meaning": "name (neuter noun in Marathi)", "pos": "noun", "is_construction": False},

    # Spatial & Deictic Markers
    {"hi": "वहाँ", "mr": "तिथे", "mr_rom": "tithe", "meaning": "there (adverb of place)", "pos": "adverb", "is_construction": False},
    {"hi": "वहा", "mr": "तिथे", "mr_rom": "tithe", "meaning": "there (adverb of place)", "pos": "adverb", "is_construction": False},
    {"hi": "यहाँ", "mr": "इथे", "mr_rom": "ithe", "meaning": "here (adverb of place)", "pos": "adverb", "is_construction": False},
    {"hi": "यहा", "mr": "इथे", "mr_rom": "ithe", "meaning": "here (adverb of place)", "pos": "adverb", "is_construction": False},

    # Temporal Markers
    {"hi": "कल", "mr": "उद्या", "mr_rom": "udya", "meaning": "tomorrow (unambiguous future)", "pos": "adverb", "is_construction": True},
    {"hi": "आज", "mr": "आज", "mr_rom": "aaj", "meaning": "today", "pos": "adverb", "is_construction": False},
    {"hi": "अब", "mr": "आता", "mr_rom": "aata", "meaning": "now", "pos": "adverb", "is_construction": False},
    {"hi": "सुबह", "mr": "सकाळी", "mr_rom": "sakaali", "meaning": "in the morning", "pos": "adverb", "is_construction": True},
    {"hi": "रात", "mr": "रात्री", "mr_rom": "raatri", "meaning": "at night", "pos": "adverb", "is_construction": True},

    # Destinations & Objects
    {"hi": "कॉलेज", "mr": "कॉलेजला", "mr_rom": "college-la", "meaning": "to college (dative -ला suffix)", "pos": "noun + postposition", "is_construction": True},
    {"hi": "ऑफिस", "mr": "ऑफिसला", "mr_rom": "office-la", "meaning": "to office (dative -ला suffix)", "pos": "noun + postposition", "is_construction": True},
    {"hi": "घर", "mr": "घरी", "mr_rom": "ghari", "meaning": "at home (locative -ी suffix)", "pos": "noun + postposition", "is_construction": True},
    {"hi": "पानी", "mr": "पाणी", "mr_rom": "paani", "meaning": "water (neuter in Marathi)", "pos": "noun", "is_construction": False},
    {"hi": "खाना", "mr": "जेवण", "mr_rom": "jevan", "meaning": "meal / food (neuter in Marathi)", "pos": "noun", "is_construction": False},
    {"hi": "चाय", "mr": "चहा", "mr_rom": "chaha", "meaning": "tea (masculine in Marathi)", "pos": "noun", "is_construction": False},

    # Verb Phrases, Modals & Continuous Aspects
    {"hi": "जा रहा हूँ", "mr": "जात आहे", "mr_rom": "jaat aahe", "meaning": "am going (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "जा रहा हु", "mr": "जात आहे", "mr_rom": "jaat aahe", "meaning": "am going (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "जा रहे हैं", "mr": "जात आहेत", "mr_rom": "jaat ahet", "meaning": "are going (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "जा रहे हो", "mr": "जात आहेस", "mr_rom": "jaat aahes", "meaning": "are going (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "आ रहा हूँ", "mr": "येत आहे", "mr_rom": "yet aahe", "meaning": "am coming (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "कर रहा हूँ", "mr": "करत आहे", "mr_rom": "karat aahe", "meaning": "am doing (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "खा रहा हूँ", "mr": "खात आहे", "mr_rom": "khaat aahe", "meaning": "am eating (present continuous)", "pos": "verb phrase", "is_construction": True},
    {"hi": "जाना है", "mr": "जायचं आहे", "mr_rom": "jaycha aahe", "meaning": "have to go / must go (obligation modal)", "pos": "verb phrase", "is_construction": True},
    {"hi": "सीखनी है", "mr": "शिकायची आहे", "mr_rom": "shikaychi aahe", "meaning": "want to learn (feminine language agreement)", "pos": "verb phrase", "is_construction": True},
    {"hi": "करना है", "mr": "करायचं आहे", "mr_rom": "karaycha aahe", "meaning": "have to do (obligation modal)", "pos": "verb phrase", "is_construction": True},
    {"hi": "चाहिए", "mr": "पाहिजे", "mr_rom": "pahije", "meaning": "want / need", "pos": "modal", "is_construction": True},
    {"hi": "है", "mr": "आहे", "mr_rom": "aahe", "meaning": "is (present auxiliary)", "pos": "auxiliary", "is_construction": False},
    {"hi": "हूँ", "mr": "आहे", "mr_rom": "aahe", "meaning": "am (present auxiliary)", "pos": "auxiliary", "is_construction": False},
    {"hi": "हैं", "mr": "आहेत / आहात", "mr_rom": "ahet / aahat", "meaning": "are (plural / honorific auxiliary)", "pos": "auxiliary", "is_construction": False},
    {"hi": "नहीं", "mr": "नाही", "mr_rom": "nahi", "meaning": "no / not", "pos": "negation", "is_construction": False},

    # Interrogatives & Modifiers
    {"hi": "कहाँ", "mr": "कुठे", "mr_rom": "kuthe", "meaning": "where", "pos": "interrogative", "is_construction": False},
    {"hi": "कब", "mr": "कधी", "mr_rom": "kadhi", "meaning": "when", "pos": "interrogative", "is_construction": False},
    {"hi": "क्या", "mr": "काय", "mr_rom": "kay", "meaning": "what", "pos": "interrogative", "is_construction": False},
    {"hi": "कैसा", "mr": "कसा", "mr_rom": "kasa", "meaning": "how (masculine)", "pos": "interrogative", "is_construction": False},
    {"hi": "कैसी", "mr": "कशी", "mr_rom": "kashi", "meaning": "how (feminine)", "pos": "interrogative", "is_construction": False},
    {"hi": "कैसे", "mr": "कसे", "mr_rom": "kase", "meaning": "how (plural/honorific)", "pos": "interrogative", "is_construction": False},
    {"hi": "बहुत", "mr": "खूप", "mr_rom": "khoop", "meaning": "very / much", "pos": "adverb", "is_construction": False},
    {"hi": "अच्छा", "mr": "छान / चांगला", "mr_rom": "chan / changla", "meaning": "good / nice", "pos": "adjective", "is_construction": False}
]

def align_sentence_vocabulary(source_text: str, target_text: str, source_lang: str = "hindi") -> List[VocabularyItem]:
    """
    Scans source and target texts to produce aligned vocabulary pairs,
    categorizing direct lexical items vs construction-based mappings.
    """
    clean_src = source_text.lower()
    clean_tgt = target_text.lower()

    aligned: List[VocabularyItem] = []
    seen = set()

    for entry in ALIGNMENT_LEXICON:
        hi_term = entry["hi"].lower()
        mr_term = entry["mr"].lower()

        # Check if terms match the respective source and target sentences
        if (hi_term in clean_src or hi_term in clean_tgt) and (mr_term in clean_src or mr_term in clean_tgt or entry["mr_rom"].lower() in clean_tgt):
            key = (entry["mr"].strip(), entry["meaning"])
            if key not in seen:
                seen.add(key)
                src_word = entry["hi"] if source_lang == "hindi" else entry["mr"]
                tgt_word = entry["mr"] if source_lang == "hindi" else entry["hi"]
                tgt_rom = entry["mr_rom"] if source_lang == "hindi" else entry["hi"]

                aligned.append(VocabularyItem(
                    source_word=src_word,
                    target_word=tgt_word,
                    target_roman=tgt_rom,
                    meaning=entry["meaning"],
                    part_of_speech=entry["pos"],
                    is_construction_based=entry["is_construction"]
                ))

    # If no alignments matched, provide safe fallback token item
    if not aligned:
        aligned.append(VocabularyItem(
            source_word=source_text.strip("।."),
            target_word=target_text.strip("।."),
            target_roman=target_text.strip("।."),
            meaning="Sentence-level equivalent expression",
            part_of_speech="phrase",
            is_construction_based=True
        ))

    return aligned
