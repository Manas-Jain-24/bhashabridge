import React, { useState, useEffect } from 'react';
import { DailyQuestData, PronunciationEvaluateResult } from '../../types';
import { api } from '../../services/api';
import { speech } from '../../utils/speechEngine';
import { sfx } from '../../utils/soundEffects';
import { triggerConfetti } from '../../utils/confetti';
import {
  Mic,
  MicOff,
  Volume2,
  Sparkles,
  CheckCircle2,
  Calendar,
  Flame,
  Award,
  ArrowRight,
  Loader2,
  Target,
} from 'lucide-react';

interface DailyQuestsAndPronunciationProps {
  onXpEarned: (amount: number) => void;
}

const SAMPLE_PRACTICE_PHRASES = [
  { devanagari: 'मला उद्या कॉलेजला जायचं आहे', roman: 'Mala udya college-la jaycha aahe', english: 'I have to go to college tomorrow' },
  { devanagari: 'मी आता घरी जात आहे', roman: 'Mi aata ghari jaat aahe', english: 'I am going home right now' },
  { devanagari: 'भाऊ एक कडक चहा द्या', roman: 'Bhau ek kadak chaha dya', english: 'Brother please give one strong tea' },
  { devanagari: 'तुम्ही कसे आहात', roman: 'Tumhi kase aahat', english: 'How are you all (respectful)' },
];

