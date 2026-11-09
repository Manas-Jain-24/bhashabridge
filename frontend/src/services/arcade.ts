import type { Language } from '../config/languages';
export type GameMode = 'recognize' | 'spell' | 'meaning' | 'sprint';
export type Difficulty = 'beginner' | 'intermediate' | 'advanced';
export type Practice = 'mixed' | 'new' | 'review';
export interface GameQuestion { id: string; prompt: string; source: string; options?: {id: string; text: string}[]; tiles?: string[]; }
export interface GameFeedback { question_id: string; correct: boolean; reference: string; roman: string; xp_awarded: number; lesson_completed?: boolean; completion_xp?: number; }
export interface GameSession { session_id: string; language: Language; mode: GameMode; difficulty: Difficulty; practice: Practice; lesson_id?: string; score: number; correct: number; answered: number; total: number; lives: number; remaining_seconds: number; done: boolean; question: GameQuestion | null; feedback?: GameFeedback; }
export interface ArcadeStats { language: Language; xp: number; level: number; next_level_xp: number; correct_first_awards: number; best_score: number; badges: string[]; available: Record<GameMode, number>; available_by_difficulty: Record<Difficulty, Record<GameMode, number>>; review_due: Record<Difficulty, Record<GameMode,number>>; mastered_items: number; completed_lessons: string[]; topic_counts:Record<string,number>; }
export async function arcadeRequest<T>(path: string, body?: object, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api/arcade/' + path, {method: body ? 'POST' : 'GET', signal,
    headers: body ? {'Content-Type':'application/json'} : undefined, body: body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not save this game. Please retry.');
  return data;
}
