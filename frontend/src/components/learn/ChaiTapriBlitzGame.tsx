import React, { useState, useEffect, useRef } from 'react';
import { BlitzQuestionItem } from '../../types';
import { sfx } from '../../utils/soundEffects';
import { triggerConfetti } from '../../utils/confetti';
import {
  Timer,
  Flame,
  Award,
  Zap,
  RotateCcw,
  CheckCircle2,
  XCircle,
  Trophy,
  ArrowRight,
  Play,
} from 'lucide-react';

interface ChaiTapriBlitzGameProps {
  questions: BlitzQuestionItem[];
  highScore: number;
  onGameEnd: (finalScore: number) => void;
}

export const ChaiTapriBlitzGame: React.FC<ChaiTapriBlitzGameProps> = ({
  questions,
  highScore,
  onGameEnd,
}) => {
  const [gameState, setGameState] = useState<'idle' | 'playing' | 'gameover'>('idle');
  const [timeLeft, setTimeLeft] = useState(60);
  const [score, setScore] = useState(0);
  const [combo, setCombo] = useState(1);
  const [currentIdx, setCurrentIdx] = useState(0);

  const [feedback, setFeedback] = useState<{
    type: 'correct' | 'wrong';
    text: string;
  } | null>(null);

  const timerRef = useRef<any>(null);

  const currentQ = questions[currentIdx] || questions[0];

  // Start game loop
  const startGame = () => {
    sfx.playTileClick();
    setScore(0);
    setCombo(1);
    setTimeLeft(60);
    setCurrentIdx(0);
    setFeedback(null);
    setGameState('playing');
  };

  useEffect(() => {
    if (gameState === 'playing') {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            endGame();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [gameState]);

  const endGame = () => {
    setGameState('gameover');
    sfx.playVictoryFanfare();
    triggerConfetti();
    onGameEnd(score);
  };

  const handleAnswer = (userChoice: boolean | number) => {
    if (gameState !== 'playing' || !currentQ) return;

    let isCorrect = false;

    if (currentQ.type === 'true_false') {
      isCorrect = userChoice === currentQ.is_true;
    } else {
      isCorrect = userChoice === currentQ.correct_index;
    }

    if (isCorrect) {
      const addedPoints = currentQ.points * combo;
      setScore((s) => s + addedPoints);
      setCombo((c) => Math.min(5, c + 1));
      sfx.playComboFlame(combo);
      setFeedback({
        type: 'correct',
        text: `+${addedPoints} pts! ${currentQ.explanation}`,
      });
    } else {
      setCombo(1);
      sfx.playErrorBuzz();
      setFeedback({
        type: 'wrong',
        text: `Oops! ${currentQ.explanation}`,
      });
    }

    // Advance to next question after tiny delay
    setTimeout(() => {
      setFeedback(null);
      setCurrentIdx((prev) => (prev + 1) % questions.length);
    }, 900);
  };

  // Idle Start Screen
  if (gameState === 'idle') {
    return (
      <div className="max-w-xl mx-auto rounded-3xl p-8 sm:p-10 bg-gradient-to-br from-amber-950/60 via-slate-900/90 to-orange-950/60 border border-amber-500/30 text-center space-y-6 shadow-2xl backdrop-blur-xl animate-in zoom-in-95">
        <div className="w-20 h-20 mx-auto rounded-3xl bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center text-4xl shadow-xl shadow-orange-500/20 ring-4 ring-orange-500/30 animate-bounce">
          ☕
        </div>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/20 border border-orange-500/30 text-orange-300 text-xs font-bold uppercase tracking-wider">
            <Flame className="w-3.5 h-3.5 fill-current" />
            <span>Chai Tapri 60s Blitz</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white">Rapid-Fire Marathi Arcade</h2>
          <p className="text-sm text-slate-300 max-w-md mx-auto leading-relaxed">
            Answer as many Marathi vocab, false friends, and grammar questions as possible in 60 seconds. Build your flame multiplier up to <span className="text-amber-300 font-bold">5x</span>!
          </p>
        </div>

        {/* High Score Banner */}
        <div className="inline-flex items-center gap-3 px-5 py-2.5 rounded-2xl bg-slate-900/90 border border-amber-500/30 text-sm">
          <Trophy className="w-4 h-4 text-amber-400" />
          <span className="text-slate-400">Current Tapri High Score:</span>
          <span className="font-extrabold text-amber-300 font-mono text-base">{highScore} pts</span>
        </div>

        <div>
          <button
            onClick={startGame}
            className="w-full sm:w-auto px-10 py-4 rounded-2xl font-extrabold text-lg bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 hover:from-amber-400 hover:to-orange-400 text-white shadow-xl shadow-orange-500/30 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-3 mx-auto"
          >
            <Play className="w-5 h-5 fill-current" />
            <span>Start 60s Challenge</span>
          </button>
        </div>
      </div>
    );
  }

  // Game Over Scoreboard Screen
  if (gameState === 'gameover') {
    const isNewHigh = score > highScore;
    return (
      <div className="max-w-xl mx-auto rounded-3xl p-8 sm:p-10 bg-slate-900/90 border border-indigo-500/40 text-center space-y-6 shadow-2xl backdrop-blur-xl animate-in zoom-in-95">
        <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-4xl shadow-xl shadow-indigo-500/30">
          🏆
        </div>

        <div className="space-y-2">
          <h2 className="text-3xl font-extrabold text-white">Time's Up!</h2>
          <p className="text-sm text-slate-400">Great effort on the street trivia!</p>
        </div>

        {/* Score Card */}
        <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-4">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider">
            Final Score
          </div>
          <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-orange-400 to-indigo-300 font-mono">
            {score}
          </div>

          {isNewHigh && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-bold animate-pulse">
              <Flame className="w-3.5 h-3.5 fill-current" />
              <span>NEW PERSONAL BEST!</span>
            </div>
          )}

          <div className="text-xs text-indigo-300 pt-2 border-t border-slate-800">
            Earned <span className="font-bold text-white">+{Math.max(20, Math.floor(score / 5))} XP</span> added to your profile!
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={startGame}
            className="px-6 py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95 flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Play Again</span>
          </button>
        </div>
      </div>
    );
  }

  // Active 60s Playing View
  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Top Status Bar: Timer, Score, Multiplier Flame */}
      <div className="grid grid-cols-3 items-center gap-3 p-4 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-lg">
        {/* Timer */}
        <div className="flex items-center gap-2">
          <div className={`p-2 rounded-xl ${timeLeft <= 10 ? 'bg-rose-500/20 text-rose-400 animate-ping' : 'bg-slate-800 text-slate-300'}`}>
            <Timer className="w-5 h-5" />
          </div>
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Time</div>
            <div className={`text-xl font-black font-mono ${timeLeft <= 10 ? 'text-rose-400' : 'text-white'}`}>
              {timeLeft}s
            </div>
          </div>
        </div>

        {/* Score */}
        <div className="text-center">
          <div className="text-[10px] text-slate-400 uppercase font-semibold">Score</div>
          <div className="text-2xl font-black text-amber-300 font-mono">{score}</div>
        </div>

        {/* Multiplier Combo Flame */}
        <div className="flex items-center justify-end gap-2">
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Multiplier</div>
            <div className="text-lg font-black text-orange-400 font-mono">x{combo}</div>
          </div>
          <div className={`p-2 rounded-xl ${combo > 1 ? 'bg-orange-500/20 text-orange-400 animate-bounce' : 'bg-slate-800 text-slate-600'}`}>
            <Flame className="w-5 h-5 fill-current" />
          </div>
        </div>
      </div>

      {/* Progress Bar for Time */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-1000 ${
            timeLeft <= 10 ? 'bg-rose-500' : 'bg-gradient-to-r from-amber-500 to-orange-500'
          }`}
          style={{ width: `${(timeLeft / 60) * 100}%` }}
        />
      </div>

      {/* Question Card */}
      <div className="rounded-3xl p-6 sm:p-8 bg-slate-900/90 border border-slate-800 shadow-xl space-y-6 text-center">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800 text-slate-400 text-xs font-mono">
          <span>Question {currentIdx + 1}</span>
          <span>•</span>
          <span className="capitalize">{currentQ.concept.replace('_', ' ')}</span>
        </div>

        <div className="text-xl sm:text-2xl font-bold text-white font-devanagari leading-snug">
          {currentQ.question}
        </div>

        {currentQ.question_roman && (
          <div className="text-xs sm:text-sm text-slate-400 font-mono">
            {currentQ.question_roman}
          </div>
        )}

        {/* Answer Options */}
        {currentQ.type === 'true_false' ? (
          <div className="grid grid-cols-2 gap-4 pt-2">
            <button
              onClick={() => handleAnswer(true)}
              className="py-4 px-6 rounded-2xl font-extrabold text-base sm:text-lg bg-emerald-600/90 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2 border border-emerald-400/40"
            >
              <CheckCircle2 className="w-6 h-6" />
              <span>TRUE (बरोबर)</span>
            </button>

            <button
              onClick={() => handleAnswer(false)}
              className="py-4 px-6 rounded-2xl font-extrabold text-base sm:text-lg bg-rose-600/90 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2 border border-rose-400/40"
            >
              <XCircle className="w-6 h-6" />
              <span>FALSE (चूक)</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
            {currentQ.options?.map((opt, optIdx) => (
              <button
                key={optIdx}
                onClick={() => handleAnswer(optIdx)}
                className="py-3 px-4 rounded-xl font-bold text-sm sm:text-base bg-slate-800 hover:bg-indigo-600 border border-slate-700 text-white transition-all hover:scale-105 active:scale-95 font-devanagari"
              >
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* Live Feedback Toast */}
        {feedback && (
          <div
            className={`p-3 rounded-xl text-xs font-semibold animate-in fade-in duration-200 ${
              feedback.type === 'correct'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
            }`}
          >
            {feedback.text}
          </div>
        )}
      </div>
    </div>
  );
};
