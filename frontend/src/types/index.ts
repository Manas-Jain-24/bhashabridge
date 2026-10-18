export type ScriptMode = 'roman' | 'devanagari' | 'both';
export type BridgeLevel = 'beginner' | 'intermediate' | 'advanced';
export type Language = 'hindi' | 'marathi';

export interface VocabularyItem {
  source_word: string;
  target_word: string;
  target_roman?: string;
  meaning: string;
  part_of_speech?: string;
  is_construction_based: boolean;
  morph_analysis?: string;
  gender_contrast?: string;
  root_lemma?: string;
}

export interface GrammarPoint {
  title: string;
  concept: string;
  source_pattern?: string;
  target_pattern?: string;
  explanation: string;
}

export interface ExampleItem {
  source_sentence: string;
  target_sentence: string;
  target_roman: string;
  english_translation: string;
}

export interface AnalyzeResponse {
  detected_language: string;
  detected_script: string;
  normalized_text: string;
  native_text: string;
  roman_text: string;
  translation: string;
  translation_native: string;
  translation_roman: string;
  english_meaning: string;
  vocabulary: VocabularyItem[];
  grammar_explanation: GrammarPoint[];
  differences: string[];
  common_mistakes: string[];
  examples: ExampleItem[];
  model_source?: string;
  explanation_source?: string;
  cultural_mnemonic?: string;
}

export interface PracticeOption {
  id: string;
  text_devanagari: string;
  text_roman: string;
}

export interface PracticeQuestion {
  id: string;
  question_type: string;
  prompt: string;
  prompt_roman?: string;
  target_language: string;
  source_language: string;
  options?: PracticeOption[];
  hint?: string;
}

export interface PracticeEvaluateResponse {
  correctness: boolean;
  score: number;
  expected_answer_devanagari: string;
  expected_answer_roman: string;
  user_answer: string;
  explanation: string;
  mistakes: string[];
  concepts_to_review: string[];
}

export interface SkillScore {
  name: string;
  percentage: number;
  level: string;
}

export interface MilestoneItem {
  id: number;
  title: string;
  level: string;
  completed_exercises: number;
  total_exercises: number;
  status: string;
}

export interface MilestoneRoadmapItem {
  id: number;
  level: string;
  level_number: number;
  title: string;
  description?: string;
  total_exercises: number;
  completed_exercises: number;
  progress_percentage: number;
  status: 'completed' | 'in_progress' | 'locked';
  is_active: boolean;
}

export interface ScriptRecommendation {
  current_mode: string;
  recommended_mode: string;
  composite_script_score: number;
  ready_to_advance: boolean;
  recommendation_message: string;
  action_label: string;
}

export interface ProgressData {
  target_language: string;
  overall_percentage: number;
  language_skills: SkillScore[];
  script_skills: SkillScore[];
  current_milestone: MilestoneItem;
  weak_areas: string[];
  review_due_count: number;
  bridge_mode_level: string;
  script_recommendation?: ScriptRecommendation;
}

export interface GamificationProfile {
  xp: number;
  level: number;
  streak_days: number;
  hearts: number;
  max_hearts: number;
  rank_title: string;
  unlocked_badges: string[];
  blitz_high_score: number;
  completed_scrambles: number;
  completed_scenarios: string[];
  next_level_xp: number;
}

export interface ScrambleTileItem {
  id: string;
  token: string;
  roman: string;
  is_distractor: boolean;
  trap_explanation?: string;
}

export interface ScrambleQuestionItem {
  id: string;
  prompt_hindi: string;
  prompt_roman: string;
  english_meaning: string;
  target_sentence_devanagari: string;
  target_sentence_roman: string;
  target_tokens: string[];
  tiles: ScrambleTileItem[];
  grammar_tip: string;
  topic: string;
  level: number;
}

export interface BlitzQuestionItem {
  id: string;
  question: string;
  question_roman?: string;
  type: 'true_false' | 'multiple_choice';
  is_true?: boolean;
  options?: string[];
  correct_index?: number;
  explanation: string;
  concept: string;
  points: number;
}

export interface StreetScenarioChoiceItem {
  id: string;
  text_devanagari: string;
  text_roman: string;
  english: string;
  is_best: boolean;
  is_hindi_slip: boolean;
  reaction_devanagari: string;
  reaction_roman: string;
  xp_reward: number;
  feedback: string;
}

export interface StreetScenarioStepItem {
  step_number: number;
  speaker: string;
  avatar: string;
  dialogue_devanagari: string;
  dialogue_roman: string;
  english_meaning: string;
  choices: StreetScenarioChoiceItem[];
}

export interface StreetScenarioItem {
  id: string;
  title: string;
  marathi_title: string;
  location: string;
  badge_id: string;
  badge_name: string;
  badge_icon: string;
  description: string;
  steps: StreetScenarioStepItem[];
}

export interface SkillTreeNodeItem {
  id: number;
  level: number;
  title: string;
  marathi_title: string;
  icon: string;
  status: 'completed' | 'in_progress' | 'locked';
  stars: number;
  exercises_count: number;
  completed_count: number;
  description: string;
  key_concepts: string[];
}

export interface SrsWordItem {
  id: number;
  devanagari: string;
  roman: string;
  english_meaning: string;
  hindi_meaning?: string;
  topic?: string;
  difficulty?: string;
  box_level: number;
  repetition_count: number;
}

export interface BoxDistributionItem {
  box: number;
  name: string;
  count: number;
  percentage: number;
  interval: string;
}

export interface VocabularyBoxStatistics {
  total_words: number;
  mastered_words: number;
  box_distribution: BoxDistributionItem[];
}

export interface DailyMission {
  id: string;
  title: string;
  marathi_title: string;
  xp_reward: number;
  target: number;
  current: number;
  completed: boolean;
  icon: string;
}

export interface DailyQuestData {
  word_of_the_day: {
    devanagari: string;
    roman: string;
    meaning_english: string;
    meaning_hindi: string;
    cultural_note: string;
    example_marathi: string;
    example_roman: string;
    example_hindi: string;
  };
  idiom_of_the_day: {
    devanagari: string;
    roman: string;
    meaning_english: string;
    hindi_equivalent: string;
    explanation: string;
  };
  daily_missions: DailyMission[];
}

export interface PronunciationEvaluateResult {
  accuracy_score: number;
  spoken_text: string;
  target_phrase: string;
  matched_words: string[];
  missing_words: string[];
  feedback: string;
  phonetic_stress_guide: string;
  is_native_pass: boolean;
}

