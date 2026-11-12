from app.core.auth import current_user, Identity
from typing import Literal, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.languages import Language
from app.models.database import get_db
from app.services.gamification import arcade
from app.services.gamification.curriculum import course

router = APIRouter()

class StartGame(BaseModel):
    language: Language
    mode: Literal["recognize", "spell", "meaning", "sprint"]
    difficulty: Literal['beginner','intermediate','advanced'] = 'advanced'
    topic: Literal['all','daily','places','people','objects','nature','numbers'] = 'all'
    practice: Literal['mixed','new','review'] = 'mixed'
    lesson_id: Optional[str] = Field(default=None,min_length=1,max_length=50)

class GameAnswer(BaseModel):
    session_id: str = Field(min_length=1, max_length=36)
    question_id: str = Field(min_length=1, max_length=40)
    choice_id: Optional[str] = Field(default=None, max_length=4)
    tile_ids: Optional[list[int]] = Field(default=None, max_length=40)

@router.get("/arcade/stats/{language}")
def game_stats(language: Language, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return arcade.stats(db, language, user_id=user.id)

@router.post("/arcade/start")
def start_game(request: StartGame, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return arcade.start_session(db, request.language, request.mode,request.difficulty,request.topic,request.practice,request.lesson_id,user_id=user.id)

@router.get('/arcade/lessons/{language}')
def lessons(language: Language):
    return course(language)

@router.get("/arcade/session/{session_id}")
def get_game(session_id: str, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    session = arcade.get_session(db, session_id, user_id=user.id)
    import json
    return arcade.session_view(session, json.loads(session.state_json))

@router.post("/arcade/answer")
def game_answer(request: GameAnswer, db: Session = Depends(get_db), user: Identity = Depends(current_user)):
    return arcade.submit_answer(db, request, user_id=user.id)
