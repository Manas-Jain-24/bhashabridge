from fastapi import HTTPException
from app.core.languages import LANGUAGES, has_native, rule_pair, validate_language
"""
BhashaBridge — IndicTrans2 Translation Adapter
Adheres to Principle 3 (models must be replaceable).
Supports AI4Bharat IndicTrans2 distilled 320M model architecture with lazy-loading,
thread-safe circuit breaker, bounded LRU cache, and collision-free entity shielding.
"""

import os
import re
import logging
import threading
from contextlib import nullcontext
from collections import OrderedDict
from typing import Any, Dict, Optional, Tuple, Set
from app.services.base import BaseTranslationService
from app.services.transliteration.service import transliteration_service
from app.services.translation.translator import modular_translator
from app.core.config import settings
from app.services.translation.punctuation import finish_native_sentence
from app.services.translation.generation import generate_next_token_scores,GENERATION_SETTINGS,validate_native_output

logger = logging.getLogger(__name__)

class IndicTrans2Adapter(BaseTranslationService):
    """
    Adapter for AI4Bharat IndicTrans2 multilingual translation model.
    Language tags:
      - Hindi: 'hin_Deva'
      - Marathi: 'mar_Deva'
    """

    LANG_TAG_MAP = {
        **{name: spec["flores"] for name, spec in LANGUAGES.items()}
    }

    # Common proper noun ambiguities where dictionary translation causes errors
    KNOWN_NAME_NOUN_AMBIGUITIES = {
        "आनंद", "अनंत", "कमल", "विकास", "विजय", "आकाश", "सूरज", "प्रिया", "पूजा", "आरती",
        "अमित", "रोहन", "स्नेहा", "राहुल", "दीपक", "नेहा", "संजय", "सचिन",
        "अंजली", "सुरेश", "रमेश", "कविता", "मनीष", "किरण", "अजय", "सुनीता", "प्रमोद", "सारिका"
    }

    # Stop words that should NOT be shielded even if following "माझे नाव" etc.
    NER_STOP_WORDS = {
        "नाव", "नांव", "नाम", "माझे", "माझं", "माझा", "माझी", "माझ",
        "मेरा", "मेरी", "मेरे", "मित्र", "दोस्त", "भाऊ", "बहीण", "भाई", "बहन"
    }

    # Extended anchor names pool
    ANCHOR_NAMES = [
        "रोहित", "सुरेश", "अमित", "पूजा", "प्रिया", "अनिल", "राहुल", "दीपक", "नेहा", "संजय",
        "विकास", "अंजली", "मनीष", "किरण", "अजय", "सुनीता", "प्रमोद", "सारिका", "नितिन", "शीतल",
        "मनोज", "विद्या", "राजेश", "सीमा", "सचिन", "अमृता", "प्रशांत", "स्वाती", "विक्रम", "कविता"
    ]

    def __init__(self, model_checkpoint: Optional[str] = None, cpu_dtype: str = 'float32', stream_weights: bool = False, allow_adapters: bool = True):
        if cpu_dtype not in ('float32','float16','bfloat16'):
            raise ValueError('Unsupported CPU inference dtype')
        self.cpu_dtype = cpu_dtype
        self.stream_weights = stream_weights
        self.allow_adapters = allow_adapters
        self.adapter_sha256 = None
        self.model_checkpoint = model_checkpoint or settings.INDICTRANS2_MODEL_CHECKPOINT
        self.tokenizer = None
        self.model = None
        self.processor = None
        self.is_loaded = False
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self._cache_lock = threading.Lock()
        self._load_failed = False
        self._load_attempted = False
        self.max_cache_size = int(os.getenv("TRANSLATION_CACHE_MAX_SIZE", "1000"))
        self._translation_cache: OrderedDict[Tuple[str,str,str,str], Dict[str, Any]] = OrderedDict()

    def _lazy_load_model(self, force_retry: bool = False) -> bool:
        """
        Attempts to load IndicTrans2 weights with thread safety and a circuit breaker.
        Once an attempt fails, subsequent requests route directly to the modular fallback
        without repeating expensive model imports or network/disk checks unless explicit
        retry is requested.
        """
        if self.is_loaded and self.model is not None and self.tokenizer is not None and self.processor is not None:
            return True

        explicit_retry = force_retry or os.getenv("INDICTRANS2_RETRY_ON_FAILURE", "false").lower() == "true"
        if self._load_failed and not explicit_retry:
            return False

        use_mock = settings.USE_MOCK_MODELS or settings.TESTING
        if use_mock:
            self._load_failed = True
            return False

        with self._load_lock:
            if self.is_loaded and self.model is not None and self.tokenizer is not None and self.processor is not None:
                return True
            if self._load_failed and not explicit_retry:
                return False

            self._load_attempted = True
            try:
                import torch
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                try:
                    from IndicTransToolkit.processor import IndicProcessor
                except ImportError:
                    from app.services.translation.indic_processor import HindiMarathiProcessor as IndicProcessor
                logger.info("Attempting to load IndicTrans2 model from %s", self.model_checkpoint)

                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_checkpoint,
                    trust_remote_code=True
                )
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if device=='cpu' and self.stream_weights:
                    from app.services.translation.low_memory import load_streamed
                    self.model=load_streamed(self.model_checkpoint,getattr(torch,self.cpu_dtype))
                else:
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        self.model_checkpoint, trust_remote_code=True,
                        dtype=torch.float16 if device == "cuda" else getattr(torch,self.cpu_dtype), low_cpu_mem_usage=True)
                self.model.to(device)
                self.model.eval()
                decision=settings.INDICTRANS2_ADAPTER_DECISION if self.allow_adapters else None
                if decision:
                    adapter_load_started=False
                    try:
                        from app.services.translation.adapter_artifact import validated_artifact
                        from peft import PeftModel
                        path,digest=validated_artifact(decision,self.model_checkpoint,getattr(self.model.config,'_commit_hash',None))
                        adapter_load_started=True
                        self.model=PeftModel.from_pretrained(self.model,path,is_trainable=False)
                        self.model.eval(); self.adapter_sha256=digest
                        logger.info('Validated Bengali-Marathi adapter loaded (%s)',digest[:12])
                    except Exception as exc:
                        # PEFT can modify modules before an exception. Do not
                        # advertise a partially modified model as clean base weights.
                        if adapter_load_started: raise
                        logger.warning('Optional adapter unavailable (%s); using base weights',type(exc).__name__)
                self.processor = IndicProcessor(inference=True)
                self.is_loaded = True
                self._load_failed = False
                logger.info("IndicTrans2 model loaded successfully.")
                return True
            except Exception as e:
                logger.warning(
                    "IndicTrans2 load failed (%s). Circuit breaker active; routing to modular conversational engine.",
                    e.__class__.__name__
                )
                self.is_loaded = False
                self._load_failed = True
                return False

    def _adapter_context(self, source_language, target_language):
        if self.adapter_sha256 and (source_language,target_language)!=('bengali','marathi'):
            return self.model.disable_adapter()
        return nullcontext()

    def translate_native_batch(self, texts, source_language, target_language):
        """Native-script neural inference for offline benchmarks (no memory overrides)."""
        import torch
        validate_language(source_language); validate_language(target_language)
        if source_language == target_language:
            raise ValueError("Choose distinct languages")
        if not texts:
            return []
        if not self._lazy_load_model():
            raise RuntimeError("IndicTrans2 is unavailable; benchmark fallback is forbidden")
        shielded = [self._shield_proper_names(t) if rule_pair(source_language, target_language) else (t, {}) for t in texts]
        with self._inference_lock, self._adapter_context(source_language,target_language):
            prepared = self.processor.preprocess_batch([t for t, _ in shielded], src_lang=self.LANG_TAG_MAP[source_language], tgt_lang=self.LANG_TAG_MAP[target_language])
            device = next(self.model.parameters()).device
            inputs = self.tokenizer(prepared, padding="longest", truncation=True, return_tensors="pt", return_attention_mask=True).to(device)
            with torch.inference_mode():
                generated = generate_next_token_scores(self.model,**inputs,**GENERATION_SETTINGS)
            decoded = self.tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=True)
            outputs = self.processor.postprocess_batch(decoded, lang=self.LANG_TAG_MAP[target_language])
        results = []
        for output, (_, mapping), original in zip(outputs, shielded, texts):
            native = self._unshield_proper_names(output.strip(), mapping)
            if not native:
                raise ValueError("IndicTrans2 returned an empty translation")
            native=finish_native_sentence(validate_native_output(native, original))
            results.append(native)
        if len(results) != len(texts):
            raise ValueError("IndicTrans2 returned an incomplete batch")
        return results

    def _get_unique_anchor(self, idx: int, text: str, used_anchors: Set[str]) -> str:
        """Selects or generates a collision-free anchor name that does not exist in text."""
        if idx < len(self.ANCHOR_NAMES):
            cand = self.ANCHOR_NAMES[idx]
            if cand not in text and cand not in used_anchors:
                return cand
        # Generate collision-free unique placeholder
        counter = idx + 1
        while True:
            cand = f"नामधारक{counter}"
            if cand not in text and cand not in used_anchors:
                return cand
            counter += 1

    def _shield_proper_names(self, devanagari_text: str, original_raw_text: str = "") -> Tuple[str, Dict[str, str]]:
        """
        Shields proper nouns/names from being translated into literal dictionary nouns.
        Uses collision-free generated placeholders/anchors supporting unlimited names.
        """
        detected_names = set()

        # 1. Regex context patterns for name intros and friend/relative introductions
        patterns = [
            r'(?:माझं|माझे|माझा|माझी)\s+(?:नाव|नांव)\s+([ऀ-ॿ]+)',
            r'(?:मेरा|मेरी|मेरे)\s+(?:नाम)\s+([ऀ-ॿ]+)',
            r'(?:नाव|नांव)\s+([ऀ-ॿ]+)',
            r'(?:नाम)\s+([ऀ-ॿ]+)',
            r'(?:हा|ही|हे)\s+(?:माझा|माझी|माझे)?\s*(?:मित्र|मैत्रीण|भाऊ|बहीण)?\s+([ऀ-ॿ]+)',
            r'(?:यह|ये)\s+(?:मेरा|मेरी|मेरे)?\s*(?:दोस्त|मित्र|भाई|बहन)?\s+([ऀ-ॿ]+)'
        ]
        for p in patterns:
            for m in re.finditer(p, devanagari_text):
                w = m.group(1).strip()
                if w not in self.NER_STOP_WORDS:
                    detected_names.add(w)

        # 2. Check for known noun-name ambiguities
        for word in devanagari_text.split():
            clean_w = re.sub(r'[^ऀ-ॿ]', '', word)
            if clean_w in self.KNOWN_NAME_NOUN_AMBIGUITIES:
                detected_names.add(clean_w)

        # 3. Capitalized Roman tokens if input was Latin
        if original_raw_text:
            cap_tokens = [w for w in re.findall(r'\b[A-Z][a-z]+\b', original_raw_text)]
            for cap in cap_tokens:
                dev_word = transliteration_service.transliterate(cap.lower(), direction="latin_to_devanagari")
                if dev_word in devanagari_text:
                    detected_names.add(dev_word)

        shield_map: Dict[str, str] = {}
        shielded = devanagari_text
        used_anchors: Set[str] = set()

        # Sort names by length descending to shield compound names first
        for idx, name in enumerate(sorted(detected_names, key=len, reverse=True)):
            anchor = self._get_unique_anchor(idx, devanagari_text, used_anchors)
            used_anchors.add(anchor)
            shield_map[anchor] = name
            # Use Devanagari character lookahead/lookbehind for exact word boundary
            pattern = rf'(?<![ऀ-ॿ]){re.escape(name)}(?![ऀ-ॿ])'
            shielded = re.sub(pattern, anchor, shielded)

        return shielded, shield_map

    def _unshield_proper_names(self, text: str, shield_map: Dict[str, str]) -> str:
        """Restores original proper entities into translated text including inflected case suffixes."""
        unshielded = text
        for anchor, original in sorted(shield_map.items(), key=lambda item: len(item[0]), reverse=True):
            for suffix in ["च्या", "ला", "चा", "ची", "चे", "ने", "शी", "हून", "वरून", "को", "का", "की", "के", "से", "में", "पर"]:
                unshielded = unshielded.replace(f"{anchor}{suffix}", f"{original}{suffix}")
            pattern = rf'(?<![ऀ-ॿ]){re.escape(anchor)}(?![ऀ-ॿ])'
            unshielded = re.sub(pattern, original, unshielded)
        return unshielded

    def translate(
        self,
        text: str,
        source_language: str = "hindi",
        target_language: str = "marathi",
        script: str = "both"
    ) -> Dict[str, Any]:
        validate_language(source_language)
        validate_language(target_language)
        clean_text = text.strip()
        cache_key = (source_language,target_language,script,clean_text)
        with self._cache_lock:
            if cache_key in self._translation_cache:
                res = dict(self._translation_cache[cache_key])
                res["source_text"] = text
                self._translation_cache.move_to_end(cache_key)
                return res

        # 1. Normalize input script (ensure Devanagari input for neural model)
        is_devanagari = has_native(clean_text, source_language)
        devanagari_input = transliteration_service.transliterate(
            clean_text, language=source_language, direction="latin_to_devanagari"
        )

        # 2. Attempt IndicTrans2 neural translation with NER shielding
        if self._lazy_load_model() and self.model and self.tokenizer and self.processor:
            try:
                import torch
                src_tag = self.LANG_TAG_MAP[source_language]
                tgt_tag = self.LANG_TAG_MAP[target_language]

                # Shield proper names from literal dictionary translation
                shielded_input, shield_map = (self._shield_proper_names(devanagari_input, original_raw_text=clean_text)
                                               if rule_pair(source_language, target_language) else (devanagari_input, {}))

                with self._inference_lock, self._adapter_context(source_language,target_language):
                    prepared = self.processor.preprocess_batch(
                        [shielded_input], src_lang=src_tag, tgt_lang=tgt_tag
                    )
                    device = next(self.model.parameters()).device
                    inputs = self.tokenizer(prepared, padding="longest", truncation=True,
                                            return_tensors="pt", return_attention_mask=True).to(device)

                    with torch.no_grad():
                        generated_tokens = generate_next_token_scores(self.model,
                            **inputs,
                            **GENERATION_SETTINGS
                        )

                    decoded = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True,
                                                          clean_up_tokenization_spaces=True)
                    processed = self.processor.postprocess_batch(decoded, lang=tgt_tag)
                raw_translation = processed[0].strip() if processed else ""
                if not raw_translation:
                    raise ValueError("IndicTrans2 returned an empty translation")

                # Unshield entities to restore proper names in the exact target position
                native_translation = self._unshield_proper_names(raw_translation, shield_map)

                native_translation=finish_native_sentence(validate_native_output(native_translation,clean_text))

                roman_translation = transliteration_service.transliterate(
                    native_translation, language=target_language, direction="devanagari_to_latin"
                )

                result = {
                    "source_text": text,
                    "source_language": source_language,
                    "target_language": target_language,
                    "translation": native_translation if script in ("native", "devanagari") else roman_translation,
                    "translation_native": native_translation,
                    "translation_roman": roman_translation,
                    "english_meaning": "",
                    "model_source": "indictrans2-320m-neural+lora" if self.adapter_sha256 and (source_language,target_language)==('bengali','marathi') else "indictrans2-320m-neural",
                    "engine": "indictrans2-320m-neural+lora" if self.adapter_sha256 and (source_language,target_language)==('bengali','marathi') else "indictrans2-320m-neural",
                    "fallback_used": False
                }
                with self._cache_lock:
                    self._translation_cache[cache_key] = dict(result)
                    if len(self._translation_cache) > self.max_cache_size:
                        self._translation_cache.popitem(last=False)
                return result
            except Exception as exc:
                logger.warning("IndicTrans2 inference failed (%s); checking available fallback.", exc.__class__.__name__)

        if not rule_pair(source_language, target_language):
            if self.is_loaded:
                raise HTTPException(status_code=503,detail='The model could not produce a reliable translation for this sentence. Try a shorter or simpler sentence.')
            raise HTTPException(status_code=503, detail="Neural translation is unavailable for this language pair. Install requirements-neural.txt and retry; no rule translation is available.")

        # 3. Fallback to our high-accuracy modular conversational translator
        fallback_res = modular_translator.translate(
            text=clean_text,
            source_language=source_language,
            target_language=target_language,
            script=script
        )
        fallback_res["fallback_used"] = True
        fallback_res["engine"] = fallback_res.get("engine", fallback_res.get("model_source", "curated_corpus"))
        fallback_res["model_source"] = fallback_res.get("model_source", "curated_corpus")

        with self._cache_lock:
            self._translation_cache[cache_key] = dict(fallback_res)
            if len(self._translation_cache) > self.max_cache_size:
                self._translation_cache.popitem(last=False)
        return fallback_res

indictrans2_adapter = IndicTrans2Adapter()
