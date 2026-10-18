"""
BhashaBridge — Neural Transformer Translation Service
Powered by Facebook's M2M100 (418M parameters) Sequence-to-Sequence model.
Features:
  - 100% Local / Offline Neural Machine Translation (NO cloud LLM APIs).
  - Native support for Marathi ('mr') <-> Hindi ('hi').
  - Robust handling of Roman input (e.g., 'majha naav manas aahe' -> 'माझा नाव मानस आहे').
  - Beam-search neural decoding for fluent, conversational grammar and named entities.
  - In-memory LRU cache for ultra-fast repeat queries.
  - Seamless fallback to calibrated modular translator if needed.
"""

import os
import logging
from typing import Any, Dict, Optional, Tuple
from app.services.base import BaseTranslationService
from app.services.transliteration.service import transliteration_service
from app.services.translation.translator import modular_translator

logger = logging.getLogger("bhashabridge.translation.neural")

class NeuralTransformerTranslator(BaseTranslationService):
    """
    Local Neural Machine Translation Service using M2M100 Transformer.
    """
    MODEL_NAME = "facebook/m2m100_418M"
    LANG_CODE_MAP = {
        "marathi": "mr",
        "hindi": "hi"
    }

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self._is_loaded = False
        self._load_failed = False
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _load_model(self) -> bool:
        if self._is_loaded:
            return True
        if self._load_failed:
            return False

        use_mock = os.getenv("USE_MOCK_MODELS", "false").lower() == "true"
        if use_mock:
            return False

        try:
            import torch
            from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[*] Loading Neural M2M100 model ({self.MODEL_NAME}) onto {self.device}...")
            
            self.tokenizer = M2M100Tokenizer.from_pretrained(self.MODEL_NAME)
            self.model = M2M100ForConditionalGeneration.from_pretrained(self.MODEL_NAME).to(self.device)
            self.model.eval()

            self._is_loaded = True
            logger.info("[*] Neural M2M100 model loaded and ready for inference!")
            return True
        except Exception as e:
            logger.warning(f"[!] Could not load neural model {self.MODEL_NAME}: {e}. Using calibrated fallback.")
            self._load_failed = True
            return False

    def translate(
        self,
        text: str,
        source_language: str = "marathi",
        target_language: str = "hindi",
        script: str = "both"
    ) -> Dict[str, Any]:
        clean_text = text.strip()
        if not clean_text:
            return {
                "source_text": text,
                "source_language": source_language,
                "target_language": target_language,
                "translation": "",
                "translation_native": "",
                "translation_roman": "",
                "english_meaning": ""
            }

        cache_key = f"{source_language.lower()}_{target_language.lower()}_{script}_{clean_text.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Normalize input script: if Latin/Roman script, transliterate to Devanagari first
        is_devanagari = any('\u0900' <= c <= '\u097f' for c in clean_text)
        devanagari_input = clean_text if is_devanagari else transliteration_service.transliterate(
            clean_text, language=source_language, direction="latin_to_devanagari"
        )

        # 2. Attempt Neural Translation
        src_code = self.LANG_CODE_MAP.get(source_language.lower(), "mr")
        tgt_code = self.LANG_CODE_MAP.get(target_language.lower(), "hi")

        if self._load_model() and self.model is not None and self.tokenizer is not None:
            try:
                import torch

                self.tokenizer.src_lang = src_code
                inputs = self.tokenizer(devanagari_input, return_tensors="pt").to(self.device)
                tgt_lang_id = self.tokenizer.get_lang_id(tgt_code)

                with torch.no_grad():
                    generated = self.model.generate(
                        **inputs,
                        forced_bos_token_id=tgt_lang_id,
                        max_length=256,
                        num_beams=4,
                        length_penalty=1.0,
                        early_stopping=True,
                        no_repeat_ngram_size=3
                    )

                native_translation = self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

                # Ensure proper punctuation
                if not native_translation.endswith("।") and not native_translation.endswith("."):
                    native_translation += "।"

                # Linguistic post-processing: Hindi 'kal' is ambiguous (yesterday/tomorrow); Marathi requires 'udya' or 'kaal'
                if target_language.lower() == "marathi" and re.search(r'\bकल\b', native_translation):
                    if any(w in native_translation for w in ["नाही", "आहे", "जाणार", "येणार", "होणार", "करणार", "जायचं"]):
                        native_translation = re.sub(r'\bकल\b', 'उद्या', native_translation)
                    else:
                        native_translation = re.sub(r'\bकल\b', 'काल', native_translation)

                roman_translation = transliteration_service.transliterate(
                    native_translation, language=target_language, direction="devanagari_to_latin"
                )

                english_meaning = modular_translator._generate_english(
                    devanagari_input if source_language == "hindi" else native_translation,
                    native_translation if source_language == "hindi" else devanagari_input
                )

                result = {
                    "source_text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "translation": native_translation if script == "devanagari" else roman_translation,
                    "translation_native": native_translation,
                    "translation_roman": roman_translation,
                    "english_meaning": english_meaning,
                    "model_source": "m2m100-neural-seq2seq-418m"
                }
                self._cache[cache_key] = result
                return result
            except Exception as e:
                logger.error(f"Neural inference exception: {e}")

        # 3. Fallback to calibrated modular translator
        fallback_res = modular_translator.translate(
            text=text,
            source_language=source_language,
            target_language=target_language,
            script=script
        )
        fallback_res["model_source"] = "bhashabridge-calibrated-adapter"
        self._cache[cache_key] = fallback_res
        return fallback_res

neural_transformer_translator = NeuralTransformerTranslator()
