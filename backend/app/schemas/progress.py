from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class SkillScore(BaseModel):
    name: str
    percentage: int
    level: str

class MilestoneItem(BaseModel):
    id: int
    title: str
    level: str
    completed_exercises: int
    total_exercises: int
    status: str

class ScriptRecommendationDTO(BaseModel):
    current_mode: str
    recommended_mode: str
    composite_script_score: float
    ready_to_advance: bool
    recommendation_message: str
    action_label: str

class MilestoneRoadmapItem(BaseModel):
    id: int
    level: str
    level_number: int
    title: str
    description: Optional[str] = None
    total_exercises: int
    completed_exercises: int
    progress_percentage: int
    status: str
    is_active: bool

class BridgeModeUpdateRequest(BaseModel):
    mode: str = Field(..., description="beginner, intermediate, or advanced")

class ProgressResponse(BaseModel):
    target_language: str
    overall_percentage: int
    language_skills: List[SkillScore]
    script_skills: List[SkillScore]
    current_milestone: MilestoneItem
    weak_areas: List[str]
    review_due_count: int
    bridge_mode_level: str
    script_recommendation: Optional[ScriptRecommendationDTO] = None
