import React, { useState } from 'react';
import { AnalyzeResponse, ScriptMode, BridgeLevel } from '../types';
import { HelpCircle, Copy, Check, Volume2, Sparkles, ArrowRight } from 'lucide-react';
import { speech } from '../utils/speechEngine';

interface TranslationCardProps {
  data: AnalyzeResponse;
  scriptMode: ScriptMode;
  onScriptModeChange: (mode: ScriptMode) => void;
  onOpenExplain: () => void;
  bridgeLevel: BridgeLevel;
}

export const TranslationCard: React.FC<TranslationCardProps> = ({
  data,
  scriptMode,
  onScriptModeChange,
  onOpenExplain,
  bridgeLevel,
}) => {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(`${data.translation_native}\n${data.translation_roman}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSpeech = () => {
    if (speaking) {
      speech.stop();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    const targetLang = data.detected_language === 'hindi' ? 'marathi' : 'hindi';
    const textToSpeak = data.translation_native;
    speech.speak(textToSpeak, targetLang, 0.85, () => {
      setSpeaking(false);
    });
  };

  // Determine what text to emphasize based on user script selection and Bridge Mode
  const showDevanagari = scriptMode === 'devanagari' || (scriptMode === 'both' && bridgeLevel !== 'beginner');
  const showRoman = scriptMode === 'roman' || (scriptMode === 'both' && bridgeLevel !== 'advanced');

  return (
    <div className="glass-panel-glow rounded-3xl p-6 md:p-8 space-y-6 relative overflow-hidden border border-indigo-500/30">
      {/* Background glow decoration */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header with language indicator & script switch */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            Target: {data.detected_language === 'hindi' ? 'Marathi' : 'Hindi'}
          </span>
          <span className="text-xs text-slate-400">
            Detected: <strong className="text-slate-300 capitalize">{data.detected_language}</strong> ({data.detected_script})
          </span>
          <span className="text-xs text-slate-400">
            {data.model_source === 'reviewed_database' || data.model_source === 'curated_corpus'
              ? 'Reviewed example'
              : data.model_source === 'indictrans2-320m-neural'
                ? 'AI translation'
                : 'Rule translation'}
          </span>
        </div>

        {/* Script selector buttons */}
        <div className="inline-flex rounded-xl bg-slate-900/90 p-1 border border-slate-800">
          {(['both', 'devanagari', 'roman'] as ScriptMode[]).map((mode) => (
            <button
              key={mode}
              onClick={() => onScriptModeChange(mode)}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-all capitalize ${
                scriptMode === mode
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {data.model_source === 'rule_fallback' && <p className="text-xs text-amber-200">This is a rule-based approximation. Some wording may be incomplete; compare it with the lesson examples.</p>}
      {/* Main Translation Display */}
      <div className="space-y-4">
        {showDevanagari && (
          <div className="group relative">
            <label className="text-[11px] font-semibold tracking-wider uppercase text-slate-400 mb-1 block">
              {data.detected_language === 'hindi' ? 'Marathi (Devanagari)' : 'Hindi (Devanagari)'}
            </label>
            <div className="font-devanagari text-2xl sm:text-3xl md:text-4xl font-bold tracking-wide text-white leading-relaxed">
              {data.translation_native}
            </div>
          </div>
        )}

        {showRoman && (
          <div className="pt-2">
            <label className="text-[11px] font-semibold tracking-wider uppercase text-indigo-400 mb-1 block flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              {data.detected_language === 'hindi' ? 'Roman Marathi (Latin Script)' : 'Roman Hindi (Latin Script)'}
            </label>
            <div className="text-xl sm:text-2xl font-semibold tracking-wide text-indigo-200">
              {data.translation_roman}
            </div>
          </div>
        )}
      </div>

      {/* Reviewed English gloss is available for curated examples. */}
      <div className="bg-slate-950/50 rounded-2xl p-4 border border-slate-800/60 flex items-start justify-between gap-4">
        <div>
          <span className="text-xs uppercase tracking-wider font-semibold text-slate-400 block mb-1">
            English meaning
          </span>
          <p className="text-sm sm:text-base text-slate-200 font-medium">
            {data.english_meaning ? `"${data.english_meaning}"` : 'Not available for this sentence yet.'}
          </p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleSpeech}
            title="Listen pronunciation"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-all"
          >
            <Volume2 className={`w-4 h-4 ${speaking ? 'text-indigo-400 animate-pulse' : ''}`} />
          </button>
          <button
            onClick={handleCopy}
            title="Copy translations"
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-all"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Quick Contrast Highlights Banner */}
      {data.differences && data.differences.length > 0 && (
        <div className="bg-gradient-to-r from-amber-950/20 via-indigo-950/30 to-slate-950/40 p-3.5 rounded-xl border border-amber-500/25 space-y-2 animate-in fade-in">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-300 uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Key Contrast Insights (Why It Differs)</span>
            </div>
            {data.explanation_source === 'hybrid_gemini' ? (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                AI Sensei (Gemini)
              </span>
            ) : (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
                Local UD Contrast Engine
              </span>
            )}
          </div>
          <div className="space-y-1 text-xs text-slate-300 leading-relaxed">
            {data.differences.slice(0, 3).map((diff, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">•</span>
                <span>{diff}</span>
              </div>
            ))}
          </div>
          {data.cultural_mnemonic && (
            <div className="mt-2 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 flex items-start gap-2 text-xs text-indigo-200">
              <span className="text-amber-400 font-bold shrink-0">💡 Sensei's Tip:</span>
              <span className="leading-snug">{data.cultural_mnemonic}</span>
            </div>
          )}
        </div>
      )}

      {/* Why? Button & Learn More Footer */}
      <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80">
        <div className="text-xs text-slate-400 flex items-center gap-2">
          <span>Input normalized:</span>
          <code className="text-slate-300 bg-slate-900 px-2 py-0.5 rounded text-[11px] border border-slate-800 font-mono">
            {data.native_text}
          </code>
        </div>

        <button
          id="why-btn"
          onClick={onOpenExplain}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <HelpCircle className="w-4 h-4 text-slate-950" />
          <span>Why is this sentence different?</span>
          <ArrowRight className="w-4 h-4 text-slate-950" />
        </button>
      </div>
    </div>
  );
};
