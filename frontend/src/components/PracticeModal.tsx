import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { PracticeQuestion, PracticeEvaluateResponse } from '../types';
import { X, CheckCircle, XCircle, ArrowRight, RefreshCw, Sparkles, HelpCircle } from 'lucide-react';

interface PracticeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPracticeCompleted?: () => void;
}

export const PracticeModal: React.FC<PracticeModalProps> = ({
  isOpen,
  onClose,
  onPracticeCompleted,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitting = useRef(false);
  const [question, setQuestion] = useState<PracticeQuestion | null>(null);
  const [userAnswer, setUserAnswer] = useState('');
  const [evaluation, setEvaluation] = useState<PracticeEvaluateResponse | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  const loadNewQuestion = async () => {
    try {
      setLoading(true);
      setError(null);
      setQuestion(null);
      setEvaluation(null);
      setUserAnswer('');
      const progress = await api.getProgress();
      const roadmap = await api.getMilestones();
      const active = roadmap.find(m => m.is_active);
      const level = active?.level_number ?? 0;
      const topics = ['greetings', 'requests', 'college', 'conversation', 'grammar', 'script'];
      const q = await api.generatePractice('marathi', `level_${level}`, topics[level] || 'general');
      setQuestion(q);
    } catch (err) {
      console.error(err);
      setError('Could not load practice. Check the backend connection and retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadNewQuestion();
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen]);

  const handleSubmit = async (answerToSubmit?: string, optionId?: string) => {
    const finalAnswer = answerToSubmit || userAnswer;
    if (!finalAnswer.trim() || !question || submitting.current || evaluation) return;
    submitting.current = true;
    setError(null);

    try {
      setEvaluating(true);
      const res = await api.evaluatePractice(question.id, finalAnswer, 'roman', optionId);
      setEvaluation(res);
      if (onPracticeCompleted) onPracticeCompleted();
    } catch (err) {
      console.error(err);
      setError('Your answer could not be saved. Please retry.');
    } finally {
      submitting.current = false;
      setEvaluating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Interactive Practice Modal"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4"
    >
      <div className="w-full max-w-xl bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Interactive Practice</h2>
              <p className="text-xs text-slate-400">Bridge your spoken intuition to written forms</p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close modal"
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && <div role="alert" className="text-sm text-rose-300">{error} {!question && <button onClick={loadNewQuestion} className="underline ml-2">Retry</button>}</div>}
        {loading ? (
          <div className="py-12 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
            <span className="text-sm text-slate-400">Generating adaptive question...</span>
          </div>
        ) : question ? (
          <div className="space-y-6">
            {/* Question Card */}
            <div className="bg-slate-950/70 p-5 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 font-mono text-[11px] border border-indigo-500/20 capitalize">
                  {question.question_type.replace(/_/g, ' ')}
                </span>
                {question.hint && (
                  <span className="text-slate-400 flex items-center gap-1">
                    <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                    Hint: {question.hint}
                  </span>
                )}
              </div>

              <div className="text-base sm:text-lg font-medium text-white">
                {question.prompt}
              </div>
              {question.prompt_roman && question.prompt_roman !== question.prompt && (
                <div className="text-xs text-indigo-300 font-mono">
                  {question.prompt_roman}
                </div>
              )}
            </div>

            {/* Answer Options or Input */}
            {question.options && question.options.length > 0 ? (
              <div className="space-y-2">
                <label className="text-xs text-slate-400 uppercase font-semibold tracking-wider block">
                  Select correct answer:
                </label>
                <div className="space-y-2">
                  {question.options.map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => {
                        setUserAnswer(opt.text_roman);
                        handleSubmit(opt.text_roman, opt.id);
                      }}
                      disabled={evaluating || evaluation !== null}
                      className="w-full text-left p-3.5 rounded-xl border border-slate-800 bg-slate-950/40 hover:bg-indigo-950/30 hover:border-indigo-500/40 transition-all group"
                    >
                      <div className="text-sm font-semibold text-white font-devanagari group-hover:text-indigo-200">
                        {opt.text_devanagari}
                      </div>
                      <div className="text-xs text-slate-400 font-mono mt-0.5">
                        {opt.text_roman}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <label className="text-xs text-slate-400 uppercase font-semibold tracking-wider block">
                  Your Answer (Roman or Devanagari):
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                    placeholder="e.g. Mala paani pahije..."
                    disabled={evaluating || evaluation !== null}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                  />
                  <button
                    onClick={() => handleSubmit()}
                    disabled={!userAnswer.trim() || evaluating || evaluation !== null}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-indigo-600/20"
                  >
                    Check
                  </button>
                </div>
              </div>
            )}

            {/* Evaluation Feedback */}
            {evaluation && (
              <div
                className={`p-5 rounded-2xl border space-y-3 animate-in fade-in ${
                  evaluation.correctness
                    ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-100'
                    : 'bg-rose-950/30 border-rose-500/40 text-rose-100'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {evaluation.correctness ? (
                      <>
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                        <span className="font-bold text-sm text-emerald-300">Great Job! Correct.</span>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-5 h-5 text-rose-400" />
                        <span className="font-bold text-sm text-rose-300">Needs Review</span>
                      </>
                    )}
                  </div>
                  <span className="text-xs font-mono font-semibold">
                    Score: {evaluation.score}%
                  </span>
                </div>

                <div className="text-xs space-y-1 text-slate-300">
                  <div>
                    <strong>Expected (Devanagari):</strong> {evaluation.expected_answer_devanagari}
                  </div>
                  <div>
                    <strong>Expected (Roman):</strong>{' '}
                    <span className="font-mono text-indigo-300">{evaluation.expected_answer_roman}</span>
                  </div>
                  <div className="pt-1 text-slate-200">
                    <strong>Explanation:</strong> {evaluation.explanation}
                  </div>
                </div>

                <button
                  onClick={loadNewQuestion}
                  className="w-full mt-3 py-2.5 rounded-xl bg-white text-slate-950 font-bold text-sm hover:bg-slate-200 transition-colors flex items-center justify-center gap-2"
                >
                  <span>Next Question</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};
