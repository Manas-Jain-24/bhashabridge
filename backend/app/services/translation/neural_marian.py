"""
BhashaBridge — Neural MarianMT Translation Adapter
Uses pre-trained pure sequence-to-sequence Transformer models:
  - Marathi -> Hindi: Helsinki-NLP/opus-mt-mr-hi (~70M parameters)
  - Hindi -> Marathi: Helsinki-NLP/opus-mt-hi-mr (~70M parameters)
No hardcoded dictionary lookups — translates generalized grammar, names, and conversational context purely through neural attention.
"""

import os
import logging
from typing import Any, Dict, Optional, Tuple
from app.services.base import BaseTranslationService
from app.services.transliteration.service import transliteration_service
from app.services.translation.translator import modular_translator

logger = logging.getLogger("bhashabridge.translation.neural")

class MarianNeuralTranslator(BaseTranslationService):
    MODEL_MAP = {
        ("marathi", "hindi"): "Helsinki-NLP/opus-mt-mr-hi",
        ("hindi", "marathi"): "Helsinki-NLP/opus-mt-hi-mr"
    }

    def __init__(self):
        self.models: Dict[Tuple[str, str], Any] = {}
        self.tokenizers: Dict[Tuple[str, str], Any] = {}
        self.device = "cpu"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_failed: Dict[Tuple[str, str], bool] = {}

    def _get_model_and_tokenizer(self, src: str, tgt: str):
        key = (src.lower(), tgt.lower())
        if key in self.models:
            return self.models[key], self.tokenizers[key]

        if self._load_failed.get(key, False):
            return None, None

        model_name = self.MODEL_MAP.get(key)
        if not model_name:
            return None, None

        try:
            import torch
            from transformers import MarianMTModel, MarianTokenizer

            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[*] Loading neural translation model: {model_name} onto {self.device}...")
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name).to(self.device)
            model.eval()

            self.models[key] = model
            self.tokenizers[key] = tokenizer
            logger.info(f"[*] Neural model {model_name} loaded successfully!")
            return model, tokenizer
        except Exception as e:
            logger.warning(f"[!] Could not load neural model {model_name}: {e}. Using calibrated conversational fallback.")
            self._load_failed[key] = True
            return None, None

    def translate(
        self,
        text: str,
        source_language: str = "hindi",
        target_language: str = "marathi",
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

        cache_key = f"{source_language}_{target_language}_{script}_{clean_text.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Normalize input to Devanagari script for neural model if user typed in Roman/Latin
        is_devanagari = any('\u0900' <= c <= '\u097f' for c in clean_text)
        devanagari_input = clean_text if is_devanagari else transliteration_service.transliterate(
            clean_text, language=source_language, direction="latin_to_devanagari"
        )

        # 2. Attempt Pure Neural Translation (MarianMT 70M)
        model, tokenizer = self._get_model_and_tokenizer(source_language, target_language)
        if model is not None and tokenizer is not None:
            try:
                import torch
                inputs = tokenizer(devanagari_input, return_tensors="pt", padding=True).to(self.device)
                with torch.no_grad():
                    translated_tokens = model.generate(
                        **inputs,
                        max_length=256,
                        num_beams=4,
                        length_penalty=1.0,
                        early_stopping=True,
                        no_repeat_ngram_size=3
                    )
                native_translation = tokenizer.decode(translated_tokens[0], skip_special_tokens=True).strip()

                if not native_translation.endswith("।") and not native_translation.endswith("."):
                    native_translation += "।"

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
                    "model_source": "marian-nmt-70m-neural"
                }
                self._cache[cache_key] = result
                return result
            except Exception as e:
                logger.error(f"Neural inference error: {e}")

        # 3. Fallback to calibrated modular engine
        fallback_res = modular_translator.translate(
            text=text,
            source_language=source_language,
            target_language=target_language,
            script=script
        )
        fallback_res["model_source"] = "bhashabridge-calibrated-adapter"
        self._cache[cache_key] = fallback_res
        return fallback_res

neural_marian_translator = MarianNeuralTranslator()
