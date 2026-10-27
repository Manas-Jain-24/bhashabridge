import React, { useState, useRef } from 'react';
import { ScrambleQuestionItem, ScrambleTileItem } from '../../types';
import { sfx } from '../../utils/soundEffects';
import { triggerConfetti } from '../../utils/confetti';
import {
  Sparkles,
  HelpCircle,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Lightbulb,
  Check,
  X,
} from 'lucide-react';

interface SentenceScrambleGameProps {
  questions: ScrambleQuestionItem[];
  onCompleteExercise: (exerciseId: string, tokens: string[]) => Promise<number>;
  onHeartLost: () => void;
}

export const SentenceScrambleGame: React.FC<SentenceScrambleGameProps> = ({
  questions,
  onCompleteExercise,
  onHeartLost,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const currentQ = questions[currentIndex] || questions[0];

  // Assembled tiles list
  const [assembledTiles, setAssembledTiles] = useState<ScrambleTileItem[]>([]);
  // Remaining pool of tiles
  const [availableTiles, setAvailableTiles] = useState<ScrambleTileItem[]>(
    currentQ ? currentQ.tiles : []
  );

  const [evaluation, setEvaluation] = useState<{
    checked: boolean;
    isCorrect: boolean;
    trapsTriggered: ScrambleTileItem[];
  } | null>(null);

  const [showTip, setShowTip] = useState(false);
  const saving = useRef(false);
  const [savedXp, setSavedXp] = useState(0);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Switch question
  const loadQuestion = (index: number) => {
    const q = questions[index];
    if (!q) return;
    setCurrentIndex(index);
    setAssembledTiles([]);
    setAvailableTiles(q.tiles);
    setEvaluation(null);
    setShowTip(false);
  };

  const handleTileClick = (tile: ScrambleTileItem) => {
    sfx.playTileClick();
    // Move from available to assembled
    setAvailableTiles((prev) => prev.filter((t) => t.id !== tile.id));
    setAssembledTiles((prev) => [...prev, tile]);
    setEvaluation(null); // Clear previous eval state on edit
  };

  const handleRemoveTile = (tile: ScrambleTileItem) => {
    sfx.playTileClick();
    // Move back to available
    setAssembledTiles((prev) => prev.filter((t) => t.id !== tile.id));
    setAvailableTiles((prev) => [...prev, tile]);
    setEvaluation(null);
  };

  const handleReset = () => {
    sfx.playTileClick();
    setAssembledTiles([]);
    setAvailableTiles(currentQ.tiles);
    setEvaluation(null);
  };

  const handleCheckAnswer = async () => {
    if (assembledTiles.length === 0 || saving.current || evaluation?.isCorrect) return;
    setSaveError(null);

    const assembledTokens = assembledTiles.map((t) => t.token);
    const targetTokens = currentQ.target_tokens;

    // Check if matches target sentence exactly
    const isExactMatch =
      assembledTokens.length === targetTokens.length &&
      assembledTokens.every((token, idx) => token === targetTokens[idx]);

    // Check if any trap distractor was included
    const traps = assembledTiles.filter((t) => t.is_distractor);

    if (isExactMatch) {
      saving.current = true;
      try { setSavedXp(await onCompleteExercise(currentQ.id, assembledTokens)); }
      catch { setSaveError('Could not save this exercise. Please check your connection and retry.'); return; }
      finally { saving.current = false; }
      sfx.playSuccessChime();
      triggerConfetti();
      setEvaluation({
        checked: true,
        isCorrect: true,
        trapsTriggered: [],
      });

    } else {
      sfx.playErrorBuzz();
      setEvaluation({
        checked: true,
        isCorrect: false,
        trapsTriggered: traps,
      });
      onHeartLost();
    }
  };

  const handleNext = () => {
    sfx.playTileClick();
    const nextIdx = (currentIndex + 1) % questions.length;
    loadQuestion(nextIdx);
  };

  if (!currentQ) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading sentence questions...
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      {saveError && <p role="alert" className="text-rose-300 text-sm">{saveError}</p>}
      {/* Header & Question Tracker */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-bold text-indigo-400 tracking-wider">
              Sentence Builder Scramble
            </span>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-slate-400 font-mono">
              Challenge {currentIndex + 1} of {questions.length}
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-white mt-1">
            Assemble the Marathi Sentence
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTip(!showTip)}
            title="Grammar Tip"
            className="p-2 rounded-xl bg-slate-900 border border-slate-700/80 hover:bg-slate-800 text-amber-400 hover:text-amber-300 transition-all"
          >
            <Lightbulb className="w-5 h-5" />
          </button>
          <button
            onClick={handleReset}
            title="Reset Sentence"
            className="p-2 rounded-xl bg-slate-900 border border-slate-700/80 hover:bg-slate-800 text-slate-300 hover:text-white transition-all"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Grammar Tip Accordion */}
      {showTip && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs sm:text-sm flex items-start gap-3 animate-in slide-in-from-top-2">
          <Lightbulb className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-amber-300">Grammar Guidance</p>
            <p className="text-amber-200/90 leading-relaxed">{currentQ.grammar_tip}</p>
          </div>
        </div>
      )}

      {/* Prompt Card */}
      <div className="rounded-3xl p-6 sm:p-7 bg-gradient-to-br from-slate-900/90 to-indigo-950/40 border border-slate-800 shadow-xl space-y-3">
        <div className="text-xs font-semibold uppercase text-slate-400 tracking-wide">
          Translate to Marathi (Watch out for trap words!)
        </div>
        <div className="text-xl sm:text-2xl font-bold text-white font-devanagari">
          {currentQ.prompt_hindi}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
          <span className="font-mono text-indigo-300">{currentQ.prompt_roman}</span>
          <span>•</span>
          <span className="italic text-slate-300">"{currentQ.english_meaning}"</span>
        </div>
      </div>

      {/* Assembled Sentence Dock */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1">
          <span>Your Assembled Marathi Sentence:</span>
          <span className="text-[11px] text-slate-500">Tap word to return to bank</span>
        </div>

        <div className="min-h-[72px] sm:min-h-[80px] p-4 rounded-2xl bg-slate-950/90 border-2 border-dashed border-indigo-500/30 flex flex-wrap items-center gap-2.5 transition-all">
          {assembledTiles.length === 0 ? (
            <span className="text-slate-500 text-sm italic select-none">
              Click tiles below to build the sentence in order...
            </span>
          ) : (
            assembledTiles.map((tile, idx) => (
              <button
                key={tile.id}
                onClick={() => handleRemoveTile(tile)}
                className="group relative px-4 py-2 rounded-xl bg-gradient-to-b from-indigo-600 to-indigo-700 hover:from-rose-600 hover:to-rose-700 text-white shadow-md border border-indigo-400/30 text-base sm:text-lg font-bold font-devanagari transition-all hover:scale-105 active:scale-95 flex items-center gap-1.5"
              >
                <span>{tile.token}</span>
                <span className="text-[11px] font-mono opacity-70">({tile.roman})</span>
                <X className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity ml-0.5" />
              </button>
            ))
          )}
        </div>
      </div>

      {/* Available Tiles Bank */}
      <div className="space-y-2 pt-2">
        <div className="text-xs text-slate-400 px-1 flex items-center justify-between">
          <span>Available Word Tiles:</span>
          <span className="text-[11px] text-amber-400/90 font-medium">
            ⚠️ Contains intentional false friends & trap distractors
          </span>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center gap-3">
          {availableTiles.length === 0 ? (
            <span className="text-xs text-slate-500">All tiles selected above.</span>
          ) : (
            availableTiles.map((tile) => (
              <button
                key={tile.id}
                onClick={() => handleTileClick(tile)}
                className="px-4 py-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 border border-slate-700 text-slate-100 hover:text-white shadow-sm text-base sm:text-lg font-bold font-devanagari transition-all hover:scale-105 active:scale-95 flex items-center gap-2 group"
              >
                <span>{tile.token}</span>
                <span className="text-xs font-mono text-indigo-300 font-normal">
                  {tile.roman}
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Evaluation Feedback Banner */}
      {evaluation && (
        <div
          className={`p-5 rounded-2xl border animate-in zoom-in-95 duration-200 ${
            evaluation.isCorrect
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/40 border-rose-500/40 text-rose-200'
          }`}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-bold text-base">
                {evaluation.isCorrect ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    <span>कडक! Perfectly assembled! (+{savedXp} XP)</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                    <span>Not quite right. Review the differences below:</span>
                  </>
                )}
              </div>

              {/* Trap explanation if traps were clicked */}
              {evaluation.trapsTriggered.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <div className="text-xs font-bold uppercase tracking-wider text-amber-300">
                    Trap Distractors Detected:
                  </div>
                  {evaluation.trapsTriggered.map((trap, tIdx) => (
                    <div
                      key={tIdx}
                      className="p-2.5 rounded-xl bg-slate-950/60 border border-amber-500/30 text-xs text-amber-200 flex items-start gap-2"
                    >
                      <span className="font-bold font-devanagari text-white bg-rose-500/20 px-2 py-0.5 rounded border border-rose-500/30">
                        {trap.token}
                      </span>
                      <span>{trap.trap_explanation}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Expected answer reveal */}
              {!evaluation.isCorrect && (
                <div className="text-xs text-slate-300 pt-2 border-t border-slate-800/80">
                  <span className="text-slate-400">Correct order: </span>
                  <span className="font-bold text-white font-devanagari">
                    {currentQ.target_sentence_devanagari}
                  </span>
                  <span className="font-mono text-indigo-300 ml-2">
                    ({currentQ.target_sentence_roman})
                  </span>
                </div>
              )}
            </div>

            {/* Next Button */}
            {evaluation.isCorrect && (
              <button
                onClick={handleNext}
                className="px-5 py-2.5 rounded-xl font-bold text-sm bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition-all hover:scale-105 active:scale-95 shrink-0 flex items-center gap-2"
              >
                <span>Next</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={handleReset}
          className="px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold text-slate-400 hover:text-white bg-slate-900 border border-slate-800 transition-colors"
        >
          Clear Tiles
        </button>

        <button
          onClick={handleCheckAnswer}
          disabled={assembledTiles.length === 0}
          className="px-7 py-3 rounded-2xl font-bold text-sm sm:text-base bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02] active:scale-[0.98] flex items-center gap-2"
        >
          <Check className="w-5 h-5" />
          <span>Check Answer</span>
        </button>
      </div>
    </div>
  );
};
