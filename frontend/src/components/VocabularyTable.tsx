import React, { useState } from 'react';
import { VocabularyItem } from '../types';
import { BookOpen, AlertCircle, Volume2, Sparkles } from 'lucide-react';
import { speech } from '../utils/speechEngine';

interface VocabularyTableProps {
  vocabulary: VocabularyItem[];
  sourceLang: string;
  targetLang: string;
}

export const VocabularyTable: React.FC<VocabularyTableProps> = ({
  vocabulary,
  sourceLang,
  targetLang,
}) => {
  const [playingIndex, setPlayingIndex] = useState<number | null>(null);

  if (!vocabulary || vocabulary.length === 0) return null;

  const handleSpeak = (text: string, index: number) => {
    setPlayingIndex(index);
    speech.speak(text, 'marathi', 0.85, () => {
      setPlayingIndex(null);
    });
  };

  return (
    <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-indigo-400" />
          <h3 className="text-base font-semibold text-white">Learn from this sentence</h3>
        </div>
        <span className="text-xs text-slate-400 font-mono">
          {vocabulary.length} Word & Construction Alignments
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead>
            <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4 font-semibold capitalize">{sourceLang}</th>
              <th className="py-3 px-4 font-semibold capitalize">{targetLang} (Devanagari)</th>
              <th className="py-3 px-4 font-semibold">Roman Script</th>
              <th className="py-3 px-4 font-semibold">Meaning / Function</th>
              <th className="py-3 px-4 font-semibold">Grammar & Gender Contrast</th>
              <th className="py-3 px-4 font-semibold text-right">Alignment Type</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {vocabulary.map((item, idx) => (
              <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-3.5 px-4 font-medium text-slate-200">
                  <span className="font-devanagari text-base font-semibold text-white">{item.source_word}</span>
                </td>
                <td className="py-3.5 px-4 font-devanagari font-semibold text-emerald-300">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{item.target_word}</span>
                    <button
                      onClick={() => handleSpeak(item.target_word, idx)}
                      title="Pronounce word"
                      className="p-1 rounded text-slate-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                    >
                      <Volume2 className={`w-3.5 h-3.5 ${playingIndex === idx ? 'text-emerald-400 animate-pulse' : ''}`} />
                    </button>
                  </div>
                </td>
                <td className="py-3.5 px-4 font-mono text-xs text-indigo-300">
                  {item.target_roman || '—'}
                </td>
                <td className="py-3.5 px-4 text-slate-300">
                  <div className="font-medium text-slate-200">{item.meaning}</div>
                  {item.root_lemma && (
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      <span className="text-indigo-400 font-mono font-semibold">Lemma:</span> {item.root_lemma}
                    </div>
                  )}
                </td>
                <td className="py-3.5 px-4">
                  <div className="space-y-1">
                    {item.gender_contrast && (
                      <div className="text-[11px] px-2 py-0.5 rounded bg-purple-950/40 text-purple-200 border border-purple-500/30 leading-snug">
                        <strong className="text-purple-400 font-semibold mr-1">3-Gender:</strong>
                        {item.gender_contrast}
                      </div>
                    )}
                    {item.morph_analysis && (
                      <div className="text-[11px] px-2 py-0.5 rounded bg-amber-950/30 text-amber-300 border border-amber-500/20 font-mono leading-snug">
                        {item.morph_analysis}
                      </div>
                    )}
                    {!item.gender_contrast && !item.morph_analysis && (
                      <span className="text-xs text-slate-500">—</span>
                    )}
                  </div>
                </td>
                <td className="py-3.5 px-4 text-right">
                  {item.is_construction_based ? (
                    <span className="inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-medium">
                      Construction-based
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[11px] px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      Direct Lexical
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950/40 p-3 rounded-xl border border-slate-800/50">
        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
        <span>
          Note: Hindi and Marathi share Sanskrit cognates, but Marathi preserves the 3-gender system (Masculine, Feminine, Neuter) and attaches synthetic suffixes directly to nouns and verbs.
        </span>
      </div>
    </div>
  );
};
