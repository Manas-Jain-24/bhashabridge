from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class GamificationProfileResponse(BaseModel):
    xp: int
    level: int
    streak_days: int
    hearts: int
    max_hearts: int = 3
    rank_title: str
    unlocked_badges: List[str]
    blitz_high_score: int
    completed_scrambles: int
    completed_scenarios: List[str]
    next_level_xp: int = 500

class GamificationActionRequest(BaseModel):
    action_type: str = Field(..., description="xp_gain, heart_lost, heart_refill, unlock_badge, blitz_score, complete_scramble, complete_scenario")
    xp_amount: Optional[int] = 0
    badge_id: Optional[str] = None
    score: Optional[int] = 0
    scenario_id: Optional[str] = None

class ScrambleTile(BaseModel):
    id: str
    token: str
    roman: str
    is_distractor: bool = False
    trap_explanation: Optional[str] = None

class ScrambleQuestion(BaseModel):
    id: str
    prompt_hindi: str
    prompt_roman: str
    english_meaning: str
    target_sentence_devanagari: str
    target_sentence_roman: str
    target_tokens: List[str]
    tiles: List[ScrambleTile]
    grammar_tip: str
    topic: str
    level: int

class BlitzQuestion(BaseModel):
    id: str
    question: str
    question_roman: Optional[str] = None
    type: str = "true_false"  # true_false or multiple_choice
    is_true: Optional[bool] = None
    options: Optional[List[str]] = None
    correct_index: Optional[int] = None
    explanation: str
    concept: str
    points: int = 100

class StreetScenarioChoice(BaseModel):
    id: str
    text_devanagari: str
    text_roman: str
    english: str
    is_best: bool
    is_hindi_slip: bool = False
    reaction_devanagari: str
    reaction_roman: str
    xp_reward: int = 25
    feedback: str

class StreetScenarioStep(BaseModel):
    step_number: int
    speaker: str
    avatar: str
    dialogue_devanagari: str
    dialogue_roman: str
    english_meaning: str
    choices: List[StreetScenarioChoice]

class StreetScenario(BaseModel):
    id: str
    title: str
    marathi_title: str
    location: str
    badge_id: str
    badge_name: str
    badge_icon: str
    description: str
    steps: List[StreetScenarioStep]

class SkillTreeNode(BaseModel):
    id: int
    level: int
    title: str
    marathi_title: str
    icon: str
    status: str  # completed, in_progress, locked
    stars: int
    exercises_count: int
    completed_count: int
    description: str
    key_concepts: List[str]
