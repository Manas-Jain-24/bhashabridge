from fastapi import APIRouter
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.language_detection.detector import language_detector
from app.services.transliteration.service import transliteration_service
from app.services.translation.service import translation_service
from app.services.explanation.engine import explanation_engine

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeRequest):
    """
    Principle 1 Implementation:
    INPUT -> Language/script detection -> Transliteration -> Translation
    -> Word/vocabulary analysis -> Grammar/context explanation -> Examples
    """
    normalized = language_detector.normalize(request.text)
    detected_script = language_detector.detect_script(normalized)
    
    inferred_lang = language_detector.detect_language(normalized, hint_script=detected_script)
    norm_lower_words = set(w.lower().strip(".,!?:;\"'()[]{}") for w in normalized.split())
    has_strong_marathi = any(w in language_detector.MARATHI_CUES for w in norm_lower_words)
    has_strong_hindi = any(w in language_detector.HINDI_CUES for w in norm_lower_words)

    if request.source_language == "auto":
        detected_language = inferred_lang
    elif has_strong_marathi and not has_strong_hindi and request.source_language == "hindi":
        # User typed unambiguous Marathi (e.g. 'maza naav ... aahe') while selector was on Hindi
        detected_language = "marathi"
    elif has_strong_hindi and not has_strong_marathi and request.source_language == "marathi":
        # User typed unambiguous Hindi (e.g. 'mujhe kal ... jaana hai') while selector was on Marathi
        detected_language = "hindi"
    else:
        detected_language = request.source_language

    if request.target_language and request.target_language != "auto" and request.target_language != detected_language:
        target_lang = request.target_language
    else:
        target_lang = "hindi" if detected_language == "marathi" else "marathi"

    # Transliterate to both scripts for the source
    if detected_script == "latin":
        native_source = transliteration_service.transliterate(
            normalized, language=detected_language, direction="latin_to_devanagari"
        )
        roman_source = normalized
    else:
        native_source = normalized
        roman_source = transliteration_service.transliterate(
            normalized, language=detected_language, direction="devanagari_to_latin"
        )

    # Translate
    trans_result = translation_service.translate(
        text=native_source,
        source_language=detected_language,
        target_language=target_lang,
        script=request.preferred_script
    )

    # Explain
    explanation_result = explanation_engine.explain(
        source_text=native_source,
        source_language=detected_language,
        target_text=trans_result["translation_native"],
        target_language=target_lang
    )

    return AnalyzeResponse(
        detected_language=detected_language,
        detected_script=detected_script,
        normalized_text=normalized,
        native_text=native_source,
        roman_text=roman_source,
        translation=trans_result["translation"],
        translation_native=trans_result["translation_native"],
        translation_roman=trans_result["translation_roman"],
        english_meaning=trans_result["english_meaning"],
        vocabulary=explanation_result["word_explanations"],
        grammar_explanation=explanation_result["grammar_points"],
        differences=explanation_result["differences"],
        common_mistakes=explanation_result["common_mistakes"],
        examples=explanation_result["examples"],
        model_source=trans_result.get("model_source"),
        explanation_source=explanation_result.get("explanation_source", "local_rules"),
        cultural_mnemonic=explanation_result.get("cultural_mnemonic")
    )
