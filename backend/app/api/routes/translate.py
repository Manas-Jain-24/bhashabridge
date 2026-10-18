from fastapi import APIRouter
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translation.service import translation_service

router = APIRouter()

@router.post("/translate", response_model=TranslateResponse)
def translate_text(request: TranslateRequest):
    result = translation_service.translate(
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
        script=request.script
    )
    return TranslateResponse(**result)
