import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { BridgeModeSelector } from './components/BridgeModeSelector';
import { TranslationCard } from './components/TranslationCard';
import { VocabularyTable } from './components/VocabularyTable';
import { ExplanationDrawer } from './components/ExplanationDrawer';
import { PracticeModal } from './components/PracticeModal';
import { ProgressDashboard } from './components/ProgressDashboard';
import { LearnHub } from './components/LearnHub';
import { api } from './services/api';
import { AnalyzeResponse, ScriptMode, BridgeLevel, Language } from './types';
import {
  ArrowRightLeft,
  Sparkles,
  HelpCircle,
  BookOpen,
  Send,
  Loader2,
  ChevronDown,
} from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState<'translate' | 'learn'>('translate');
  const [sourceLang, setSourceLang] = useState<Language>('hindi');
  const [targetLang, setTargetLang] = useState<Language>('marathi');
  const [scriptMode, setScriptMode] = useState<ScriptMode>('both');
  const [bridgeLevel, setBridgeLevel] = useState<BridgeLevel>('intermediate');

  const [inputText, setInputText] = useState('Mujhe Marathi seekhni hai');
  const [transliterationPreview, setTransliterationPreview] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);
  const [isExplainOpen, setIsExplainOpen] = useState(false);
  const [isPracticeOpen, setIsPracticeOpen] = useState(false);
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState<number>(0);

  const analyzeReqId = useRef(0);
  const analyzeController = useRef<AbortController | null>(null);
  const invalidateAnalysis = () => {
    analyzeReqId.current += 1;
    analyzeController.current?.abort();
    setLoading(false);
    setAnalysisResult(null);
  };
  useEffect(() => () => analyzeController.current?.abort(), []);
  const refreshProgress = () => api.getProgress().then(p => setReviewCount(p.review_due_count)).catch(() => {});
  const transliterateReqId = useRef(0);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    api.getProgress()
      .then((prog) => {
        if (prog) {
          if (typeof prog.review_due_count === 'number') {
            setReviewCount(prog.review_due_count);
          }
          if (prog.bridge_mode_level && ['beginner', 'intermediate', 'advanced'].includes(prog.bridge_mode_level)) {
            setBridgeLevel(prog.bridge_mode_level as BridgeLevel);
          }
        }
      })
      .catch(() => {
        // Fallback default
      });
  }, []);

  const handleBridgeLevelChange = async (newLevel: BridgeLevel) => {
    const prevLevel = bridgeLevel;
    setBridgeLevel(newLevel);
    try {
      await api.updateBridgeMode(newLevel);
    } catch (err) {
      console.error("Failed to update bridge mode on server:", err);
      setBridgeLevel(prevLevel);
      setError(`Failed to update Bridge Mode to ${newLevel}. Reverted to ${prevLevel}.`);
      setTimeout(() => setError(null), 5000);
    }
  };

  const quickSamples = [
    { label: 'Learn Marathi', text: 'Mujhe Marathi seekhni hai', s: 'hindi', t: 'marathi' },
    { label: 'College tomorrow (Hindi)', text: 'Mujhe kal college jaana hai', s: 'hindi', t: 'marathi' },
    { label: 'College tomorrow (Marathi)', text: 'Mala udya college-la jaycha aahe', s: 'marathi', t: 'hindi' },
    { label: 'Need water', text: 'Mala paani pahije', s: 'marathi', t: 'hindi' },
    { label: 'How are you?', text: 'Aap kaise hain?', s: 'hindi', t: 'marathi' },
  ];

  const handleSwapLanguages = () => {
    invalidateAnalysis();
    const nextSource = targetLang;
    const nextTarget = sourceLang;
    setSourceLang(nextSource);
    setTargetLang(nextTarget);
  };

  const handleAnalyze = async (
    textToAnalyze?: string,
    explicitSource?: Language,
    explicitTarget?: Language,
    openExplanation = false
  ) => {
    const text = textToAnalyze || inputText;
    if (!text.trim()) return;

    const effectiveSource = explicitSource || sourceLang;
    const effectiveTarget = explicitTarget || targetLang;

    const requestId = ++analyzeReqId.current;
    analyzeController.current?.abort();
    const controller = new AbortController();
    analyzeController.current = controller;
    try {
      setLoading(true);
      setError(null);
      const res = await api.analyze(text, effectiveSource, effectiveTarget, scriptMode, controller.signal);
      if (requestId !== analyzeReqId.current) return;
      if (openExplanation) setIsExplainOpen(true);
      setAnalysisResult(res);
      if (res.detected_language === 'marathi' && effectiveSource === 'hindi') {
        setSourceLang('marathi');
        setTargetLang('hindi');
      } else if (res.detected_language === 'hindi' && effectiveSource === 'marathi') {
        setSourceLang('hindi');
        setTargetLang('marathi');
      }
    } catch (err: any) {
      if (controller.signal.aborted || requestId !== analyzeReqId.current) return;
      console.error(err);
      setError('Failed to analyze sentence. Ensure backend server is running.');
    } finally {
      if (requestId === analyzeReqId.current) setLoading(false);
    }
  };

  // Every input/language change invalidates in-flight previews, including clearing.
  useEffect(() => {
    const requestId = ++transliterateReqId.current;
    const controller = new AbortController();
    setTransliterationPreview('');
    if (inputText.trim() && /[a-zA-Z]/.test(inputText)) {
      debounceTimerRef.current = setTimeout(async () => {
        try {
          const result = await api.transliterate(inputText, sourceLang, 'latin_to_devanagari', controller.signal);
          if (requestId === transliterateReqId.current) setTransliterationPreview(result.output);
        } catch { /* The preview is optional; analysis errors are shown separately. */ }
      }, 250);
    }
    return () => {
      ++transliterateReqId.current;
      controller.abort();
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [inputText, sourceLang]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    invalidateAnalysis();
    setInputText(e.target.value);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Top Navbar */}
      <Navbar
        currentView={currentView}
        onChangeView={(v) => setCurrentView(v)}
        onOpenDashboard={() => setIsDashboardOpen(true)}
        onOpenPractice={() => setIsPracticeOpen(true)}
        reviewCount={reviewCount}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {currentView === 'learn' ? (
          <LearnHub onProgressChange={refreshProgress} />
        ) : (
          <>
            {/* Hero Section */}
            <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Speak freely in Roman letters • Learn Devanagari at your own pace</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white">
            Bridge Hindi & Marathi effortlessly
          </h1>
          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto">
            Natural translations with deep grammar explanations, bilingual alignments, and script-adaptive learning.
          </p>
        </div>

        {/* Bridge Mode Selector */}
        <BridgeModeSelector
          currentLevel={bridgeLevel}
          onChange={handleBridgeLevelChange}
        />

        {/* Language & Input Card */}
        <div className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6 border border-slate-800 shadow-xl">
          {/* Language Selection Row */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
            <div className="flex flex-wrap items-center gap-3">
              {/* Source Lang */}
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-semibold text-slate-400">I speak</span>
                <div className="relative">
                  <select
                    id="source-language-select"
                    value={sourceLang}
                    onChange={(e) => { invalidateAnalysis(); setSourceLang(e.target.value as Language); setTargetLang(e.target.value === "hindi" ? "marathi" : "hindi"); }}
                    className="appearance-none bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 pr-8 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="hindi">Hindi</option>
                    <option value="marathi">Marathi</option>
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                </div>
              </div>

              {/* Swap Button */}
              <button
                id="swap-lang-btn"
                onClick={handleSwapLanguages}
                title="Swap languages"
                className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white transition-all hover:scale-105 active:scale-95"
              >
                <ArrowRightLeft className="w-4 h-4 text-indigo-400" />
              </button>

              {/* Target Lang */}
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-semibold text-slate-400">I want to learn</span>
                <div className="relative">
                  <select
                    id="target-language-select"
                    value={targetLang}
                    onChange={(e) => { invalidateAnalysis(); setTargetLang(e.target.value as Language); setSourceLang(e.target.value === "hindi" ? "marathi" : "hindi"); }}
                    className="appearance-none bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 pr-8 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="marathi">Marathi</option>
                    <option value="hindi">Hindi</option>
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                </div>
              </div>
            </div>

            {/* Script Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-semibold text-slate-400">Script</span>
              <div className="relative">
                <select
                  id="script-select"
                  value={scriptMode}
                  onChange={(e) => setScriptMode(e.target.value as ScriptMode)}
                  className="appearance-none bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 pr-8 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 capitalize"
                >
                  <option value="both">Both (Roman & Devanagari)</option>
                  <option value="roman">Roman Only</option>
                  <option value="devanagari">Devanagari Only</option>
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Text Input Area */}
          <div className="space-y-3">
            <div className="relative">
              <textarea
                id="main-sentence-input"
                rows={3}
                value={inputText}
                onChange={handleInputChange}
                placeholder="Type or enter a sentence in English/Roman or Devanagari... (e.g. Mujhe Marathi seekhni hai)"
                className="w-full bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-base sm:text-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 resize-none font-medium leading-relaxed"
              />

              {/* Transliteration badge preview */}
              {transliterationPreview && (
                <div className="absolute bottom-3 left-4 flex items-center gap-2 text-xs bg-slate-900/90 border border-indigo-500/30 px-3 py-1 rounded-lg backdrop-blur-md">
                  <span className="text-slate-400 font-mono">Devanagari preview:</span>
                  <span className="text-indigo-300 font-devanagari font-bold">{transliterationPreview}</span>
                </div>
              )}
            </div>

            {/* Quick Sample Chips */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="text-xs text-slate-500">Quick examples:</span>
              {quickSamples.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    invalidateAnalysis();
                    setInputText(sample.text);
                    setSourceLang(sample.s as Language);
                    setTargetLang(sample.t as Language);
                    handleAnalyze(sample.text, sample.s as Language, sample.t as Language);
                  }}
                  className="text-xs px-3 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-800/80">
            <div className="text-xs text-slate-400">
              Works with both <span className="text-indigo-300 font-mono">Roman letters</span> and <span className="text-white font-devanagari font-semibold">देवनागरी</span>
            </div>

            <div className="flex items-center gap-3">
              <button
                id="practice-btn-main"
                onClick={() => setIsPracticeOpen(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 hover:text-white transition-all"
              >
                <BookOpen className="w-4 h-4 text-indigo-400" />
                <span>Quick Practice</span>
              </button>

              <button
                id="explain-btn-main"
                onClick={() => {
                  if (analysisResult) {
                    setIsExplainOpen(true);
                  } else {
                    handleAnalyze(undefined, undefined, undefined, true);
                  }
                }}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 transition-all"
              >
                <HelpCircle className="w-4 h-4 text-amber-400" />
                <span>Explain</span>
              </button>

              <button
                id="translate-btn-main"
                onClick={() => handleAnalyze()}
                disabled={loading || !inputText.trim()}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                <span>Translate</span>
              </button>
            </div>
          </div>
        </div>

        {/* Error message if any */}
        {error && (
          <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/30 text-rose-200 text-sm">
            {error}
          </div>
        )}

        {/* Output Section */}
        {analysisResult && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Translation Result Card */}
            <TranslationCard
              data={analysisResult}
              scriptMode={scriptMode}
              onScriptModeChange={(mode) => setScriptMode(mode)}
              onOpenExplain={() => setIsExplainOpen(true)}
              bridgeLevel={bridgeLevel}
            />

            {/* Learn from this sentence Vocabulary Table */}
            <VocabularyTable
              vocabulary={analysisResult.vocabulary}
              sourceLang={analysisResult.detected_language}
              targetLang={targetLang}
            />
          </div>
        )}
          </>
        )}
      </main>

      {/* Slide-over Explanation Drawer */}
      <ExplanationDrawer
        isOpen={isExplainOpen}
        onClose={() => setIsExplainOpen(false)}
        data={analysisResult}
      />

      {/* Practice Modal */}
      <PracticeModal
        isOpen={isPracticeOpen}
        onClose={() => setIsPracticeOpen(false)}
        onPracticeCompleted={refreshProgress}
      />

      {/* Progress Dashboard */}
      <ProgressDashboard
        isOpen={isDashboardOpen}
        onClose={() => setIsDashboardOpen(false)}
        onBridgeLevelChange={handleBridgeLevelChange}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        BhashaBridge — NLP-Powered Language Learning Engine • IndicTrans2 & IndicXlit Ready
      </footer>
    </div>
  );
}
