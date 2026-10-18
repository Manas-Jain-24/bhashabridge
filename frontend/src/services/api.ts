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
    preferredScript: ScriptMode = 'both'
  ): Promise<AnalyzeResponse> {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        source_language: sourceLanguage,
        target_language: targetLanguage,
        preferred_script: preferredScript,
      }),
    });
    if (!res.ok) throw new Error('Analysis failed');
    return res.json();
  },

  async transliterate(
    text: string,
    language: Language = 'marathi',
    direction: 'latin_to_devanagari' | 'devanagari_to_latin' = 'latin_to_devanagari'
  ): Promise<{ input: string; output: string; detected_script: string }> {
    const res = await fetch(`${API_BASE}/transliterate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, direction }),
    });
    if (!res.ok) throw new Error('Transliteration failed');
    return res.json();
  },

  async getProgress(): Promise<ProgressData> {
    const res = await fetch(`${API_BASE}/progress`);
    if (!res.ok) throw new Error('Failed to fetch progress');
    return res.json();
  },

  async getMilestones(): Promise<import('../types').MilestoneRoadmapItem[]> {
    const res = await fetch(`${API_BASE}/progress/milestones`);
    if (!res.ok) throw new Error('Failed to fetch milestones roadmap');
    return res.json();
  },

  async updateBridgeMode(mode: string): Promise<{ status: string; updated_mode: string; message: string }> {
    const res = await fetch(`${API_BASE}/progress/bridge-mode`, {
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
    const res = await fetch(`${API_BASE}/practice/generate`, {
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
    userScript: string = 'roman'
  ): Promise<PracticeEvaluateResponse> {
    const res = await fetch(`${API_BASE}/practice/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: questionId,
        user_answer: userAnswer,
        user_script: userScript,
      }),
    });
    if (!res.ok) throw new Error('Failed to evaluate practice answer');
    return res.json();
  },

  // Gamification Hub Methods
  async getGamificationProfile(): Promise<import('../types').GamificationProfile> {
    const res = await fetch(`${API_BASE}/gamification/profile`);
    if (!res.ok) throw new Error('Failed to fetch gamification profile');
    return res.json();
  },

  async recordGamificationAction(payload: {
    action_type: string;
    xp_amount?: number;
    badge_id?: string;
    score?: number;
    scenario_id?: string;
  }): Promise<import('../types').GamificationProfile> {
    const res = await fetch(`${API_BASE}/gamification/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to record gamification action');
    return res.json();
  },

  async getSkillTree(): Promise<import('../types').SkillTreeNodeItem[]> {
    const res = await fetch(`${API_BASE}/gamification/skill-tree`);
    if (!res.ok) throw new Error('Failed to fetch skill tree');
    return res.json();
  },

  async getScrambleQuestions(): Promise<import('../types').ScrambleQuestionItem[]> {
    const res = await fetch(`${API_BASE}/gamification/scramble`);
    if (!res.ok) throw new Error('Failed to fetch sentence scramble questions');
    return res.json();
  },

  async getBlitzQuestions(): Promise<import('../types').BlitzQuestionItem[]> {
    const res = await fetch(`${API_BASE}/gamification/blitz`);
    if (!res.ok) throw new Error('Failed to fetch blitz questions');
    return res.json();
  },

  async getStreetScenarios(): Promise<import('../types').StreetScenarioItem[]> {
    const res = await fetch(`${API_BASE}/gamification/scenarios`);
    if (!res.ok) throw new Error('Failed to fetch street scenarios');
    return res.json();
  },

  // SRS Vocabulary Methods
  async getSrsReviewQueue(limit: number = 20): Promise<import('../types').SrsWordItem[]> {
    const res = await fetch(`${API_BASE}/vocabulary/review?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch vocabulary review queue');
    return res.json();
  },

  async recordSrsReview(wordId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<any> {
    const res = await fetch(`${API_BASE}/vocabulary/review/${wordId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating }),
    });
    if (!res.ok) throw new Error('Failed to record vocabulary review');
    return res.json();
  },

  async getVocabularyBoxes(): Promise<import('../types').VocabularyBoxStatistics> {
    const res = await fetch(`${API_BASE}/vocabulary/boxes`);
    if (!res.ok) throw new Error('Failed to fetch vocabulary box statistics');
    return res.json();
  },

  async getDailyQuest(): Promise<import('../types').DailyQuestData> {
    const res = await fetch(`${API_BASE}/vocabulary/daily-quest`);
    if (!res.ok) throw new Error('Failed to fetch daily quest data');
    return res.json();
  },

  // Pronunciation Evaluation Method
  async evaluatePronunciation(spokenText: string, targetPhrase: string): Promise<import('../types').PronunciationEvaluateResult> {
    const res = await fetch(`${API_BASE}/pronunciation/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ spoken_text: spokenText, target_phrase: targetPhrase }),
    });
    if (!res.ok) throw new Error('Failed to evaluate pronunciation');
    return res.json();
  },
};
