import {apiFetch} from './http';
import {languages} from '../config/languages';

function validAnalysis(value: any): boolean {
  if (!value || typeof value !== 'object') return false;
  if (!['translation','translation_native','translation_roman','english_meaning','normalized_text',
    'native_text','roman_text','detected_script'].every(key=>typeof value[key]==='string')) return false;
  if (!(value.detected_language in languages) || !(value.target_language in languages)) return false;
  const rows = (key:string, fields:string[]) => Array.isArray(value[key]) && value[key].every((row:any)=>
    row && typeof row==='object' && fields.every(field=>typeof row[field]==='string') &&
    Object.values(row).every(item=>item===null||['string','boolean','undefined'].includes(typeof item)));
  if (!rows('vocabulary',['source_word','target_word','meaning']) ||
      !rows('grammar_explanation',['title','concept','explanation']) ||
      !rows('examples',['source_sentence','target_sentence','target_roman','english_translation'])) return false;
  if (!['differences','common_mistakes'].every(key=>Array.isArray(value[key])&&value[key].every((item:any)=>typeof item==='string'))) return false;
  if (value.meaning_alternatives!==undefined && !rows('meaning_alternatives',['label','source_text'])) return false;
  return ['meaning_note','quality_note','cultural_mnemonic','model_source','explanation_source'].every(key=>value[key]==null||typeof value[key]==='string');
}
import {
  AnalyzeResponse,
  PracticeQuestion,
  PracticeEvaluateResponse,
  ProgressData,
  ScriptMode,
  Language
} from '../types';

const API_BASE = '/api';

export const api = {
  async analyze(
    text: string,
    sourceLanguage: string = 'auto',
    targetLanguage: string = 'marathi',
    preferredScript: ScriptMode = 'both',
    signal?: AbortSignal,
    translationMode: 'hybrid' | 'local' = 'hybrid',
  ): Promise<AnalyzeResponse> {
    const res = await apiFetch(`${API_BASE}/analyze`, {
      signal,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        preferred_script: preferredScript,
        translation_mode: translationMode,
      }),
    });
    if (!res.ok) { const error = await res.json().catch(() => ({})); throw new Error(typeof error.detail === 'string' ? error.detail : 'Analysis failed. Please check the language and retry.'); }
    const data=await res.json();
    if(!validAnalysis(data)) throw new Error('The server returned an incomplete translation. Please retry.');
    return data;
  },

  async transliterate(
    text: string,
    language: Language = 'marathi',
    direction: 'latin_to_devanagari' | 'devanagari_to_latin' = 'latin_to_devanagari',
    signal?: AbortSignal
  ): Promise<{ input: string; output: string; detected_script: string }> {
    const res = await apiFetch(`${API_BASE}/transliterate`, {
      signal,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, direction }),
    });
    if (!res.ok) throw new Error('Transliteration failed');
    return res.json();
  },

  async getProgress(): Promise<ProgressData> {
    const res = await apiFetch(`${API_BASE}/progress`);
    if (!res.ok) throw new Error('Failed to fetch progress');
    return res.json();
  },

  async getMilestones(): Promise<import('../types').MilestoneRoadmapItem[]> {
    const res = await apiFetch(`${API_BASE}/progress/milestones`);
    if (!res.ok) throw new Error('Failed to fetch milestones roadmap');
    return res.json();
  },

  async updateBridgeMode(mode: string): Promise<{ status: string; updated_mode: string; message: string }> {
    const res = await apiFetch(`${API_BASE}/progress/bridge-mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error('Failed to update bridge mode');
    return res.json();
  },


  async generatePractice(
    language: Language = 'marathi',
    difficulty: string = 'level_1',
    topic: string = 'general'
  ): Promise<PracticeQuestion> {
    const res = await apiFetch(`${API_BASE}/practice/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language, difficulty, topic }),
    });
    if (!res.ok) throw new Error('Failed to generate practice question');
    return res.json();
  },

  async evaluatePractice(
    questionId: string,
    userAnswer: string,
    userScript: string = 'roman',
    selectedOptionId?: string
  ): Promise<PracticeEvaluateResponse> {
    const res = await apiFetch(`${API_BASE}/practice/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: questionId,
        selected_option_id: selectedOptionId,
        user_answer: userAnswer,
        user_script: userScript,
      }),
    });
    if (!res.ok) throw new Error('Failed to evaluate practice answer');
    return res.json();
  },

  // Gamification Hub Methods
  async getGamificationProfile(): Promise<import('../types').GamificationProfile> {
    const res = await apiFetch(`${API_BASE}/gamification/profile`);
    if (!res.ok) throw new Error('Failed to fetch gamification profile');
    return res.json();
  },

  async recordGamificationAction(payload: {
    action_type: string;
    xp_amount?: number;
    badge_id?: string;
    score?: number;
    scenario_id?: string;
    exercise_id?: string;
    answer_tokens?: string[];
    answers?: { question_id: string; answer: boolean | number }[];
    choice_ids?: string[];
  }): Promise<import('../types').GamificationProfile> {
    const res = await apiFetch(`${API_BASE}/gamification/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to record gamification action');
    return res.json();
  },

  async getSkillTree(): Promise<import('../types').SkillTreeNodeItem[]> {
    const res = await apiFetch(`${API_BASE}/gamification/skill-tree`);
    if (!res.ok) throw new Error('Failed to fetch skill tree');
    return res.json();
  },

  async getScrambleQuestions(): Promise<import('../types').ScrambleQuestionItem[]> {
    const res = await apiFetch(`${API_BASE}/gamification/scramble`);
    if (!res.ok) throw new Error('Failed to fetch sentence scramble questions');
    return res.json();
  },

  async getBlitzQuestions(): Promise<import('../types').BlitzQuestionItem[]> {
    const res = await apiFetch(`${API_BASE}/gamification/blitz`);
    if (!res.ok) throw new Error('Failed to fetch blitz questions');
    return res.json();
  },

  async getStreetScenarios(): Promise<import('../types').StreetScenarioItem[]> {
    const res = await apiFetch(`${API_BASE}/gamification/scenarios`);
    if (!res.ok) throw new Error('Failed to fetch street scenarios');
    return res.json();
  },

  // SRS Vocabulary Methods
  async getSrsReviewQueue(limit: number = 20): Promise<import('../types').SrsWordItem[]> {
    const res = await apiFetch(`${API_BASE}/vocabulary/review?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch vocabulary review queue');
    return res.json();
  },

  async recordSrsReview(wordId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<any> {
    const res = await apiFetch(`${API_BASE}/vocabulary/review/${wordId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating }),
    });
    if (!res.ok) throw new Error('Failed to record vocabulary review');
    return res.json();
  },

  async getVocabularyBoxes(): Promise<import('../types').VocabularyBoxStatistics> {
    const res = await apiFetch(`${API_BASE}/vocabulary/boxes`);
    if (!res.ok) throw new Error('Failed to fetch vocabulary box statistics');
    return res.json();
  },

  async getDailyQuest(): Promise<import('../types').DailyQuestData> {
    const res = await apiFetch(`${API_BASE}/vocabulary/daily-quest`);
    if (!res.ok) throw new Error('Failed to fetch daily quest data');
    return res.json();
  },

  // Pronunciation Evaluation Method
  async evaluatePronunciation(spokenText: string, targetPhrase: string): Promise<import('../types').PronunciationEvaluateResult> {
    const res = await apiFetch(`${API_BASE}/pronunciation/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spoken_text: spokenText, target_phrase: targetPhrase }),
    });
    if (!res.ok) throw new Error('Failed to evaluate pronunciation');
    return res.json();
  },
};
