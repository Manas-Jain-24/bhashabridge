"""
BhashaBridge — Pronunciation & Speech Evaluation Service
Evaluates spoken Marathi audio transcriptions against target native phrases.
Computes phonetic similarity, detects missed words, and provides syllable stress guides.
"""

from typing import Dict, Any, List
import re
import unicodedata

class PronunciationService:
    """
    Evaluates spoken Marathi against target phrases.
    """

    def evaluate_spoken_phrase(self, spoken_text: str, target_phrase: str) -> Dict[str, Any]:
        clean_spoken = self._normalize(spoken_text)
        clean_target = self._normalize(target_phrase)

        spoken_words = clean_spoken.split()
        target_words = clean_target.split()

        if not spoken_words or not target_words:
            return {
                "spoken_text": spoken_text,
                "target_phrase": target_phrase,
                "accuracy_score": 0.0,
                "feedback": "No speech detected. Please speak clearly into the microphone.",
                "matched_words": [],
                "missing_words": target_words,
                "phonetic_stress_guide": self._generate_stress_guide(target_phrase),
                "is_native_pass": False
            }

        matched_words = []
        missing_words = []

        remaining_words = list(spoken_words)
        for tw in target_words:
            if tw in remaining_words:
                matched_words.append(tw)
                remaining_words.remove(tw)
            else:
                missing_words.append(tw)

        # Word-level accuracy
        word_accuracy = self._levenshtein_similarity(spoken_words, target_words) * 100.0

        # Character-level similarity for slight pronunciation deviations
        char_sim = self._levenshtein_similarity(clean_spoken, clean_target) * 100.0

        # Blended score
        composite_score = round(0.6 * word_accuracy + 0.4 * char_sim, 1)

        # Feedback generation
        if composite_score >= 85:
            feedback = "Your speech transcript closely matches the target. Listen to the example to compare pronunciation."
            is_native_pass = True
        elif composite_score >= 65:
            feedback = f"फार छान! (Very Good!) High comprehension. Pay special attention to missing words: {', '.join(missing_words) if missing_words else 'none'}."
            is_native_pass = True
        else:
            feedback = f"सराव चालू ठेवा! (Keep practicing!) You spoke: '{spoken_text}'. Try stressing the bolded syllables below."
            is_native_pass = False

        return {
            "accuracy_score": composite_score,
            "spoken_text": spoken_text,
            "target_phrase": target_phrase,
            "matched_words": matched_words,
            "missing_words": missing_words,
            "feedback": feedback,
            "phonetic_stress_guide": self._generate_stress_guide(target_phrase),
            "is_native_pass": is_native_pass
        }

    def _normalize(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text.lower().strip())
        t = ''.join(c if c.isspace() or unicodedata.category(c)[0] in "LMN" else ' ' for c in text)
        return re.sub(r'\s+', ' ', t).strip()

    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        if s1 == s2:
            return 1.0
        if not s1 or not s2:
            return 0.0

        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        distance = dp[m][n]
        max_len = max(m, n)
        return max(0.0, 1.0 - (distance / max_len))

    def _generate_stress_guide(self, phrase: str) -> str:
        # Generates capitalized syllable stress approximations
        guides = {
            "मला उद्या कॉलेजला जायचं आहे": "ma-LA ud-YA col-lege-LA jay-cha AA-he",
            "मी आता घरी जात आहे": "MI aa-TA gha-RI jaat AA-he",
            "मला थंड पाणी पाहिजे": "ma-LA thand PAA-ni pa-HI-je",
            "भाऊ एक कडक चहा द्या": "BHAU ek ka-DAK cha-HA DYA",
            "तुम्ही कसे आहात": "tum-HI ka-SE aa-HAAT",
            "काय चाललंय": "KAAY chaal-LAY"
        }
        return guides.get(phrase.strip(), phrase)

pronunciation_service = PronunciationService()
