from app.core.auth import current_user, Identity
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import PracticeAttempt, PracticeIssue
from datetime import timedelta
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
def generate_practice(request: PracticeGenerateRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    question = practice_service.generate_question(
        language=request.language,
        difficulty=request.difficulty,
        topic=request.topic or "general",
        question_type=request.question_type or "all",
        db=db, user_id=user.id
    )
    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"No practice questions found matching language='{request.language}', difficulty='{request.difficulty}', topic='{request.topic}'."
        )
    issue = db.query(PracticeIssue).filter_by(user_id=user.id, question_key=question.id).first()
    if issue is None:
        issue = PracticeIssue(user_id=user.id, question_key=question.id)
        db.add(issue)
    issue.issued_at = now_utc()
    db.commit()
    return question

@router.post("/practice/evaluate", response_model=PracticeEvaluateResponse)
def evaluate_practice(request: PracticeEvaluateRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    if user.role != 'local' and not db.query(PracticeIssue).filter(
        PracticeIssue.user_id == user.id, PracticeIssue.question_key == request.question_id,
        PracticeIssue.issued_at > now_utc()-timedelta(days=1)).first():
        raise HTTPException(404, 'Generate this practice question in your account first')
    result = practice_service.evaluate_answer(
        question_id=request.question_id,
        user_answer=request.user_answer,
        user_script=request.user_script or "roman",
        db=db,
        selected_option_id=request.selected_option_id, user_id=user.id
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
    db: Session = Depends(get_db), user: Identity = Depends(current_user)
) -> List[Dict[str, Any]]:
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user.id
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
    db: Session = Depends(get_db), user: Identity = Depends(current_user)
) -> List[Dict[str, Any]]:
    return srs_service.get_review_queue(db, limit=limit, user_id=user.id)

@router.post("/vocabulary/review/{word_id}")
def record_vocabulary_review(word_id: int, req: VocabularyReviewRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return srs_service.record_review_result(db, word_id=word_id, rating=req.rating, user_id=user.id)

@router.get("/vocabulary/boxes")
def get_vocabulary_boxes(db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return srs_service.get_box_statistics(db, user_id=user.id)

@router.get("/vocabulary/daily-quest")
def get_daily_quest(db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return srs_service.get_daily_quest_data(db, user_id=user.id)

@router.post("/pronunciation/evaluate", response_model=PronunciationEvaluateResponse)
def evaluate_pronunciation(req: PronunciationEvaluateRequest, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    result = pronunciation_service.evaluate_spoken_phrase(req.spoken_text, req.target_phrase)
    normalize = pronunciation_service._normalize
    known_targets = {normalize(q["expected_dev"]) for q in practice_service.QUESTIONS_BANK}
    if req.spoken_text.strip() and normalize(req.target_phrase) in known_targets:
        phrase_key = hashlib.sha256(normalize(req.target_phrase).encode("utf-8")).hexdigest()[:32]
        record_activity(db, f"speech:{now_utc().date()}:{phrase_key}", "speech", user_id=user.id)
        if result["is_native_pass"]:
            awarded = record_activity(db, f"speech_reward:{now_utc().date()}:{phrase_key}", "speech_reward", 40, user_id=user.id)
            result["xp_awarded"] = 40 if awarded else 0
        award_daily_missions(db, user_id=user.id)
        db.commit()
    return result
