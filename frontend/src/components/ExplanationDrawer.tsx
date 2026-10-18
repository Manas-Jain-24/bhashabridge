import React, { useState, useMemo } from 'react';
import { AnalyzeResponse } from '../types';
import { 
  X, 
  Sparkles, 
  BookOpen, 
  AlertTriangle, 
  Layers, 
  CheckCircle2, 
  Volume2, 
  Copy, 
  Check, 
  Lightbulb, 
  ArrowRight,
  Target,
  RotateCcw,
  Zap,
  GitCompare,
  Languages
} from 'lucide-react';
import { speech } from '../utils/speechEngine';
import { sfx } from '../utils/soundEffects';
import { triggerConfetti } from '../utils/confetti';

interface ExplanationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  data: AnalyzeResponse | null;
}

export const ExplanationDrawer: React.FC<ExplanationDrawerProps> = ({
  isOpen,
  onClose,
  data,
}) => {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Interactive Word Chips & Morphological Inspector state
  const [selectedWordIndex, setSelectedWordIndex] = useState<number | null>(0);
  const [hoveredWordIndex, setHoveredWordIndex] = useState<number | null>(null);

  // Mini-Quiz interactive state
  const [quizIndex, setQuizIndex] = useState<number>(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [quizStatus, setQuizStatus] = useState<'unanswered' | 'correct' | 'incorrect'>('unanswered');

  if (!isOpen || !data) return null;

  const handleSpeak = (text: string, index: number) => {
    setPlayingIndex(index);
    speech.speak(text, 'marathi', 0.85, () => {
      setPlayingIndex(null);
    });
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const primaryRule = data.grammar_explanation && data.grammar_explanation.length > 0
    ? data.grammar_explanation[0]
    : null;

  const activeIndex = hoveredWordIndex !== null ? hoveredWordIndex : selectedWordIndex;
  const activeWord = (data.vocabulary && activeIndex !== null && data.vocabulary[activeIndex])
    ? data.vocabulary[activeIndex]
    : (data.vocabulary && data.vocabulary.length > 0 ? data.vocabulary[0] : null);

  // Active quiz question derived from current example
  const currentExample = data.examples && data.examples.length > 0
    ? data.examples[quizIndex % data.examples.length]
    : null;

  // Generate 3 plausible choices with common learner trap distractors
  const quizOptions = useMemo(() => {
    if (!currentExample) return [];

    const correct = currentExample.target_sentence;

    // Distractor 1: Subject Trap (e.g. replacing dative 'मला' with nominative 'मी')
    let distractor1 = correct;
    if (correct.includes('मला')) {
      distractor1 = correct.replace('मला', 'मी');
    } else if (correct.includes('मी')) {
      distractor1 = correct.replace('मी', 'मला');
    } else if (correct.includes('आम्ही')) {
      distractor1 = correct.replace('आम्ही', 'आपण');
    } else if (correct.includes('उद्या')) {
      distractor1 = correct.replace('उद्या', 'काल');
    } else {
      distractor1 = correct.replace('आहे', 'होता');
    }
    if (distractor1 === correct) {
      distractor1 = correct + ' का?';
    }

    // Distractor 2: Verb / Suffix Trap (e.g. replacing modal 'पाहिजे' with 'आहे' or changing verb ending)
    let distractor2 = correct;
    if (correct.includes('पाहिजे')) {
      distractor2 = correct.replace('पाहिजे', 'आहे');
    } else if (correct.includes('जायचं')) {
      distractor2 = correct.replace('जायचं', 'जातो');
    } else if (correct.includes('करायचं')) {
      distractor2 = correct.replace('करायचं', 'करतो');
    } else if (correct.includes('शिकायची')) {
      distractor2 = correct.replace('शिकायची', 'शिकायचा');
    } else if (correct.includes('घरी')) {
      distractor2 = correct.replace('घरी', 'घर');
    } else {
      distractor2 = correct.replace('आहे', 'नाही');
    }
    if (distractor2 === correct || distractor2 === distractor1) {
      distractor2 = distractor1.replace('आहे', 'नाही');
    }

    // Deterministic shuffle based on quizIndex
    const options = [
      { text: correct, isCorrect: true },
      { text: distractor1, isCorrect: false },
      { text: distractor2, isCorrect: false },
    ];

    if (quizIndex % 3 === 1) {
      return [options[1], options[0], options[2]];
    } else if (quizIndex % 3 === 2) {
      return [options[2], options[1], options[0]];
    }
    return options;
  }, [currentExample, quizIndex]);

  const handleSelectQuizOption = (index: number, isCorrect: boolean) => {
    if (quizStatus !== 'unanswered') return;

    setSelectedOption(index);
    if (isCorrect) {
      setQuizStatus('correct');
      sfx.playSuccessChime();
      triggerConfetti();
    } else {
      setQuizStatus('incorrect');
      sfx.playErrorBuzz();
    }
  };

  const handleNextQuiz = () => {
    sfx.playTileClick();
    setSelectedOption(null);
    setQuizStatus('unanswered');
    if (data.examples && data.examples.length > 0) {
      setQuizIndex((prev) => (prev + 1) % data.examples.length);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/80 backdrop-blur-md flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-slate-900/90 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">Why is this sentence different?</h2>
                {data.explanation_source === 'hybrid_gemini' ? (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                    AI Sensei (Gemini)
                  </span>
                ) : (
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    Local UD Engine
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Grammar rules, sentence changes, and parallel examples
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content body */}
        <div className="p-6 space-y-8 flex-1">
          {/* Quick comparison box with Interactive Word Chips */}
          <div className="bg-slate-950/80 p-5 rounded-2xl border border-indigo-500/20 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold flex items-center gap-2">
                <GitCompare className="w-3.5 h-3.5 text-indigo-400" />
                Sentence Pair & Interactive Word Alignment
              </span>
              <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20 font-medium">
                Tap words to inspect morphology
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-slate-900/80 p-3.5 rounded-xl border border-slate-800">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase">
                    Source ({data.detected_language})
                  </span>
                  <button
                    onClick={() => handleSpeak(data.native_text, 998)}
                    className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    title="Listen to source"
                  >
                    <Volume2 className={`w-3.5 h-3.5 ${playingIndex === 998 ? 'text-indigo-400 animate-pulse' : ''}`} />
                  </button>
                </div>
                <div className="text-white font-medium text-base leading-relaxed">
                  {data.vocabulary && data.vocabulary.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {data.vocabulary.map((item, idx) => {
                        const isHighlighted = activeIndex === idx;
                        return (
                          <button
                            key={idx}
                            onClick={() => setSelectedWordIndex(idx)}
                            onMouseEnter={() => setHoveredWordIndex(idx)}
                            onMouseLeave={() => setHoveredWordIndex(null)}
                            className={`px-2 py-1 rounded-lg text-sm font-devanagari transition-all cursor-pointer ${
                              isHighlighted
                                ? 'bg-amber-500/25 text-amber-200 border border-amber-400 shadow-md scale-105'
                                : 'bg-slate-800/80 text-slate-200 hover:bg-slate-800 hover:text-white border border-slate-700/50'
                            }`}
                          >
                            {item.source_word}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div>{data.native_text}</div>
                  )}
                </div>
                <div className="text-xs text-slate-400 mt-2 font-mono">{data.roman_text}</div>
              </div>

              <div className="bg-slate-900/80 p-3.5 rounded-xl border border-indigo-500/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-indigo-400 uppercase">
                    Target (Translation)
                  </span>
                  <button
                    onClick={() => handleSpeak(data.translation_native, 999)}
                    className="p-1 rounded text-indigo-300 hover:text-white hover:bg-slate-800 transition-colors"
                    title="Listen to Marathi translation"
                  >
                    <Volume2 className={`w-3.5 h-3.5 ${playingIndex === 999 ? 'text-emerald-400 animate-pulse' : ''}`} />
                  </button>
                </div>
                <div className="text-white font-medium text-base leading-relaxed">
                  {data.vocabulary && data.vocabulary.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {data.vocabulary.map((item, idx) => {
                        const isHighlighted = activeIndex === idx;
                        return (
                          <button
                            key={idx}
                            onClick={() => setSelectedWordIndex(idx)}
                            onMouseEnter={() => setHoveredWordIndex(idx)}
                            onMouseLeave={() => setHoveredWordIndex(null)}
                            className={`px-2 py-1 rounded-lg text-sm font-devanagari transition-all cursor-pointer ${
                              isHighlighted
                                ? 'bg-emerald-500/30 text-emerald-200 border border-emerald-400 shadow-md scale-105'
                                : 'bg-slate-800/80 text-slate-200 hover:bg-slate-800 hover:text-white border border-slate-700/50'
                            }`}
                          >
                            {item.target_word}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div>{data.translation_native}</div>
                  )}
                </div>
                <div className="text-xs text-indigo-300 mt-2 font-mono">{data.translation_roman}</div>
              </div>
            </div>

            {/* Active Word Morphological Inspector */}
            {activeWord && (
              <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-4 rounded-xl border border-indigo-500/30 space-y-2.5 animate-in fade-in duration-150">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-amber-300 font-devanagari bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      {activeWord.source_word}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-xs font-bold text-emerald-300 font-devanagari bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      {activeWord.target_word}
                    </span>
                    {activeWord.target_roman && (
                      <span className="text-[11px] text-slate-400 font-mono">
                        ({activeWord.target_roman})
                      </span>
                    )}
                    <button
                      onClick={() => handleSpeak(activeWord.target_word, 997)}
                      className="p-1 rounded text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                      title="Pronounce word"
                    >
                      <Volume2 className={`w-3.5 h-3.5 ${playingIndex === 997 ? 'text-emerald-400 animate-pulse' : ''}`} />
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {activeWord.part_of_speech || 'word'}
                    </span>
                    {activeWord.is_construction_based ? (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        Synthetic Construction
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        Direct Cognate
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-xs text-slate-300 flex items-center gap-1.5">
                  <span className="text-slate-400 font-semibold">Meaning:</span>
                  <span>{activeWord.meaning}</span>
                </div>

                {activeWord.root_lemma && (
                  <div className="text-xs text-slate-300 flex items-center gap-1.5">
                    <span className="text-indigo-400 font-semibold">Root Lemma:</span>
                    <span className="font-mono text-slate-200">{activeWord.root_lemma}</span>
                  </div>
                )}

                {activeWord.morph_analysis && (
                  <div className="text-xs text-slate-300 flex items-start gap-1.5 bg-black/30 p-2.5 rounded-lg border border-white/5 font-mono">
                    <span className="text-amber-400 font-semibold shrink-0">UD Morphology:</span>
                    <span className="text-slate-300 leading-relaxed">{activeWord.morph_analysis}</span>
                  </div>
                )}

                {activeWord.gender_contrast && (
                  <div className="text-xs bg-purple-950/30 text-purple-200 p-2.5 rounded-lg border border-purple-500/30 flex items-start gap-1.5">
                    <span className="font-bold text-purple-400 shrink-0">3-Gender Contrast:</span>
                    <span>{activeWord.gender_contrast}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sensei's Cultural Mnemonic / Memory Hook */}
          {data.cultural_mnemonic && (
            <div className="bg-gradient-to-r from-amber-950/40 via-purple-950/30 to-indigo-950/40 p-4 rounded-xl border border-amber-500/30 space-y-1.5 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold uppercase tracking-wider">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span>Sensei's Memory Trick</span>
                </div>
                {data.explanation_source === 'hybrid_gemini' && (
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    Gemini AI
                  </span>
                )}
              </div>
              <p className="text-sm text-amber-100/95 leading-relaxed font-medium">
                {data.cultural_mnemonic}
              </p>
            </div>
          )}

          {/* Pattern Takeaway Formula Banner */}
          {primaryRule && primaryRule.source_pattern && primaryRule.target_pattern && (
            <div className="bg-gradient-to-r from-indigo-950/40 via-purple-950/30 to-slate-950/50 p-4 rounded-xl border border-indigo-500/30 space-y-2">
              <div className="flex items-center gap-2 text-indigo-300 text-xs font-semibold uppercase tracking-wider">
                <Lightbulb className="w-4 h-4 text-amber-400" />
                <span>Pattern Rule Formula</span>
              </div>
              <div className="flex items-center flex-wrap gap-2 text-sm bg-black/40 px-3 py-2 rounded-lg border border-white/5 font-mono">
                <span className="text-slate-200">{primaryRule.source_pattern}</span>
                <ArrowRight className="w-4 h-4 text-amber-400 shrink-0" />
                <span className="text-emerald-300 font-bold">{primaryRule.target_pattern}</span>
              </div>
              <p className="text-xs text-slate-300">
                Master this substitution pattern to construct dozens of natural sentences!
              </p>
            </div>
          )}

          {/* Key Structural Differences (Why they differ) */}
          {data.differences && data.differences.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Why The Sentences Differ
              </h3>
              <ul className="space-y-2.5 text-xs text-slate-300">
                {data.differences.map((diff, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800 leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                    <span>{diff}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Vocabulary & Morpheme Alignment Table */}
          {data.vocabulary && data.vocabulary.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <Languages className="w-4 h-4 text-emerald-400" />
                  Vocabulary & Morpheme Alignment
                </h3>
                <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full font-mono">
                  {data.vocabulary.length} aligned items
                </span>
              </div>
              <div className="grid grid-cols-1 gap-2.5">
                {data.vocabulary.map((v, vIdx) => (
                  <div
                    key={vIdx}
                    onClick={() => setSelectedWordIndex(vIdx)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      activeIndex === vIdx
                        ? 'bg-slate-900 border-indigo-500/60 shadow-md ring-1 ring-indigo-500/30'
                        : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2 font-devanagari">
                        <span className="text-sm font-bold text-white">{v.source_word}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-sm font-bold text-emerald-300">{v.target_word}</span>
                        {v.target_roman && (
                          <span className="text-xs text-indigo-300 font-mono">({v.target_roman})</span>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSpeak(v.target_word, 800 + vIdx);
                          }}
                          className="p-1 rounded text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                          title="Pronounce word"
                        >
                          <Volume2 className={`w-3 h-3 ${playingIndex === 800 + vIdx ? 'text-emerald-400 animate-pulse' : ''}`} />
                        </button>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          {v.part_of_speech || 'word'}
                        </span>
                        {v.is_construction_based && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                            Construction
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      <span className="text-slate-500 font-semibold mr-1">Meaning:</span>
                      {v.meaning}
                    </div>
                    {(v.morph_analysis || v.gender_contrast || v.root_lemma) && (
                      <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex flex-wrap gap-2 text-[11px]">
                        {v.root_lemma && (
                          <span className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            <strong className="text-indigo-400 font-mono">Lemma:</strong> {v.root_lemma}
                          </span>
                        )}
                        {v.morph_analysis && (
                          <span className="text-amber-200/90 bg-amber-950/20 px-2 py-0.5 rounded border border-amber-500/20 font-mono">
                            {v.morph_analysis}
                          </span>
                        )}
                        {v.gender_contrast && (
                          <span className="text-purple-300 bg-purple-950/20 px-2 py-0.5 rounded border border-purple-500/20">
                            {v.gender_contrast}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Grammar Concepts */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Grammar Construction Points
              </h3>
            </div>

            <div className="space-y-3">
              {data.grammar_explanation.map((pt, i) => (
                <div key={i} className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-white">{pt.title}</h4>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {pt.concept}
                    </span>
                  </div>
                  {pt.source_pattern && pt.target_pattern && (
                    <div className="flex items-center gap-2 text-xs bg-black/40 px-3 py-1.5 rounded-lg border border-white/5 font-mono">
                      <span className="text-slate-300">{pt.source_pattern}</span>
                      <span className="text-indigo-400 font-bold">→</span>
                      <span className="text-emerald-300">{pt.target_pattern}</span>
                    </div>
                  )}
                  <p className="text-xs text-slate-300 leading-relaxed">{pt.explanation}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Common Learner Mistakes */}
          {data.common_mistakes && data.common_mistakes.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Common Learner Traps & Pitfalls
              </h3>
              <div className="space-y-2">
                {data.common_mistakes.map((mistake, idx) => (
                  <div key={idx} className="bg-amber-950/20 border border-amber-500/30 p-3.5 rounded-xl text-xs text-amber-200/90 leading-relaxed flex items-start gap-2">
                    <span className="text-amber-400 font-bold">⚠️</span>
                    <span>{mistake}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Similar Parallel Examples to Grasp Easily */}
          {data.examples && data.examples.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  Similar Parallel Examples
                </h3>
                <span className="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-full font-mono">
                  {data.examples.length} practice pairs
                </span>
              </div>
              <div className="space-y-3">
                {data.examples.map((ex, idx) => (
                  <div key={idx} className="bg-slate-950/70 p-4 rounded-xl border border-slate-800/90 hover:border-indigo-500/40 transition-all space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                        Pattern Example {idx + 1}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleSpeak(ex.target_sentence, idx)}
                          title="Listen to pronunciation"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                        >
                          <Volume2 className={`w-3.5 h-3.5 ${playingIndex === idx ? 'text-emerald-400 animate-pulse' : ''}`} />
                        </button>
                        <button
                          onClick={() => handleCopy(ex.target_sentence, idx)}
                          title="Copy Marathi sentence"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-colors"
                        >
                          {copiedIndex === idx ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="text-xs text-slate-400">
                      <span className="text-slate-500 text-[10px] uppercase font-semibold mr-1">Hindi:</span>
                      {ex.source_sentence}
                    </div>

                    <div className="text-sm font-semibold text-white font-devanagari">
                      <span className="text-emerald-400 text-[10px] uppercase font-semibold mr-1">Marathi:</span>
                      {ex.target_sentence}
                    </div>

                    <div className="text-xs text-indigo-300 font-mono">
                      {ex.target_roman}
                    </div>

                    <div className="text-xs text-slate-400 italic">
                      "{ex.english_translation}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interactive "Try This Pattern!" Mini-Quiz */}
          {currentExample && quizOptions.length > 0 && (
            <div className="bg-gradient-to-br from-indigo-950/60 via-slate-900 to-slate-950 p-5 rounded-2xl border border-indigo-500/30 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-300">
                    <Target className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white flex items-center gap-1.5">
                      <span>Quick Practice — Try This Pattern!</span>
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                    </h4>
                    <p className="text-[11px] text-slate-400">Test your recall of this sentence pattern</p>
                  </div>
                </div>

                <button
                  onClick={handleNextQuiz}
                  title="Next Question"
                  className="flex items-center gap-1 text-xs text-indigo-300 hover:text-white px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 transition-all"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Next Drill</span>
                </button>
              </div>

              {/* Question Prompt */}
              <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Translate to Marathi:
                </span>
                <div className="text-sm font-medium text-white">
                  "{currentExample.source_sentence}"
                </div>
                <div className="text-xs text-slate-400 italic">
                  "{currentExample.english_translation}"
                </div>
              </div>

              {/* Options */}
              <div className="space-y-2">
                {quizOptions.map((opt, oIdx) => {
                  let btnStyle = "bg-slate-900/90 border-slate-800 hover:border-indigo-500/50 text-slate-200";

                  if (selectedOption !== null) {
                    if (opt.isCorrect) {
                      btnStyle = "bg-emerald-950/50 border-emerald-500 text-emerald-200 font-bold";
                    } else if (selectedOption === oIdx && !opt.isCorrect) {
                      btnStyle = "bg-rose-950/50 border-rose-500 text-rose-200";
                    } else {
                      btnStyle = "bg-slate-950/40 border-slate-900 text-slate-500 opacity-50";
                    }
                  }

                  return (
                    <button
                      key={oIdx}
                      disabled={quizStatus !== 'unanswered'}
                      onClick={() => handleSelectQuizOption(oIdx, opt.isCorrect)}
                      className={`w-full text-left p-3 rounded-xl border transition-all text-xs flex items-center justify-between font-devanagari ${btnStyle}`}
                    >
                      <span>{opt.text}</span>
                      {selectedOption !== null && opt.isCorrect && (
                        <Check className="w-4 h-4 text-emerald-400 shrink-0 ml-2" />
                      )}
                      {selectedOption === oIdx && !opt.isCorrect && (
                        <X className="w-4 h-4 text-rose-400 shrink-0 ml-2" />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Feedback Banner */}
              {quizStatus === 'correct' && (
                <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-200 text-xs flex items-center justify-between animate-in fade-in">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span><strong>कडक! Perfectly matched!</strong> (+15 XP)</span>
                  </div>
                  <button
                    onClick={handleNextQuiz}
                    className="text-[11px] font-bold uppercase tracking-wider text-emerald-300 hover:underline ml-2"
                  >
                    Try Another →
                  </button>
                </div>
              )}

              {quizStatus === 'incorrect' && (
                <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 text-xs flex items-center justify-between animate-in fade-in">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>Watch out for the subject case or verb ending!</span>
                  </div>
                  <button
                    onClick={handleNextQuiz}
                    className="text-[11px] font-bold uppercase tracking-wider text-rose-300 hover:underline ml-2"
                  >
                    Try Another →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
