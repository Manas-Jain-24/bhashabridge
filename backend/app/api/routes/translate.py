from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.translate import TranslateRequest, TranslateResponse
from app.services.translation.service import translate_with_memory
from app.services.translation.english import with_english_meaning
from app.core.auth import current_user, Identity
from app.services.runtime import run_inference

router = APIRouter()

@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return await run_inference(lambda session: translate_sync(request, session), db, user.id,
                               'translate', request.source_language, request.target_language)


def translate_sync(request: TranslateRequest, db: Session):
    result = translate_with_memory(db,
        text=request.text,
        source_language=request.source_language,
        target_language=request.target_language,
        script=request.script,
        translation_mode=request.translation_mode,
    )
    return TranslateResponse(**with_english_meaning(result))
