from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translation.service import translate_with_memory
from app.services.translation.english import with_english_meaning

router = APIRouter()

@router.post("/translate", response_model=TranslateResponse)
def translate_text(request: TranslateRequest, db: Session = Depends(get_db)):
    result = translate_with_memory(db,
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
        script=request.script,
        translation_mode=request.translation_mode,
    )
    return TranslateResponse(**with_english_meaning(result))
