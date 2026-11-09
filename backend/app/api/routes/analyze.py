from app.core.languages import check_source_script
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.language_detection.detector import language_detector
from app.services.transliteration.service import transliteration_service
from app.services.translation.service import translate_with_memory
from app.services.explanation.engine import explanation_engine
from app.services.translation.english import with_english_meaning

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_text(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Principle 1 Implementation:
    INPUT -> Language/script detection -> Transliteration -> Translation
    -> Word/vocabulary analysis -> Grammar/context explanation -> Examples
    """
    if request.source_language != "auto":
        check_source_script(request.text, request.source_language)
    normalized = " ".join(request.text.split()) if request.source_language == "bengali" else language_detector.normalize(request.text)
    detected_script = language_detector.detect_script(normalized)
    
    inferred_lang = language_detector.detect_language(normalized, hint_script=detected_script)
    # A shared word such as घर or nahi is not evidence to override an explicit
    # source selector. Heuristic detection is used only when the caller asks for it.
    detected_language = inferred_lang if request.source_language == 'auto' else request.source_language

    if request.target_language == detected_language and "target_language" in request.model_fields_set:
        raise HTTPException(422, "Source and target languages must be different. Please choose another target language.")
    if request.target_language and request.target_language != "auto" and request.target_language != detected_language:
        target_lang = request.target_language
    else:
        target_lang = "hindi" if detected_language == "marathi" else "marathi"

    # Convert Roman tokens even when the input also contains native characters.
    native_source = transliteration_service.transliterate(
        normalized, language=detected_language, direction="latin_to_native"
    )
    roman_source = normalized if detected_script == "latin" else transliteration_service.transliterate(
        normalized, language=detected_language, direction="native_to_latin"
    )

    # Translate
    trans_result = translate_with_memory(db,
        text=request.text,
        source_language=detected_language,
        target_language=target_lang,
        script=request.preferred_script,
        native_text=native_source,
        translation_mode=request.translation_mode,
    )

    # Reuse the same contextual interpretation instead of generating a second,
    # potentially contradictory grammar story for the guessed spelling.
    native_source = trans_result.get('source_native', native_source)
    explanation_result = trans_result.get('_explanation') or explanation_engine.explain(
        source_text=native_source,
        source_language=detected_language,
        target_text=trans_result["translation_native"],
        target_language=target_lang,
        use_tutor=not trans_result.get('_skip_tutor', False),
    )

    trans_result=with_english_meaning({**trans_result,'target_language':target_lang},explanation_result)
    return AnalyzeResponse(
        target_language=target_lang,
        detected_language=detected_language,
        detected_script=detected_script,
        normalized_text=normalized,
        native_text=native_source,
        roman_text=roman_source,
        translation=trans_result["translation"],
        translation_native=trans_result["translation_native"],
        translation_roman=trans_result["translation_roman"],
        english_meaning=trans_result["english_meaning"],
        english_meaning_source=trans_result['english_meaning_source'],
        meaning_note=trans_result.get('meaning_note'),
        meaning_alternatives=trans_result.get('meaning_alternatives',[]),
        context_status=trans_result.get('context_status'),
        context_assessment=trans_result.get('context_assessment'),
        context_issue=trans_result.get('context_issue'),
        quality_note=trans_result.get('quality_note'),
        local_model_source=trans_result.get('local_model_source'),
        vocabulary=explanation_result["word_explanations"],
        grammar_explanation=explanation_result["grammar_points"],
        differences=explanation_result["differences"],
        common_mistakes=explanation_result["common_mistakes"],
        examples=explanation_result["examples"],
        model_source=trans_result.get("model_source"),
        explanation_source=explanation_result.get("explanation_source", "local_rules"),
        cultural_mnemonic=explanation_result.get("cultural_mnemonic")
    )
