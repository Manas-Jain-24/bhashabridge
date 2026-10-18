import React from 'react';
import { BridgeLevel } from '../types';
import { ShieldCheck, Sparkles, Feather } from 'lucide-react';

interface BridgeModeSelectorProps {
  currentLevel: BridgeLevel;
  onChange: (level: BridgeLevel) => void;
}

export const BridgeModeSelector: React.FC<BridgeModeSelectorProps> = ({
  currentLevel,
  onChange,
}) => {
  const modes: { id: BridgeLevel; title: string; subtitle: string; example: string; icon: any }[] = [
    {
      id: 'beginner',
      title: 'Beginner',
      subtitle: 'Roman Script Only',
      example: 'Mala Marathi shikaychi aahe',
      icon: Feather,
    },
    {
      id: 'intermediate',
      title: 'Intermediate (Bridge)',
      subtitle: 'Roman + Devanagari',
      example: 'Mala Marathi शिकायची आहे',
      icon: Sparkles,
    },
    {
      id: 'advanced',
      title: 'Advanced',
      subtitle: 'Devanagari Only',
      example: 'मला मराठी शिकायची आहे',
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="bg-slate-900/60 p-3 rounded-2xl border border-slate-800/80 shadow-inner">
      <div className="flex items-center justify-between mb-2 px-1">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          Bridge Script Mode
        </span>
        <span className="text-[11px] text-slate-400">
          Gradual transition from Latin to Devanagari
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {modes.map((mode) => {
          const isActive = currentLevel === mode.id;
          const Icon = mode.icon;
          return (
            <button
              key={mode.id}
              onClick={() => onChange(mode.id)}
              className={`text-left p-3 rounded-xl border transition-all relative overflow-hidden ${
                isActive
                  ? 'bg-gradient-to-br from-indigo-950/80 via-slate-900 to-indigo-900/40 border-indigo-500/60 shadow-lg shadow-indigo-900/20 ring-1 ring-indigo-400/30'
                  : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 hover:bg-slate-800/30'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span className={`text-sm font-semibold ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {mode.title}
                  </span>
                </div>
                {isActive && (
                  <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                )}
              </div>
              <div className="text-xs text-slate-400 mt-1">{mode.subtitle}</div>
              <div className="text-xs font-mono text-slate-300 bg-black/40 px-2 py-1 rounded mt-2 border border-white/5 truncate">
                {mode.example}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
