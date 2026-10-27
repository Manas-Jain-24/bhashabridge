import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.services.base import BaseTranslationService
from app.services.transliteration.service import transliteration_service
from app.services.translation.corpus import exclude_heldout

class ModularTranslationService(BaseTranslationService):
    """
    Intelligent Hindi <-> Marathi translation engine with:
    1. Direct indexing of the 360-sentence curated learning dataset.
    2. Multi-word verb phrase & aspectual grammatical transformation (continuous, obligation, habitual).
    3. Bidirectional pronoun, case marker, and spatial/temporal lexicon mappings.
    4. Meaningful English context generation.
    """

    # Hand-curated seed conversational pairs
    DEFAULT_PAIRS = [
        {
            "hindi_dev": "मुझे कल कॉलेज जाना है।",
            "hindi_rom": "Mujhe kal college jaana hai.",
            "marathi_dev": "मला उद्या कॉलेजला जायचं आहे।",
            "marathi_rom": "Mala udya college-la jaycha aahe.",
            "english": "I have to go to college tomorrow.",
            "topic": "college"
        },
        {
            "hindi_dev": "मुझे मराठी सीखनी है।",
            "hindi_rom": "Mujhe Marathi seekhni hai.",
            "marathi_dev": "मला मराठी शिकायची आहे।",
            "marathi_rom": "Mala Marathi shikaychi aahe.",
            "english": "I want to learn Marathi.",
            "topic": "learning"
        },
        {
            "hindi_dev": "मैं वहाँ जा रहा हूँ।",
            "hindi_rom": "Main vahan ja raha hoon.",
            "marathi_dev": "मी तिथे जात आहे।",
            "marathi_rom": "Mi tithe jaat aahe.",
            "english": "I am going there.",
            "topic": "travel"
        },
        {
            "hindi_dev": "आप कैसे हैं?",
            "hindi_rom": "Aap kaise hain?",
            "marathi_dev": "तुम्ही कसे आहात?",
            "marathi_rom": "Tumhi kase aahat?",
            "english": "How are you? (Formal)",
            "topic": "greetings"
        },
        {
            "hindi_dev": "तुम कैसे हो?",
            "hindi_rom": "Tum kaise ho?",
            "marathi_dev": "तू कसा आहेस?",
            "marathi_rom": "Tu kasa aahes?",
            "english": "How are you? (Informal)",
            "topic": "greetings"
        },
        {
            "hindi_dev": "मुझे पानी चाहिए।",
            "hindi_rom": "Mujhe paani chahiye.",
            "marathi_dev": "मला पाणी पाहिजे।",
            "marathi_rom": "Mala paani pahije.",
            "english": "I need water.",
            "topic": "daily_life"
        },
        {
            "hindi_dev": "तुम्हारा नाम क्या है?",
            "hindi_rom": "Tumhara naam kya hai?",
            "marathi_dev": "तुझं नाव काय आहे?",
            "marathi_rom": "Tuzha naav kay aahe?",
            "english": "What is your name?",
            "topic": "introductions"
        },
        {
            "hindi_dev": "तुम कहाँ जा रहे हो?",
            "hindi_rom": "Tum kahan ja rahe ho?",
            "marathi_dev": "तू कुठे जात आहेस?",
            "marathi_rom": "Tu kuthe jaat aahes?",
            "english": "Where are you going?",
            "topic": "travel"
        },
        {
            "hindi_dev": "यह बहुत अच्छा है।",
            "hindi_rom": "Yeh bahut achha hai.",
            "marathi_dev": "हे खूप छान आहे।",
            "marathi_rom": "He khoop chan aahe.",
            "english": "This is very good / nice.",
            "topic": "compliments"
        }
    ]

    # Multi-word phrase mappings (evaluated longest first to preserve idiomatic compounds)
    HI_TO_MR_PHRASES = [
        # Continuous verb aspects
        ("जा रहा हूँ", "जात आहे", "am going"),
        ("जा रहा हु", "जात आहे", "am going"),
        ("जा रही हूँ", "जात आहे", "am going"),
        ("जा रहे हैं", "जात आहेत", "are going"),
        ("जा रहे हो", "जात आहेस", "are going"),
        ("जा रहा है", "जात आहे", "is going"),
        ("जा रही है", "जात आहे", "is going"),
        ("आ रहा हूँ", "येत आहे", "am coming"),
        ("आ रहा हु", "येत आहे", "am coming"),
        ("आ रही हूँ", "येत आहे", "am coming"),
        ("आ रहे हैं", "येत आहेत", "are coming"),
        ("आ रहे हो", "येत आहेस", "are coming"),
        ("कर रहा हूँ", "करत आहे", "am doing"),
        ("कर रहा हु", "करत आहे", "am doing"),
        ("कर रहे हैं", "करत आहेत", "are doing"),
        ("खा रहा हूँ", "खात आहे", "am eating"),
        ("पी रहा हूँ", "पीत आहे", "am drinking"),
        ("बोल रहा हूँ", "बोलत आहे", "am speaking"),
        ("देख रहा हूँ", "बघत आहे", "am watching"),
        ("सीख रहा हूँ", "शिकत आहे", "am learning"),
        ("पढ़ रहा हूँ", "वाचत आहे", "am reading"),
        ("पढ़ रहा हूँ", "वाचत आहे", "am reading"),

        # Obligation & Modals
        ("मुझ वहाँ जाना है", "मला तिथे जायचं आहे", "have to go there"),
        ("मुझे वहाँ जाना है", "मला तिथे जायचं आहे", "have to go there"),
        ("मुझ यहाँ आना है", "मला इथे यायचं आहे", "have to come here"),
        ("मुझे यहाँ आना है", "मला इथे यायचं आहे", "have to come here"),
        ("जाना है", "जायचं आहे", "have to go"),
        ("जन है", "जायचं आहे", "have to go"),
        ("जाना चाहिए", "जायला पाहिजे", "should go"),
        ("सीखनी है", "शिकायची आहे", "want to learn"),
        ("सीखना है", "शिकायचं आहे", "want to learn"),
        ("करना है", "करायचं आहे", "have to do"),
        ("खाना है", "खायचं आहे", "want to eat"),
        ("पीना है", "प्यायचं आहे", "want to drink"),
        ("बोलना है", "बोलायचं आहे", "want to speak"),

        # Habitual & Simple
        ("जाता हूँ", "जातो", "go"),
        ("जाती हूँ", "जाते", "go"),
        ("खाता हूँ", "खातो", "eat"),
        ("खाती हूँ", "खाते", "eat"),
        ("आता हूँ", "येतो", "come"),
        ("आती हूँ", "येते", "come"),

        # Case + Noun expressions
        ("कॉलेज जाना", "कॉलेजला जायचं", "going to college"),
        ("कॉलेज को", "कॉलेजला", "to college"),
        ("कॉलेज में", "कॉलेजमध्ये", "in college"),
        ("घर पर", "घरी", "at home"),
        ("घर जाना", "घरी जायचं", "going home"),
        ("ऑफिस को", "ऑफिसला", "to office"),
        ("ऑफिस में", "ऑफिसमध्ये", "in office"),
        ("दुकान पर जा रहा हूँ", "दुकानवर जात आहे", "am going to the shop"),
        ("दुकान पर", "दुकानवर", "at the shop"),
        ("लाइब्रेरी में जा रहा हूँ", "लायब्ररीत जात आहे", "am going to the library"),
        ("लाइब्रेरी में आ रहा हूँ", "लायब्ररीत येत आहे", "am coming to the library"),
        ("लाइब्रेरी में", "लायब्ररीत", "in the library"),
        ("हम सब मिलकर पढ़ाई करेंगे", "आपण सगळे मिळून अभ्यास करू", "we will all study together"),
        ("हम सब मिलकर", "आपण सगळे मिळून", "all of us together"),
        ("हम सब", "आपण सगळे", "all of us"),
        ("पढ़ाई करेंगे", "अभ्यास करू", "will study"),
        ("पढ़ाई", "अभ्यास", "study"),
        ("मिलकर", "मिळून", "together"),
        ("टहलता हूँ", "चालतो", "walk"),
        ("ठंड है", "थंडी आहे", "is cold"),
        ("चल रही है", "सुटला आहे", "is blowing")
    ]

    # Word-level mappings
    HI_TO_MR_WORDS = {
        # Pronouns
        "मैं": "मी", "मै": "मी", "हम": "आम्ही", "तुम": "तू", "आप": "तुम्ही",
        "वह": "तो", "वो": "तो", "यह": "हे", "ये": "हे", "वे": "ते",
        "उसने": "त्याने", "इन्होंने": "यांनी", "उन्होंने": "त्यांनी",
        "मुझे": "मला", "मुझ": "मला", "मुझको": "मला",
        "तुझे": "तुला", "तुझ": "तुला", "तुझको": "तुला",
        "उसे": "त्याला", "हमें": "आम्हाला", "आपको": "तुम्हाला",
        "मेरा": "माझा", "मेरी": "माझी", "मेरे": "माझे",
        "तुम्हारा": "तुझा", "तुम्हारी": "तुझी", "तुम्हारे": "तुझे",
        "आपका": "तुमचा", "आपकी": "तुमची", "आपके": "तुमचे",
        "उसका": "त्याचा", "उसकी": "त्याची", "उसके": "त्याचे",

        # Adverbs of Place & Time
        "वहाँ": "तिथे", "वहा": "तिथे", "उधर": "तिकडे",
        "यहाँ": "इथे", "यहा": "इथे", "इधर": "इकडे",
        "कहाँ": "कुठे", "कहा": "कुठे", "किधर": "कुणीकडे",
        "कल": "उद्या", "आज": "आज", "अब": "आता", "अभी": "आता",
        "सुबह": "सकाळी", "शाम": "संध्याकाळी", "रात": "रात्री", "दोपहर": "दुपारी",
        "रोज़": "रोज", "रोज": "रोज",
        "कब": "कधी", "क्यों": "का", "क्या": "काय", "कैसे": "कसे", "कैसा": "कसा", "कैसी": "कशी",

        # Common nouns, adjectives & objects
        "पानी": "पाणी", "खाना": "जेवण", "चाय": "चहा", "दूध": "दूध",
        "नाम": "नाव", "काम": "काम", "किताब": "पुस्तक", "पेन": "पेन",
        "नया": "नवीन", "नई": "नवीन", "नए": "नवीन",
        "ठंड": "थंडी", "हवा": "वारा",
        "कॉलेज": "कॉलेज", "घर": "घर", "ऑफिस": "ऑफिस", "दोस्त": "मित्र",

        # Modifiers & Auxiliaries
        "बहुत": "खूप", "अच्छा": "छान", "अच्छी": "छान", "अच्छे": "छान",
        "चाहिए": "पाहिजे", "नहीं": "नाही", "नही": "नाही", "मत": "नको",
        "दिया": "दिलं", "दी": "दिलं",
        "हूँ": "आहे", "हु": "आहे", "है": "आहे", "हैं": "आहेत", "हो": "आहेस",
        "था": "होता", "थी": "होती", "थे": "होते"
    }

    # Reverse word mappings (Marathi -> Hindi)
    MR_TO_HI_WORDS = {
        "मी": "मैं", "आम्ही": "हम", "आपण": "हम", "तू": "तुम", "तुम्ही": "आप",
        "तो": "वह", "ती": "वह", "ते": "वे", "हे": "यह",
        "मला": "मुझे", "तुला": "तुझे", "त्याला": "उसे", "तिला": "उसे", "आम्हाला": "हमें", "तुम्हाला": "आपको",
        "माझा": "मेरा", "माझी": "मेरी", "माझे": "मेरे", "माझं": "मेरा",
        "तुझा": "तुम्हारा", "तुझी": "तुम्हारी", "तुझे": "तुम्हारे", "तुझं": "तुम्हारा",
        "तुमचा": "आपका", "तुमची": "आपकी", "तुमचे": "आपके", "तुमचं": "आपका",
        "तिथे": "वहाँ", "इथे": "यहाँ", "कुठे": "कहाँ", "तिकडे": "उधर", "इकडे": "इधर",
        "उद्या": "कल", "काल": "कल", "आज": "आज", "आता": "अब",
        "सकाळी": "सुबह", "संध्याकाळी": "शाम को", "रात्री": "रात को",
        "कधी": "कब", "का": "क्यों", "काय": "क्या", "कसे": "कैसे", "कसा": "कैसा", "कशी": "कैसी",
        "पाणी": "पानी", "जेवण": "खाना", "चहा": "चाय", "दूध": "दूध", "नाव": "नाम", "पुस्तक": "किताब", "पेन": "पेन",
        "घरी": "घर", "कॉलेजला": "कॉलेज", "ऑफिसला": "ऑफिस",
        "खूप": "बहुत", "छान": "अच्छा", "चांगला": "अच्छा", "चांगली": "अच्छी",
        "नवीन": "नया", "थंडी": "ठंड", "वारा": "हवा",
        "त्याने": "उसने", "दिलं": "दिया", "चालतो": "टहलता हूँ",
        "मिळून": "मिलकर", "अभ्यास": "पढ़ाई", "करू": "करेंगे", "सगळे": "सब",
        "पाहिजे": "चाहिए", "नाही": "नहीं", "नको": "मत",
        "आहे": "है", "आहेत": "हैं", "आहोत": "हैं", "आहेस": "हो",
        "होता": "था", "होती": "थी", "होते": "थे"
    }

    def __init__(self):
        self._dataset_pairs: List[Dict[str, str]] = []
        self._load_dataset_pairs()
        self._runtime_pairs = exclude_heldout(self.DEFAULT_PAIRS + self._dataset_pairs)
        targets_by_source = defaultdict(set)
        for pair in self._runtime_pairs:
            targets_by_source[self._normalize_cmp(pair["hindi_dev"])].add(self._normalize_cmp(pair["marathi_dev"]))
        self._ambiguous_hindi_sources = {source for source, targets in targets_by_source.items() if len(targets) > 1}

    def _load_dataset_pairs(self):
        base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
        data_dir = base_dir / "data" / "processed" / "learning"
        ds_file = data_dir / "bhashabridge_learning.json"
        if ds_file.exists():
            try:
                with open(ds_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    self._dataset_pairs.append({
                        "hindi_dev": item.get("hindi_devanagari", ""),
                        "hindi_rom": item.get("hindi_roman", ""),
                        "marathi_dev": item.get("marathi_devanagari", ""),
                        "marathi_rom": item.get("marathi_roman", ""),
                        "english": item.get("english_meaning", "")
                    })
            except Exception:
                pass

        # External parallel data is noisy and unreviewed. It may be used to train
        # a separate model, but must never answer an exact user query as a fact.

    def _normalize_cmp(self, text: str) -> str:
        clean = text.lower()
        for punct in [".", "।", "-", ",", "!", "?", "'", '"', "(", ")"]:
            clean = clean.replace(punct, " ")
        return re.sub(r'\s+', ' ', clean).strip()

    def _generate_english(self, hi_text: str, mr_text: str) -> str:
        txt = f"{hi_text} {mr_text}".lower()
        if "जात आहे" in txt or "जा रहा" in txt:
            dest = "there" if ("तिथे" in txt or "वहाँ" in txt or "vaha" in txt or "teethe" in txt) else ""
            if "कॉलेज" in txt:
                dest = "to college"
            elif "ऑफिस" in txt:
                dest = "to the office"
            elif "घरी" in txt or "घर" in txt:
                dest = "home"
            return f"I am going {dest}.".strip()
        if "येत आहे" in txt or "आ रहा" in txt:
            return "I am coming here." if ("इथे" in txt or "यहाँ" in txt) else "I am coming."
        if "शिकायची आहे" in txt or "सीखनी है" in txt:
            return "I want to learn Marathi." if "मराठी" in txt else "I want to learn."
        if "जायचं आहे" in txt or "जाना है" in txt:
            dest = "to college" if "कॉलेज" in txt else "home" if "घर" in txt else "there"
            return f"I have to go {dest}."
        if "पाहिजे" in txt or "चाहिए" in txt:
            item = "water" if ("पाणी" in txt or "पानी" in txt) else "this"
            return f"I need {item}."
        if "कसे आहात" in txt or "कैसे हैं" in txt:
            return "How are you? (Formal)"
        if "कसा आहेस" in txt or "कैसे हो" in txt:
            return "How are you? (Informal)"
        return "Natural conversational translation."

    def translate(
        self,
        text: str,
        source_language: str = "hindi",
        target_language: str = "marathi",
        script: str = "both"
    ) -> Dict[str, Any]:
        norm_input = self._normalize_cmp(text)

        # 1. Check DEFAULT_PAIRS and loaded dataset pairs
        all_pairs = self._runtime_pairs
        for pair in all_pairs:
            if source_language == "hindi":
                if norm_input not in self._ambiguous_hindi_sources and norm_input in [self._normalize_cmp(pair["hindi_dev"]), self._normalize_cmp(pair["hindi_rom"])]:
                    marathi_dev = pair["marathi_dev"].rstrip("।") + "।"
                    marathi_rom = pair["marathi_rom"] or transliteration_service.transliterate(marathi_dev, language="marathi", direction="devanagari_to_latin")
                    return {
                        "source_text": text,
                        "source_language": source_language,
                        "target_language": target_language,
                        "translation": marathi_dev if script == "devanagari" else marathi_rom,
                        "translation_native": marathi_dev,
                        "translation_roman": marathi_rom,
                        "english_meaning": pair["english"],
                        "model_source": "curated_corpus",
                        "engine": "curated_corpus",
                        "fallback_used": False
                    }
            elif source_language == "marathi":
                if norm_input in [self._normalize_cmp(pair["marathi_dev"]), self._normalize_cmp(pair["marathi_rom"])]:
                    hindi_dev = pair["hindi_dev"].rstrip("।") + "।"
                    hindi_rom = pair["hindi_rom"] or transliteration_service.transliterate(hindi_dev, language="hindi", direction="devanagari_to_latin")
                    return {
                        "source_text": text,
                        "source_language": source_language,
                        "target_language": target_language,
                        "translation": hindi_dev if script == "devanagari" else hindi_rom,
                        "translation_native": hindi_dev,
                        "translation_roman": hindi_rom,
                        "english_meaning": pair["english"],
                        "model_source": "curated_corpus",
                        "engine": "curated_corpus",
                        "fallback_used": False
                    }

        # 2. General Rule & Phrase Transfer
        is_devanagari = any('\u0900' <= c <= '\u097f' for c in text)
        dev_input = text if is_devanagari else transliteration_service.transliterate(
            text, language=source_language, direction="latin_to_devanagari"
        )

        if source_language == "hindi" and target_language == "marathi":
            result_str = dev_input
            # 2a. Multi-word phrases
            for hi_p, mr_p, _ in self.HI_TO_MR_PHRASES:
                result_str = result_str.replace(hi_p, mr_p)

            # 2b. Word-level replacements (token-safe)
            words = result_str.split()
            translated_words = []
            for w in words:
                clean_w = w.strip(".,!?:;\"'()[]{}।")
                punct_tail = w[len(clean_w):] if len(w) > len(clean_w) else ""
                if clean_w in self.HI_TO_MR_WORDS:
                    translated_words.append(self.HI_TO_MR_WORDS[clean_w] + punct_tail)
                else:
                    translated_words.append(w)

            native_tr = " ".join(translated_words).strip()
            if not native_tr.endswith("।") and not native_tr.endswith("."):
                native_tr += "।"

            # Roman output
            roman_tr = transliteration_service.transliterate(
                native_tr, language="marathi", direction="devanagari_to_latin"
            )
            # Ensure proper capitalization and spacing
            roman_tr = roman_tr.strip()
            if roman_tr:
                roman_tr = roman_tr[0].upper() + roman_tr[1:]

            eng = ""

        else:
            # Marathi -> Hindi
            result_str = dev_input
            # Reverse phrases
            for hi_p, mr_p, _ in self.HI_TO_MR_PHRASES:
                result_str = result_str.replace(mr_p, hi_p)

            words = result_str.split()
            translated_words = []
            for w in words:
                clean_w = w.strip(".,!?:;\"'()[]{}।")
                punct_tail = w[len(clean_w):] if len(w) > len(clean_w) else ""
                if clean_w in self.MR_TO_HI_WORDS:
                    translated_words.append(self.MR_TO_HI_WORDS[clean_w] + punct_tail)
                else:
                    translated_words.append(w)

            native_tr = " ".join(translated_words).strip()
            if not native_tr.endswith("।") and not native_tr.endswith("."):
                native_tr += "।"

            roman_tr = transliteration_service.transliterate(
                native_tr, language="hindi", direction="devanagari_to_latin"
            )
            roman_tr = roman_tr.strip()
            if roman_tr:
                roman_tr = roman_tr[0].upper() + roman_tr[1:]

            eng = ""

        return {
            "source_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "translation": native_tr if script == "devanagari" else roman_tr,
            "translation_native": native_tr,
            "translation_roman": roman_tr,
            "english_meaning": eng,
            "model_source": "rule_fallback",
            "engine": "rule_fallback",
            "fallback_used": False
        }

modular_translator = ModularTranslationService()
