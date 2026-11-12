import { languages, type Language } from '../config/languages';
import React, { useState, useEffect, useRef } from 'react';
import { AnalyzeResponse, ScriptMode, BridgeLevel } from '../types';
import { HelpCircle, Copy, Check, Volume2, Sparkles, ArrowRight } from 'lucide-react';
import { speech } from '../utils/speechEngine';

interface TranslationCardProps {
  data: AnalyzeResponse;
  scriptMode: ScriptMode;
  onScriptModeChange: (mode: ScriptMode) => void;
  onOpenExplain: () => void;
  bridgeLevel: BridgeLevel;
  onChooseMeaning?: (sourceText: string) => void;
}

export const TranslationCard: React.FC<TranslationCardProps> = ({
  data,
  scriptMode,
  onScriptModeChange,
  onOpenExplain,
  bridgeLevel,
  onChooseMeaning,
}) => {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState<'native' | 'english' | null>(null);
  const [copiedEnglish,setCopiedEnglish]=useState(false);
  const speechRequest=useRef(0);

  const [copyError, setCopyError] = useState(false);
  useEffect(() => {
    setCopied(false);
    setCopyError(false);
    setSpeaking(null); setCopiedEnglish(false); ++speechRequest.current;
    speech.stop();
    return () => { ++speechRequest.current; speech.stop(); };
  }, [data]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(`${data.translation_native}\n${data.translation_roman}`);
      setCopied(true);
      setCopyError(false);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopyError(true);
    }
  };

  const handleSpeech = (kind: 'native' | 'english' = 'native') => {
    const request=++speechRequest.current;
    if (speaking===kind) {
      speech.stop();
      setSpeaking(null);
      return;
    }
    setSpeaking(kind);
    const targetLang = kind==='english'?'english':data.target_language;
    const textToSpeak = kind==='english'?data.english_meaning:data.translation_native;
    speech.speak(textToSpeak, targetLang, 0.85, () => {
      if(speechRequest.current===request) setSpeaking(null);
    });
  };

  const handleCopyEnglish=async()=>{
    if(!data.english_meaning) return;
    try { await navigator.clipboard.writeText(data.english_meaning); setCopiedEnglish(true); setCopyError(false); }
    catch { setCopyError(true); }
  };

  // Determine what text to emphasize based on user script selection and Bridge Mode
  const showDevanagari = scriptMode === 'devanagari' || (scriptMode === 'both' && bridgeLevel !== 'beginner');
  const showRoman = scriptMode === 'roman' || (scriptMode === 'both' && bridgeLevel !== 'advanced');

  return (
    <div className="glass-panel-glow rounded-3xl p-6 md:p-8 space-y-6 relative overflow-hidden border border-indigo-500/30 [overflow-wrap:anywhere]">
      {/* Background glow decoration */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header with language indicator & script switch */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            Target: {languages[data.target_language as Language]?.label || data.target_language}
          </span>
          <span className="text-xs text-slate-400">
            Detected: <strong className="text-slate-300 capitalize">{data.detected_language}</strong> ({data.detected_script})
          </span>
          <span className="text-xs text-slate-400">
            {data.model_source === 'reviewed_database' || data.model_source === 'curated_corpus'
              ? 'Reviewed example'
              : data.model_source === 'gemini-contextual'
                ? 'Gemini-assisted'
              : data.model_source?.startsWith('indictrans2-320m-neural')
                ? 'AI translation'
                : 'Rule translation'}
          </span>
        </div>

        {/* Script selector buttons */}
        <div className="inline-flex rounded-xl bg-slate-900/90 p-1 border border-slate-800">
          {(['both', 'devanagari', 'roman'] as ScriptMode[]).map((mode) => (
            <button
              key={mode === 'devanagari' ? 'Native' : mode}
              onClick={() => onScriptModeChange(mode)}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-all capitalize ${
                scriptMode === mode
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              {mode === 'devanagari' ? 'Native' : mode}
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
              {languages[data.target_language as Language]?.label} ({languages[data.target_language as Language]?.script_label})
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
              Roman {languages[data.target_language as Language]?.label} (Latin Script)
            </label>
            <div className="text-xl sm:text-2xl font-semibold tracking-wide text-indigo-200">
              {data.translation_roman}
            </div>
          </div>
        )}
      </div>

      {data.quality_note && <p role="status" className="rounded-xl border border-amber-500/30 p-3 text-sm text-amber-100">{data.quality_note}</p>}
      {data.meaning_note && <div role="note" className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4 space-y-3 text-sm text-amber-100">
        <p>{data.meaning_note}</p>
        {onChooseMeaning && <div className="flex flex-wrap gap-2">{data.meaning_alternatives?.map(option=><button key={option.source_text} onClick={()=>onChooseMeaning(option.source_text)} className="rounded-xl border border-amber-400/30 px-3 py-2 text-xs hover:bg-amber-500/10">{option.label}</button>)}</div>}
      </div>}

      <div className="flex flex-wrap gap-3 text-xs text-slate-300">
        <button onClick={()=>handleSpeech('native')} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2"><Volume2 className="w-4 h-4" />{speaking==='native'?'Stop audio':`Listen in ${languages[data.target_language as Language]?.label}`}</button>
        <button onClick={handleCopy} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2">{copied?<Check className="w-4 h-4" />:<Copy className="w-4 h-4" />}{copied?'Copied':'Copy translation'}</button>
      </div>

      {/* Keep reviewed glosses distinct from optional generated meanings. */}
      <div className="bg-slate-950/50 rounded-2xl p-4 border border-slate-800/60 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <span className="text-xs uppercase tracking-wider font-semibold text-slate-400 block mb-1">
            English meaning
          </span>
          {data.english_meaning && data.english_meaning_source==='ai_generated' && <span className="text-xs text-indigo-300 block mb-2">AI-generated meaning</span>}
          <p className="text-sm sm:text-base text-slate-200 font-medium">
            {data.english_meaning ? `"${data.english_meaning}"` : 'English meaning is temporarily unavailable. Try again when the AI tutor is connected.'}
          </p>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={()=>handleSpeech('english')}
            title="Listen to English meaning"
            aria-label={speaking==='english'?'Stop English audio':'Listen to English meaning'}
            disabled={!data.english_meaning}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-all disabled:opacity-30"
          >
            <Volume2 className={`w-4 h-4 ${speaking==='english' ? 'text-indigo-400 animate-pulse' : ''}`} />
          </button>
          <button
            onClick={handleCopyEnglish}
            title="Copy English meaning"
            aria-label="Copy English meaning"
            disabled={!data.english_meaning}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-all disabled:opacity-30"
          >
            {copiedEnglish ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {copyError && <p role="status" className="text-xs text-amber-200">Copy was blocked by the browser. Select the translation text to copy it.</p>}

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
          <span>{data.context_status === 'assisted' ? 'Interpreted source:' : 'Input normalized:'}</span>
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
