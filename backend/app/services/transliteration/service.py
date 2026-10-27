import os
import sys
import re
import logging
import threading
from pathlib import Path
from typing import Optional
from app.services.base import BaseTransliterationService
from app.core.config import settings

logger = logging.getLogger("bhashabridge.transliteration")

# Ensure project root containing ml/ is in sys.path
_current = Path(__file__).resolve()
for _p in _current.parents:
    if (_p / "ml" / "transliteration").exists():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

TOKEN_PATTERN = re.compile(r'([a-zA-Z]+|[ऀ-ॿ]+|[^a-zA-Zऀ-ॿ]+)')

class NeuralTransliterationService(BaseTransliterationService):
    """
    Hybrid Neural & Rule-based Transliteration Service.
    Powered by a trained Character-level Sequence-to-Sequence (Seq2Seq) GRU model
    with Bahdanau Attention, with robust phonetic fallback for high resilience.
    Uses truly lazy model initialization and token-by-token mixed-script preservation.
    """

    def __init__(self):
        self._neural_model = None
        self._is_loaded = False
        self._load_attempts = 0
        self._max_load_attempts = 2  # 1 initial attempt + 1 guarded retry
        self._load_failed = False
        self._lock = threading.Lock()
        # Do NOT load model weights or import torch during __init__ or module import

    def _ensure_neural_model_loaded(self) -> bool:
        """
        Lazily loads the neural transliteration model on first request.
        Guards against repeated expensive attempts when weights/deps are unavailable.
        Allows at most one guarded retry if the first attempt fails.
        """
        if settings.USE_MOCK_MODELS or settings.TESTING:
            return False
        if self._is_loaded and self._neural_model is not None:
            return True
        if self._load_failed or self._load_attempts >= self._max_load_attempts:
            return False

        with self._lock:
            if self._is_loaded and self._neural_model is not None:
                return True
            if self._load_failed or self._load_attempts >= self._max_load_attempts:
                return False

            while self._load_attempts < self._max_load_attempts:
                self._load_attempts += 1
                logger.info(
                    f"[*] Lazy-loading neural transliteration model (attempt {self._load_attempts}/{self._max_load_attempts})..."
                )
                try:
                    from ml.transliteration.predictor import NeuralTransliterator
                    model = NeuralTransliterator()
                    if getattr(model, "is_loaded", False):
                        self._neural_model = model
                        self._is_loaded = True
                        logger.info("[*] Neural transliteration model successfully loaded and active.")
                        return True
                    else:
                        logger.warning(
                            f"[!] NeuralTransliterator initialized without weights (attempt {self._load_attempts})."
                        )
                except Exception as exc:
                    logger.warning(
                        f"[!] Failed to load neural transliteration model on attempt {self._load_attempts}: {exc}"
                    )

            self._load_failed = True
            logger.warning(
                "[!] Neural transliteration model is unavailable. Future requests will route directly to rule fallback."
            )
            return False

    def _transliterate_single_token(self, token: str, language: str = "marathi", direction: str = "latin_to_devanagari") -> str:
        """Transliterates a single token according to direction, preserving script rules."""
        if direction == "latin_to_devanagari":
            if self._ensure_neural_model_loaded():
                try:
                    res = self._neural_model.transliterate_word(token.lower(), language=language)
                    if res:
                        return res
                except Exception as exc:
                    logger.debug(f"Neural token transliteration error for '{token}': {exc}")

            from app.services.transliteration.phonetic_rule_service import phonetic_transliterator
            return phonetic_transliterator._latin_word_to_dev(token, lang=language)
        else:
            # devanagari_to_latin
            from app.services.transliteration.phonetic_rule_service import phonetic_transliterator
            return phonetic_transliterator._dev_word_to_latin(token)

    def transliterate(self, text: str, language: str = "marathi", direction: str = "latin_to_devanagari") -> str:
        """
        Token-by-token transliteration preserving mixed scripts, whitespace, and punctuation.
        - In latin_to_devanagari: Latin tokens are transliterated, Devanagari tokens preserved.
        - In devanagari_to_latin: Devanagari tokens are transliterated, Latin tokens preserved.
        - All whitespace, punctuation, digits, and symbols are preserved in place.
        """
        if not text:
            return ""

        tokens = TOKEN_PATTERN.findall(text)
        if not tokens:
            return text

        result = []
        for tok in tokens:
            has_devanagari = any('\u0900' <= c <= '\u097f' for c in tok)
            has_latin = any(('a' <= c <= 'z') or ('A' <= c <= 'Z') for c in tok)

            if direction == "latin_to_devanagari":
                if has_devanagari and not has_latin:
                    # Already Devanagari: preserve exactly
                    result.append(tok)
                elif has_latin:
                    # Latin token: transliterate
                    result.append(self._transliterate_single_token(tok, language=language, direction=direction))
                else:
                    # Whitespace, punctuation, numbers, symbols
                    result.append(tok)
            else:
                # devanagari_to_latin
                if has_latin and not has_devanagari:
                    # Already Latin: preserve exactly
                    result.append(tok)
                elif has_devanagari:
                    # Devanagari token: transliterate
                    result.append(self._transliterate_single_token(tok, language=language, direction=direction))
                else:
                    result.append(tok)

        return "".join(result)

def get_transliteration_service() -> BaseTransliterationService:
    return NeuralTransliterationService()

transliteration_service = get_transliteration_service()
