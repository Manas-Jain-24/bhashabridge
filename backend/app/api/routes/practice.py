from typing import List, Dict, Any
from fastapi import APIRouter, Depends
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

router = APIRouter()

@router.post("/practice/generate", response_model=PracticeQuestionDTO)
def generate_practice(request: PracticeGenerateRequest):
    return practice_service.generate_question(
        language=request.language,
        difficulty=request.difficulty,
        topic=request.topic or "general",
        question_type=request.question_type or "all"
    )

@router.post("/practice/evaluate", response_model=PracticeEvaluateResponse)
def evaluate_practice(request: PracticeEvaluateRequest, db: Session = Depends(get_db)):
    return practice_service.evaluate_answer(
        question_id=request.question_id,
        user_answer=request.user_answer,
        user_script=request.user_script or "roman",
        db=db
    )

@router.get("/practice/history")
def get_practice_history(limit: int = 10, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
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
def get_vocabulary_review_queue(limit: int = 15, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
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
def evaluate_pronunciation(req: PronunciationEvaluateRequest):
    return pronunciation_service.evaluate_spoken_phrase(req.spoken_text, req.target_phrase)
