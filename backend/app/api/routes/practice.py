from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import PracticeAttempt
from app.schemas.practice import (
    PracticeGenerateRequest, PracticeQuestionDTO,
    PracticeEvaluateRequest, PracticeEvaluateResponse,
    VocabularyReviewRequest, PronunciationEvaluateRequest, PronunciationEvaluateResponse
)
from app.services.practice.engine import practice_service
from app.services.vocabulary.srs_service import srs_service
from app.services.pronunciation.service import pronunciation_service
from app.services.activity import record_activity, now_utc, award_daily_missions
import hashlib

router = APIRouter()

@router.post("/practice/generate", response_model=PracticeQuestionDTO)
def generate_practice(request: PracticeGenerateRequest, db: Session = Depends(get_db)):
    question = practice_service.generate_question(
        language=request.language,
        difficulty=request.difficulty,
        topic=request.topic or "general",
        question_type=request.question_type or "all",
        db=db
    )
    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"No practice questions found matching language='{request.language}', difficulty='{request.difficulty}', topic='{request.topic}'."
        )
    return question

@router.post("/practice/evaluate", response_model=PracticeEvaluateResponse)
def evaluate_practice(request: PracticeEvaluateRequest, db: Session = Depends(get_db)):
    result = practice_service.evaluate_answer(
        question_id=request.question_id,
        user_answer=request.user_answer,
        user_script=request.user_script or "roman",
        db=db,
        selected_option_id=request.selected_option_id
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Question with ID '{request.question_id}' not found."
        )
    return result

@router.get("/practice/history")
def get_practice_history(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of historical attempts (1-100)"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == 1
    ).order_by(PracticeAttempt.created_at.desc()).limit(limit).all()

    return [
        {
            "id": a.id,
            "user_answer": a.user_answer,
            "is_correct": a.is_correct,
            "feedback": a.feedback,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in attempts
    ]

@router.get("/vocabulary/review")
def get_vocabulary_review_queue(
    limit: int = Query(default=15, ge=1, le=100, description="Maximum review queue batch size (1-100)"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    return srs_service.get_review_queue(db, limit=limit)

@router.post("/vocabulary/review/{word_id}")
def record_vocabulary_review(word_id: int, req: VocabularyReviewRequest, db: Session = Depends(get_db)):
    return srs_service.record_review_result(db, word_id=word_id, rating=req.rating)

@router.get("/vocabulary/boxes")
def get_vocabulary_boxes(db: Session = Depends(get_db)):
    return srs_service.get_box_statistics(db)

@router.get("/vocabulary/daily-quest")
def get_daily_quest(db: Session = Depends(get_db)):
    return srs_service.get_daily_quest_data(db)

@router.post("/pronunciation/evaluate", response_model=PronunciationEvaluateResponse)
def evaluate_pronunciation(req: PronunciationEvaluateRequest, db: Session = Depends(get_db)):
    result = pronunciation_service.evaluate_spoken_phrase(req.spoken_text, req.target_phrase)
    normalize = pronunciation_service._normalize
    known_targets = {normalize(q["expected_dev"]) for q in practice_service.QUESTIONS_BANK}
    if req.spoken_text.strip() and normalize(req.target_phrase) in known_targets:
        phrase_key = hashlib.sha256(normalize(req.target_phrase).encode("utf-8")).hexdigest()[:32]
        record_activity(db, f"speech:{now_utc().date()}:{phrase_key}", "speech")
        if result["is_native_pass"]:
            awarded = record_activity(db, f"speech_reward:{now_utc().date()}:{phrase_key}", "speech_reward", 40)
            result["xp_awarded"] = 40 if awarded else 0
        award_daily_missions(db)
        db.commit()
    return result
