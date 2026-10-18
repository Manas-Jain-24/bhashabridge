import React, { useState, useEffect } from 'react';
import { SrsWordItem, VocabularyBoxStatistics } from '../../types';
import { api } from '../../services/api';
import { speech } from '../../utils/speechEngine';
import { sfx } from '../../utils/soundEffects';
import { triggerConfetti } from '../../utils/confetti';
import {
  Layers,
  Volume2,
  RotateCw,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  HelpCircle,
  Award,
  Loader2,
  Calendar,
} from 'lucide-react';

interface SrsFlashcardsDeckProps {
  onXpEarned: (amount: number) => void;
}

export const SrsFlashcardsDeck: React.FC<SrsFlashcardsDeckProps> = ({ onXpEarned }) => {
  const [cards, setCards] = useState<SrsWordItem[]>([]);
  const [boxStats, setBoxStats] = useState<VocabularyBoxStatistics | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [isCompleted, setIsCompleted] = useState(false);

  const loadDeck = async () => {
    try {
      setLoading(true);
      const [queueData, statsData] = await Promise.all([
        api.getSrsReviewQueue(20),
        api.getVocabularyBoxes(),
      ]);
      setCards(queueData);
      setBoxStats(statsData);
      setCurrentIndex(0);
      setIsFlipped(false);
      setIsCompleted(false);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDeck();
  }, []);

  const currentCard = cards[currentIndex];

  const handleFlip = () => {
    sfx.playTileClick();
    setIsFlipped(!isFlipped);
  };

  const handlePronounce = (e: React.MouseEvent, text: string) => {
    e.stopPropagation();
    speech.speak(text, 'marathi');
  };

  const handleRate = async (rating: 'again' | 'hard' | 'good' | 'easy') => {
    if (!currentCard) return;

    if (rating === 'good' || rating === 'easy') {
      sfx.playSuccessChime();
      const xp = rating === 'easy' ? 25 : 15;
      onXpEarned(xp);
    } else {
      sfx.playErrorBuzz();
    }

    try {
      await api.recordSrsReview(currentCard.id, rating);
      // Refresh box statistics in background
      api.getVocabularyBoxes().then(setBoxStats).catch(() => {});
    } catch (e) {
      console.error(e);
    }

    const nextIdx = currentIndex + 1;
    if (nextIdx < cards.length) {
      setCurrentIndex(nextIdx);
      setIsFlipped(false);
    } else {
      setIsCompleted(true);
      sfx.playVictoryFanfare();
      triggerConfetti();
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-3 text-slate-400">
        <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
        <p className="text-sm">Loading Spaced Repetition Flashcard Deck...</p>
      </div>
    );
  }

  // Completed Deck Screen
  if (isCompleted || cards.length === 0) {
    return (
      <div className="max-w-xl mx-auto rounded-3xl p-8 sm:p-10 bg-slate-900/90 border border-emerald-500/40 text-center space-y-6 shadow-2xl backdrop-blur-xl animate-in zoom-in-95">
        <div className="w-20 h-20 mx-auto rounded-3xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center text-4xl shadow-xl shadow-emerald-500/30">
          🎉
        </div>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Deck Completed!</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white">Daily Revision Finished</h2>
          <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
            All due vocabulary cards for today have been reviewed according to Leitner spaced repetition intervals.
          </p>
        </div>

        {boxStats && (
          <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-indigo-300">
            Total Mastered Words: <span className="font-bold text-white text-sm">{boxStats.mastered_words}</span> / {boxStats.total_words} words in your active bank.
          </div>
        )}

        <div>
          <button
            onClick={loadDeck}
            className="px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-all"
          >
            Review Deck Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Top Leitner Box Distribution Bar */}
      {boxStats && (
        <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-2.5 shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Leitner 5-Box Distribution</span>
            </span>
            <span className="font-mono text-indigo-300">
              Card {currentIndex + 1} of {cards.length}
            </span>
          </div>

          <div className="grid grid-cols-5 gap-1.5">
            {boxStats.box_distribution.map((b) => (
              <div
                key={b.box}
                className={`p-2 rounded-xl border text-center transition-all ${
                  currentCard.box_level === b.box
                    ? 'bg-indigo-950/80 border-indigo-500 shadow-md ring-1 ring-indigo-400/50'
                    : 'bg-slate-950/60 border-slate-800/80'
                }`}
              >
                <div className="text-[10px] text-slate-400 font-bold uppercase truncate">
                  Box {b.box}
                </div>
                <div className="text-xs font-black text-white font-mono mt-0.5">
                  {b.count}
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5">{b.interval}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3D Flippable Flashcard */}
      <div
        onClick={handleFlip}
        className="cursor-pointer min-h-[320px] sm:min-h-[360px] rounded-3xl p-8 sm:p-10 bg-gradient-to-br from-slate-900/95 via-indigo-950/40 to-slate-900/95 border border-indigo-500/30 hover:border-indigo-500/50 shadow-2xl transition-all duration-300 hover:scale-[1.01] flex flex-col justify-between select-none relative group"
      >
        {/* Top Card Bar */}
        <div className="flex items-center justify-between">
          <span className="px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
            Box {currentCard.box_level} • Reps: {currentCard.repetition_count}
          </span>

          <button
            onClick={(e) => handlePronounce(e, currentCard.devanagari)}
            title="Listen to native Marathi pronunciation"
            className="p-2.5 rounded-2xl bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/30 text-indigo-300 hover:text-white transition-all shadow-sm"
          >
            <Volume2 className="w-5 h-5" />
          </button>
        </div>

        {/* Center Card Content (Front vs Back) */}
        {!isFlipped ? (
          /* FRONT: Devanagari & Phonetic Roman */
          <div className="text-center space-y-4 my-auto">
            <div className="text-4xl sm:text-5xl font-black text-white font-devanagari tracking-wide drop-shadow-md">
              {currentCard.devanagari}
            </div>
            <div className="text-base sm:text-lg font-mono text-indigo-300 font-semibold">
              {currentCard.roman}
            </div>
            <p className="text-xs text-slate-500 italic mt-2">
              (Click card to flip and check Hindi/English meaning)
            </p>
          </div>
        ) : (
          /* BACK: Hindi & English Meanings */
          <div className="text-center space-y-4 my-auto animate-in fade-in duration-200">
            <div className="space-y-1">
              <span className="text-[11px] uppercase tracking-wider font-bold text-slate-400">
                Hindi Meaning
              </span>
              <div className="text-2xl sm:text-3xl font-extrabold text-amber-300 font-devanagari">
                {currentCard.hindi_meaning || currentCard.english_meaning}
              </div>
            </div>

            <div className="space-y-1 pt-2 border-t border-slate-800/80">
              <span className="text-[11px] uppercase tracking-wider font-bold text-slate-400">
                English Translation
              </span>
              <div className="text-lg font-semibold text-slate-200 italic">
                "{currentCard.english_meaning}"
              </div>
            </div>

            {currentCard.topic && (
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-xs font-mono">
                <span>Topic: {currentCard.topic}</span>
              </div>
            )}
          </div>
        )}

        {/* Bottom Card Footer */}
        <div className="flex items-center justify-between text-xs text-slate-500 pt-4 border-t border-slate-800/80">
          <span>{isFlipped ? 'Answer Revealed' : 'Devanagari Front'}</span>
          <span className="flex items-center gap-1 text-indigo-400 group-hover:translate-x-1 transition-transform">
            <RotateCw className="w-3.5 h-3.5" />
            <span>Tap to flip</span>
          </span>
        </div>
      </div>

      {/* Leitner Rating Controls */}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-slate-400 text-center">
          How well do you know this word? (Adjusts Leitner review interval):
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <button
            onClick={() => handleRate('again')}
            className="py-3 px-4 rounded-2xl font-bold text-xs sm:text-sm bg-rose-950/60 hover:bg-rose-900/80 border border-rose-500/40 text-rose-200 shadow-sm transition-all hover:scale-105 active:scale-95"
          >
            <div className="font-extrabold">🔴 Again</div>
            <div className="text-[10px] opacity-70">Reset (1 Day)</div>
          </button>

          <button
            onClick={() => handleRate('hard')}
            className="py-3 px-4 rounded-2xl font-bold text-xs sm:text-sm bg-amber-950/60 hover:bg-amber-900/80 border border-amber-500/40 text-amber-200 shadow-sm transition-all hover:scale-105 active:scale-95"
          >
            <div className="font-extrabold">🟡 Hard</div>
            <div className="text-[10px] opacity-70">Review in 2 Days</div>
          </button>

          <button
            onClick={() => handleRate('good')}
            className="py-3 px-4 rounded-2xl font-bold text-xs sm:text-sm bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-500/40 text-indigo-200 shadow-sm transition-all hover:scale-105 active:scale-95"
          >
            <div className="font-extrabold">🟢 Good</div>
            <div className="text-[10px] opacity-70">+1 Box (+15 XP)</div>
          </button>

          <button
            onClick={() => handleRate('easy')}
            className="py-3 px-4 rounded-2xl font-bold text-xs sm:text-sm bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-500/40 text-emerald-200 shadow-sm transition-all hover:scale-105 active:scale-95"
          >
            <div className="font-extrabold">🌟 Easy</div>
            <div className="text-[10px] opacity-70">Mastered (+25 XP)</div>
          </button>
        </div>
      </div>
    </div>
  );
};
