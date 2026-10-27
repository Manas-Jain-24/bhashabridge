from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translation.service import translate_with_memory

router = APIRouter()

@router.post("/translate", response_model=TranslateResponse)
def translate_text(request: TranslateRequest, db: Session = Depends(get_db)):
    result = translate_with_memory(db,
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
        script=request.script
    )
    return TranslateResponse(**result)
