from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.gamification import (
    GamificationProfileResponse, GamificationActionRequest,
    ScrambleQuestion, BlitzQuestion, StreetScenario, SkillTreeNode
)
from app.services.gamification.engine import gamification_service

router = APIRouter()

@router.get("/gamification/profile", response_model=GamificationProfileResponse)
def get_gamification_profile(db: Session = Depends(get_db)):
    """Fetches user XP, level, rank title, streak flame, hearts, and unlocked badges."""
    return gamification_service.get_profile_dto(db, user_id=1)

@router.post("/gamification/action", response_model=GamificationProfileResponse)
def record_gamification_action(req: GamificationActionRequest, db: Session = Depends(get_db)):
    """Processes in-game actions: XP gains, heart loss/refill, badge unlock, blitz scores."""
    return gamification_service.process_action(db, req, user_id=1)

@router.get("/gamification/skill-tree", response_model=List[SkillTreeNode])
def get_skill_tree(db: Session = Depends(get_db)):
    """Fetches the 6-level Bridge Quest roadmap with unlock status, stars, and concepts."""
    return gamification_service.get_skill_tree(db, user_id=1)

@router.get("/gamification/scramble", response_model=List[ScrambleQuestion])
def get_scramble_questions():
    """Fetches tap-to-assemble sentence scramble challenges with intentional trap distractors."""
    return gamification_service.get_scramble_questions()

@router.get("/gamification/blitz", response_model=List[BlitzQuestion])
def get_blitz_questions():
    """Fetches 60-second rapid-fire arcade questions with combo scoring."""
    return gamification_service.get_blitz_questions()

@router.get("/gamification/scenarios", response_model=List[StreetScenario])
def get_street_scenarios():
    """Fetches Pune/Mumbai street conversational simulations with branching dialogues."""
    return gamification_service.get_street_scenarios()
