from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.entities import LanguageProfile
from app.schemas.progress import (
    ProgressResponse, MilestoneRoadmapItem, BridgeModeUpdateRequest, ScriptRecommendationDTO
)
from app.services.progress.service import progress_service
from app.services.progress.progression_engine import script_progression_engine

router = APIRouter()

@router.get("/progress", response_model=ProgressResponse)
def get_progress(db: Session = Depends(get_db)):
    """Fetches user overall language vs script progress, milestones, and script recommendation."""
    return progress_service.get_user_progress(user_id=1, db=db)

@router.get("/progress/milestones", response_model=List[MilestoneRoadmapItem])
def get_milestones_roadmap(db: Session = Depends(get_db)):
    """Returns the full Level 0 to Level 5 progression roadmap with exercise completion metrics."""
    return script_progression_engine.get_milestones_roadmap(db=db, user_id=1)

@router.get("/progress/recommendation", response_model=ScriptRecommendationDTO)
def get_script_recommendation(db: Session = Depends(get_db)):
    """Computes real-time script progression recommendation based on independent script score."""
    profile = db.query(LanguageProfile).filter(LanguageProfile.user_id == 1).first()
    if not profile:
        profile = LanguageProfile(user_id=1)
    rec_data = script_progression_engine.evaluate_script_progression(profile)
    return ScriptRecommendationDTO(**rec_data)

@router.post("/progress/bridge-mode")
def update_bridge_mode(req: BridgeModeUpdateRequest, db: Session = Depends(get_db)):
    """Updates user's Bridge Mode level (beginner, intermediate, advanced)."""
    return script_progression_engine.update_bridge_mode(db=db, user_id=1, new_mode=req.mode)

