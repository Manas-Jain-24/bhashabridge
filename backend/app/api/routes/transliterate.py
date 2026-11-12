from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.core.auth import current_user, Identity
from app.services.runtime import run_inference
from app.schemas.transliterate import TransliterateRequest, TransliterateResponse
from app.services.transliteration.service import transliteration_service
from app.services.language_detection.detector import language_detector

router = APIRouter()

@router.post("/transliterate", response_model=TransliterateResponse)
async def transliterate_text(request: TransliterateRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return await run_inference(lambda _: transliterate_sync(request), db, user.id,
                               'transliterate', request.language, request.language)


def transliterate_sync(request: TransliterateRequest):
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