export const DailyQuestsAndPronunciation: React.FC<DailyQuestsAndPronunciationProps> = ({
  onXpEarned,
}) => {
  const [questData, setQuestData] = useState<DailyQuestData | null>(null);
  const [loading, setLoading] = useState(true);

  // Pronunciation Studio State
  const [selectedPhrase, setSelectedPhrase] = useState(SAMPLE_PRACTICE_PHRASES[0]);
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<PronunciationEvaluateResult | null>(null);
  const [recController, setRecController] = useState<{ stop: () => void } | null>(null);

  useEffect(() => {
    api.getDailyQuest().then((d) => {
      setQuestData(d);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handlePronounce = (text: string) => {
    sfx.playTileClick();
    speech.speak(text, 'marathi');
  };

  const handleToggleRecord = () => {
    if (isRecording) {
      if (recController) recController.stop();
      setIsRecording(false);
      return;
    }

    sfx.playTileClick();
    setTranscript('');
    setEvalResult(null);
    setIsRecording(true);

    const controller = speech.startListening({
      language: 'mr-IN',
      onInterim: (text) => setTranscript(text),
      onFinal: async (finalText) => {
        setTranscript(finalText);
        setIsRecording(false);
        await runEvaluation(finalText);
      },
      onError: (err) => {
        console.error('Speech error:', err);
        setIsRecording(false);
      },
      onEnd: () => {
        setIsRecording(false);
      },
    });

    setRecController(controller);
  };

  const runEvaluation = async (spoken: string) => {
    try {
      setEvaluating(true);
      const res = await api.evaluatePronunciation(spoken, selectedPhrase.devanagari);
      setEvalResult(res);

      if (res.is_native_pass) {
        sfx.playSuccessChime();
        triggerConfetti();
        onXpEarned(40);
      } else {
        sfx.playErrorBuzz();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setEvaluating(false);
    }
  };

  if (loading || !questData) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-3 text-slate-400">
        <Loader2 className="w-7 h-7 animate-spin text-indigo-400" />
        <p className="text-sm">Loading Daily Quests & Pronunciation Studio...</p>
      </div>
    );
  }

  const { word_of_the_day, idiom_of_the_day, daily_missions } = questData;

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* 1. Word & Idiom of the Day Spotlight */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Word of the Day Card */}
        <div className="rounded-3xl p-6 sm:p-7 bg-gradient-to-br from-amber-950/40 via-slate-900/90 to-slate-900/90 border border-amber-500/30 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 text-xs font-bold uppercase tracking-wider">
              <Calendar className="w-3.5 h-3.5" />
              <span>Word of the Day</span>
            </div>

            <button
              onClick={() => handlePronounce(word_of_the_day.devanagari)}
              title="Listen to pronunciation"
              className="p-2 rounded-xl bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-all"
            >
              <Volume2 className="w-4 h-4" />
            </button>
          </div>

          <div>
            <div className="text-3xl sm:text-4xl font-black text-white font-devanagari">
              {word_of_the_day.devanagari}
            </div>
            <div className="text-xs font-mono text-amber-300 font-semibold mt-0.5">
              ({word_of_the_day.roman}) • {word_of_the_day.meaning_hindi}
            </div>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-2xl border border-slate-800">
            {word_of_the_day.cultural_note}
          </p>

          <div className="text-xs space-y-1 pt-1 border-t border-slate-800">
            <div className="text-slate-400">Example:</div>
            <div className="font-bold text-white font-devanagari">
              "{word_of_the_day.example_marathi}"
            </div>
            <div className="text-slate-400 italic">
              "{word_of_the_day.example_hindi}"
            </div>
          </div>
        </div>

        {/* Idiom of the Day Card */}
        <div className="rounded-3xl p-6 sm:p-7 bg-gradient-to-br from-purple-950/40 via-slate-900/90 to-slate-900/90 border border-purple-500/30 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-xs font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Marathi Idiom (म्हण)</span>
            </div>

            <button
              onClick={() => handlePronounce(idiom_of_the_day.devanagari)}
              title="Listen to idiom"
              className="p-2 rounded-xl bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-all"
            >
              <Volume2 className="w-4 h-4" />
            </button>
          </div>

          <div>
            <div className="text-xl sm:text-2xl font-black text-white font-devanagari leading-snug">
              "{idiom_of_the_day.devanagari}"
            </div>
            <div className="text-xs font-mono text-purple-300 mt-1">
              ({idiom_of_the_day.roman})
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1 text-xs">
            <span className="text-slate-400 font-semibold">Hindi Equivalent:</span>
            <div className="font-bold text-amber-300 font-devanagari text-sm">
              "{idiom_of_the_day.hindi_equivalent}"
            </div>
            <p className="text-slate-400 mt-1 leading-relaxed">
              {idiom_of_the_day.explanation}
            </p>
          </div>
        </div>
      </div>

      {/* 2. Interactive Pronunciation Voice Studio */}
      <div className="rounded-3xl p-6 sm:p-8 bg-slate-900/90 border border-indigo-500/30 shadow-xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 text-xs font-semibold">
              <Mic className="w-3.5 h-3.5" />
              <span>Voice Pronunciation Studio</span>
            </div>
            <h3 className="text-xl sm:text-2xl font-extrabold text-white mt-1">
              Speak Marathi with Native Fluency
            </h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Listen to native audio, speak into the mic, and get immediate phonetic feedback.
            </p>
          </div>

          {/* Quick Phrase Selector */}
          <div className="flex flex-wrap items-center gap-2">
            {SAMPLE_PRACTICE_PHRASES.map((phrase, idx) => (
              <button
                key={idx}
                onClick={() => {
                  sfx.playTileClick();
                  setSelectedPhrase(phrase);
                  setTranscript('');
                  setEvalResult(null);
                }}
                className={`text-xs px-3 py-1.5 rounded-xl font-bold transition-all ${
                  selectedPhrase.devanagari === phrase.devanagari
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Phrase {idx + 1}
              </button>
            ))}
          </div>
        </div>

        {/* Target Phrase Display */}
        <div className="p-6 rounded-2xl bg-slate-950/80 border border-slate-800 text-center space-y-3">
          <div className="text-xs uppercase font-semibold text-slate-500">
            Target Marathi Sentence
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-white font-devanagari">
            {selectedPhrase.devanagari}
          </div>
          <div className="text-xs sm:text-sm text-indigo-300 font-mono">
            {selectedPhrase.roman}
          </div>
          <div className="text-xs text-slate-400 italic">
            "{selectedPhrase.english}"
          </div>

          <div className="pt-2 flex justify-center">
            <button
              onClick={() => handlePronounce(selectedPhrase.devanagari)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-700 text-indigo-300 text-xs font-semibold transition-all hover:scale-105 active:scale-95"
            >
              <Volume2 className="w-4 h-4" />
              <span>Listen to Native Audio</span>
            </button>
          </div>
        </div>

        {/* Live Mic Action Area */}
        <div className="text-center space-y-4">
          <div className="flex justify-center">
            <button
              onClick={handleToggleRecord}
              className={`relative w-20 h-20 rounded-full flex items-center justify-center text-white shadow-2xl transition-all duration-300 ${
                isRecording
                  ? 'bg-rose-600 ring-8 ring-rose-500/30 scale-110 animate-pulse'
                  : 'bg-gradient-to-tr from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 ring-4 ring-indigo-500/20 hover:scale-105 active:scale-95'
              }`}
            >
              {isRecording ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
            </button>
          </div>

          <div className="text-xs font-semibold text-slate-400">
            {isRecording ? (
              <span className="text-rose-400 animate-pulse">
                🎙️ Listening... Speak the sentence now in Marathi!
              </span>
            ) : (
              <span>Tap microphone to start speaking</span>
            )}
          </div>

          {/* Real-time transcription */}
          {transcript && (
            <div className="max-w-md mx-auto p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs space-y-1">
              <span className="text-slate-500 uppercase font-bold text-[10px]">
                Recognized Speech:
              </span>
              <p className="text-sm font-bold text-white font-devanagari">
                "{transcript}"
              </p>
            </div>
          )}

          {evaluating && (
            <div className="flex items-center justify-center gap-2 text-xs text-indigo-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing phonetic accuracy...</span>
            </div>
          )}
        </div>

        {/* Evaluation Feedback Banner */}
        {evalResult && (
          <div
            className={`p-6 rounded-2xl border animate-in zoom-in-95 duration-200 ${
              evalResult.is_native_pass
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
                : 'bg-amber-950/40 border-amber-500/40 text-amber-200'
            }`}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-extrabold text-base">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span>Pronunciation Score: {evalResult.accuracy_score}%</span>
                </div>
                {evalResult.is_native_pass && (
                  <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-bold text-xs">
                    +40 XP Earned
                  </span>
                )}
              </div>

              <p className="text-xs sm:text-sm leading-relaxed">{evalResult.feedback}</p>

              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1 text-xs">
                <span className="text-slate-400 font-bold uppercase text-[10px]">
                  Syllable Stress Guide (Capitalized = Stress):
                </span>
                <div className="font-mono text-indigo-300 font-bold">
                  {evalResult.phonetic_stress_guide}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Daily Missions Checklist */}
      <div className="rounded-3xl p-6 sm:p-7 bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white">Daily Learning Missions</h3>
            <p className="text-xs text-slate-400">Complete quests to maintain your streak and earn bonus XP</p>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-orange-500/10 text-orange-400 text-xs font-bold border border-orange-500/20">
            <Flame className="w-3.5 h-3.5 fill-current" />
            <span>Daily Streak Active</span>
          </div>
        </div>

        <div className="space-y-3">
          {daily_missions.map((mission) => {
            const pct = Math.min(100, Math.round((mission.current / mission.target) * 100));

            return (
              <div
                key={mission.id}
                className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-xl">
                    {mission.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">{mission.title}</h4>
                    <p className="text-xs text-slate-400 font-devanagari">{mission.marathi_title}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <div className="text-right">
                    <span className="text-xs font-bold text-amber-300 font-mono">
                      +{mission.xp_reward} XP
                    </span>
                    <div className="text-[10px] text-slate-500 font-mono">
                      {mission.current}/{mission.target}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
