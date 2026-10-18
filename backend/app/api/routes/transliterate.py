from fastapi import APIRouter
from app.schemas.transliterate import TransliterateRequest, TransliterateResponse
from app.services.transliteration.service import transliteration_service
from app.services.language_detection.detector import language_detector

router = APIRouter()

@router.post("/transliterate", response_model=TransliterateResponse)
def transliterate_text(request: TransliterateRequest):
    detected_script = language_detector.detect_script(request.text)
    output = transliteration_service.transliterate(
        text=request.text,
        language=request.language,
        direction=request.direction
    )
    return TransliterateResponse(
        input=request.text,
        output=output,
        language=request.language,
        direction=request.direction,
        detected_script=detected_script
    )
