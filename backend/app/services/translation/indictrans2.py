"""
BhashaBridge — IndicTrans2 Translation Adapter
Adheres to Principle 3 (models must be replaceable).
Supports AI4Bharat IndicTrans2 distilled 320M model architecture with lazy-loading,
inference caching, and graceful fallback to the modular conversational engine.
"""

import os
import re
import logging
from typing import Any, Dict, Optional
from app.services.base import BaseTranslationService
from app.services.transliteration.service import transliteration_service
from app.services.translation.translator import modular_translator

logger = logging.getLogger(__name__)

class IndicTrans2Adapter(BaseTranslationService):
    """
    Adapter for AI4Bharat IndicTrans2 multilingual translation model.
    Language tags:
      - Hindi: 'hin_Deva'
      - Marathi: 'mar_Deva'
    """

    LANG_TAG_MAP = {
        "hindi": "hin_Deva",
        "marathi": "mar_Deva"
    }

    def __init__(self, model_checkpoint: Optional[str] = None):
        self.model_checkpoint = model_checkpoint or os.getenv(
            "INDICTRANS2_MODEL_CHECKPOINT", "ai4bharat/indictrans2-indic-indic-dist-320M"
        )
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        self._translation_cache: Dict[str, Dict[str, Any]] = {}

    def _lazy_load_model(self) -> bool:
        """Attempts to load IndicTrans2 weights if explicitly enabled and available."""
        if self.is_loaded and self.model is not None and self.tokenizer is not None:
            return True

        use_mock = os.getenv("USE_MOCK_MODELS", "false").lower() == "true"
        if use_mock:
            return False

        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            token = os.getenv("HF_TOKEN")
            logger.info("Loading IndicTrans2 Tokenizer & Model from %s...", self.model_checkpoint)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                token=token
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_checkpoint,
                trust_remote_code=True,
                token=token
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model.to(device)
            self.model.eval()
            self.is_loaded = True
            logger.info("IndicTrans2 Model successfully loaded on %s", device)
            return True
        except Exception as e:
            logger.error("Failed to load IndicTrans2 model: %s", e)
            self.is_loaded = False
            return False

    KNOWN_NAME_NOUN_AMBIGUITIES = {
        "मानस", "कमल", "प्रकाश", "आनंद", "अमर", "किरण", "शांती", "आरती",
        "सूरज", "विकास", "सत्य", "सुमन", "भावना", "आशा", "तारा", "पवन", "गगन"
    }

    NER_STOP_WORDS = {
        "आहे", "नाही", "होता", "होती", "है", "था", "थी", "का", "की", "के", "एक",
        "नाव", "नांव", "नाम", "माझे", "माझं", "माझा", "माझी", "माझ",
        "मेरा", "मेरी", "मेरे", "मित्र", "दोस्त", "भाऊ", "बहीण", "भाई", "बहन"
    }

    def _shield_proper_names(self, devanagari_text: str, original_raw_text: str = "") -> tuple[str, Dict[str, str]]:
        """
        Shields proper nouns/names from being translated into literal dictionary nouns.
        Uses neutral high-frequency anchor names that IndicTrans2 preserves consistently.
        """
        detected_names = set()
        
        # 1. Regex context patterns for name intros and friend/relative introductions
        patterns = [
            r'(?:माझं|माझे|माझा|माझी)\s+(?:नाव|नांव)\s+([\u0900-\u097F]+)',
            r'(?:मेरा|मेरी|मेरे)\s+(?:नाम)\s+([\u0900-\u097F]+)',
            r'(?:नाव|नांव)\s+([\u0900-\u097F]+)',
            r'(?:नाम)\s+([\u0900-\u097F]+)',
            r'(?:हा|ही|हे)\s+(?:माझा|माझी|माझे)?\s*(?:मित्र|मैत्रीण|भाऊ|बहीण)?\s+([\u0900-\u097F]+)',
            r'(?:यह|ये)\s+(?:मेरा|मेरी|मेरे)?\s*(?:दोस्त|मित्र|भाई|बहन)?\s+([\u0900-\u097F]+)'
        ]
        for p in patterns:
            for m in re.finditer(p, devanagari_text):
                w = m.group(1).strip()
                if w not in self.NER_STOP_WORDS:
                    detected_names.add(w)

        # 2. Check for known noun-name ambiguities
        for word in devanagari_text.split():
            clean_w = re.sub(r'[^\u0900-\u097F]', '', word)
            if clean_w in self.KNOWN_NAME_NOUN_AMBIGUITIES:
                detected_names.add(clean_w)

        # 3. Capitalized Roman tokens if input was Latin
        if original_raw_text:
            cap_tokens = [w for w in re.findall(r'\b[A-Z][a-z]+\b', original_raw_text)]
            for cap in cap_tokens:
                dev_word = transliteration_service.transliterate_word(cap.lower())
                if dev_word in devanagari_text:
                    detected_names.add(dev_word)

        shield_map: Dict[str, str] = {}
        shielded = devanagari_text
        anchor = "रोहित"
        for name in detected_names:
            if name != anchor:
                shield_map[anchor] = name
                shielded = re.sub(rf'\b{re.escape(name)}\b', anchor, shielded)

        return shielded, shield_map

    def _unshield_proper_names(self, text: str, shield_map: Dict[str, str]) -> str:
        """Restores original proper entities into translated text including inflected case suffixes."""
        unshielded = text
        for anchor, original in shield_map.items():
            unshielded = re.sub(rf'\b{re.escape(anchor)}\b', original, unshielded)
            unshielded = unshielded.replace(f"{anchor}ला", f"{original}ला")
            unshielded = unshielded.replace(f"{anchor}चा", f"{original}चा")
            unshielded = unshielded.replace(f"{anchor}ची", f"{original}ची")
            unshielded = unshielded.replace(f"{anchor}चे", f"{original}चे")
            unshielded = unshielded.replace(f"{anchor}को", f"{original}को")
            unshielded = unshielded.replace(f"{anchor}का", f"{original}का")
            unshielded = unshielded.replace(f"{anchor}की", f"{original}की")
            unshielded = unshielded.replace(f"{anchor}के", f"{original}के")
        return unshielded

    def translate(
        self,
        text: str,
        source_language: str = "hindi",
        target_language: str = "marathi",
        script: str = "both"
    ) -> Dict[str, Any]:
        clean_text = text.strip()
        cache_key = f"{source_language}_{target_language}_{script}_{clean_text.lower()}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        # 1. Normalize input script (ensure Devanagari input for neural model)
        is_devanagari = any('\u0900' <= c <= '\u097f' for c in clean_text)
        devanagari_input = clean_text if is_devanagari else transliteration_service.transliterate(
            clean_text, language=source_language, direction="latin_to_devanagari"
        )

        # 2. Attempt IndicTrans2 neural translation with NER shielding
        if self._lazy_load_model() and self.model and self.tokenizer:
            try:
                import torch
                src_tag = self.LANG_TAG_MAP.get(source_language.lower(), "hin_Deva")
                tgt_tag = self.LANG_TAG_MAP.get(target_language.lower(), "mar_Deva")

                # Shield proper names from literal dictionary translation
                shielded_input, shield_map = self._shield_proper_names(devanagari_input, original_raw_text=clean_text)

                # IndicTransTokenizer expects: "{src_lang} {tgt_lang} {text}"
                prompt = f"{src_tag} {tgt_tag} {shielded_input}"
                device = next(self.model.parameters()).device
                inputs = self.tokenizer([prompt], padding="longest", truncation=True, return_tensors="pt").to(device)

                with torch.no_grad():
                    generated_tokens = self.model.generate(
                        **inputs,
                        max_length=128,
                        num_beams=4,
                        use_cache=False
                    )

                decoded = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
                raw_translation = decoded[0].strip() if decoded else ""

                # Unshield entities to restore proper names in the exact target position
                native_translation = self._unshield_proper_names(raw_translation, shield_map)

                if native_translation and not native_translation.endswith("।") and not native_translation.endswith("."):
                    native_translation += "।"

                roman_translation = transliteration_service.transliterate(
                    native_translation, language=target_language, direction="devanagari_to_latin"
                )

                result = {
                    "source_text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "translation": native_translation if script == "devanagari" else roman_translation,
                    "translation_native": native_translation,
                    "translation_roman": roman_translation,
                    "english_meaning": modular_translator._generate_english(
                        devanagari_input if source_language == "hindi" else native_translation,
                        native_translation if source_language == "hindi" else devanagari_input
                    ),
                    "model_source": "indictrans2-320m-neural"
                }
                self._translation_cache[cache_key] = result
                return result
            except Exception as exc:
                logger.warning("IndicTrans2 inference failed, falling back: %s", exc)

        # 3. Fallback to our high-accuracy modular conversational translator
        fallback_res = modular_translator.translate(
            text=clean_text,
            source_language=source_language,
            target_language=target_language,
            script=script
        )
        fallback_res["model_source"] = "bhashabridge-curated-adapter"
        self._translation_cache[cache_key] = fallback_res
        return fallback_res

indictrans2_adapter = IndicTrans2Adapter()
