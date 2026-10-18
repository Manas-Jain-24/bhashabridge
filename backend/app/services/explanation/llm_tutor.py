import os
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class GeminiLinguisticTutor:
    """
    Hybrid LLM Linguistic Sensei powered by Google Gemini.
    Enriches deterministic rule-based alignments with conversational nuance,
    cultural context, and memorable mnemonics.
    Silently fails over to local symbolic rules if offline or key is missing.
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Gemini Linguistic Sensei initialized successfully.")
            except Exception as e:
                logger.warning("Could not initialize Gemini Client (%s). Using local rule engine.", e)
                self._client = None

    @property
    def is_available(self) -> bool:
        # Check dynamically in case environment variable was set after startup
        if not self._client:
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key:
                try:
                    from google import genai
                    self.api_key = env_key
                    self._client = genai.Client(api_key=env_key)
                except Exception:
                    return False
        return self._client is not None

    def explain(
        self,
        source_text: str,
        source_language: str,
        target_text: str,
        target_language: str,
        aligned_tokens: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts to generate an enriched pedagogical explanation using Gemini.
        Returns a dict with 'summary', 'differences', 'cultural_mnemonic', and 'formality_note'
        or None if unavailable/failed.
        """
        if not self.is_available:
            return None

        aligned_summary = ""
        if aligned_tokens:
            aligned_summary = "\nWord Alignments:\n" + "\n".join(
                f"- {item.get('source_word')} -> {item.get('target_word')}: {item.get('meaning')} ({item.get('gender_contrast') or item.get('morph_analysis') or 'aligned'})"
                for item in aligned_tokens[:6]
            )

        prompt = f"""You are 'BhashaBridge Sensei', a friendly, linguistically expert language tutor specializing in Hindi and Marathi cross-lingual nuances.

Task: Provide a concise, pedagogical explanation of why and how the sentence changes between Hindi and Marathi.
Source ({source_language}): "{source_text}"
Target ({target_language}): "{target_text}"
{aligned_summary}

Key linguistic facts to consider if applicable:
1. Marathi preserves the Sanskrit Neuter (नपुंसकलिंग) gender (e.g. पाणी, पुस्तक, घर), whereas Hindi has only Masculine/Feminine.
2. Dative experiencer subjects (e.g., मुझे ➔ मला).
3. Synthetic suffixation in Marathi (e.g., कॉलेज ➔ कॉलेजला) vs Hindi analytic postpositions (कॉलेज में / कॉलेज को).
4. Inflecting modals in Marathi (हवे आहे, हवा आहे, हवी आहे, पाहिजेत) vs invariant Hindi (चाहिए).

Return ONLY a valid JSON object with the following keys:
{{
  "summary": "1-2 punchy sentences explaining the core shift and grammatical reason.",
  "differences": [
    "Specific contrast bullet 1 (e.g. case/gender agreement)",
    "Specific contrast bullet 2 (e.g. suffixation or word choice)",
    "Specific contrast bullet 3 (e.g. register or false friends)"
  ],
  "cultural_mnemonic": "A short, fun memory hook or tip to remember this difference in daily conversation.",
  "formality_note": "A brief note on tone/register (e.g. 'Standard conversational - suitable for daily life')."
}}
"""

        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for model_name in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.2
                    }
                )
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                data = json.loads(text.strip())
                if "summary" in data and "differences" in data:
                    return {
                        "summary": data["summary"],
                        "differences": data.get("differences", []),
                        "cultural_mnemonic": data.get("cultural_mnemonic"),
                        "formality_note": data.get("formality_note")
                    }
            except Exception as e:
                logger.debug("Gemini attempt with %s failed: %s", model_name, e)
                continue

        return None

llm_tutor = GeminiLinguisticTutor()
