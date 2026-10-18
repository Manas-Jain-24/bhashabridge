from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.analyze import AnalyzeResponse, VocabularyItem, GrammarPoint, ExampleItem
from app.schemas.practice import PracticeQuestionDTO, PracticeEvaluateResponse
from app.schemas.progress import ProgressResponse

class BaseLanguageDetector(ABC):
    @abstractmethod
    def detect_script(self, text: str) -> str:
        """Detect script: 'devanagari', 'latin', or 'mixed'."""
        pass

    @abstractmethod
    def detect_language(self, text: str, hint_script: Optional[str] = None) -> str:
        """Detect language: 'hindi', 'marathi', or 'unknown'."""
        pass

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Normalize whitespace, punctuation, diacritics."""
        pass


class BaseTransliterationService(ABC):
    @abstractmethod
    def transliterate(self, text: str, language: str, direction: str) -> str:
        """
        Transliterate between latin and devanagari.
        direction: 'latin_to_devanagari' or 'devanagari_to_latin'
        """
        pass


class BaseTranslationService(ABC):
    @abstractmethod
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        script: str = "both"
    ) -> Dict[str, Any]:
        """
        Translate sentence between Hindi and Marathi.
        Returns dict with native, roman, and english translations.
        """
        pass


class BaseExplanationService(ABC):
    @abstractmethod
    def explain(
        self,
        source_text: str,
        source_language: str,
        target_text: str,
        target_language: str
    ) -> Dict[str, Any]:
        """
        Provide structured linguistic and grammatical breakdown.
        """
        pass


class BasePracticeService(ABC):
    @abstractmethod
    def generate_question(
        self,
        language: str,
        difficulty: str = "level_1",
        topic: str = "general",
        question_type: str = "all"
    ) -> PracticeQuestionDTO:
        pass

    @abstractmethod
    def evaluate_answer(
        self,
        question_id: str,
        user_answer: str,
        user_script: str = "roman"
    ) -> PracticeEvaluateResponse:
        pass


class BaseProgressService(ABC):
    @abstractmethod
    def get_user_progress(self, user_id: int = 1) -> ProgressResponse:
        pass
