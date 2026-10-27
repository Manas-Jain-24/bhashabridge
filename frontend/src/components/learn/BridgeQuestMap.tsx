import React from 'react';
import { SkillTreeNodeItem } from '../../types';
import { Lock, Star, CheckCircle2, Play, Sparkles, ChevronRight } from 'lucide-react';
import { sfx } from '../../utils/soundEffects';

interface BridgeQuestMapProps {
  nodes: SkillTreeNodeItem[];
  onSelectNode: (node: SkillTreeNodeItem) => void;
  onLaunchScramble: () => void;
  onLaunchBlitz: () => void;
  onLaunchScenarios: () => void;
}

export const BridgeQuestMap: React.FC<BridgeQuestMapProps> = ({
  nodes,
  onSelectNode,
  onLaunchScramble,
  onLaunchBlitz,
  onLaunchScenarios,
}) => {
  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-950/80 via-slate-900/90 to-purple-950/80 border border-indigo-500/30 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
        <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Your Learning Roadmap</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Build Confidence in Marathi
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              Conquer grammatical differences, eliminate false friends like <span className="text-amber-300 font-semibold">‘काल’</span> vs <span className="text-amber-300 font-semibold">‘उद्या’</span>, and graduate to authentic street fluency.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => {
                sfx.playTileClick();
                onLaunchScramble();
              }}
              className="px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95 flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>Play Sentence Builder</span>
            </button>

            <button
              onClick={() => {
                sfx.playTileClick();
                onLaunchBlitz();
              }}
              className="px-4 py-2.5 rounded-xl font-bold text-xs sm:text-sm bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white shadow-lg shadow-orange-600/30 transition-all hover:scale-105 active:scale-95 flex items-center gap-2"
            >
              <span>🔥 60s Blitz</span>
            </button>
          </div>
        </div>
      </div>

      {/* Visual Roadmap Path */}
      <div className="relative max-w-2xl mx-auto py-6">
        {/* Central Connecting Spine Line */}
        <div className="absolute left-1/2 top-4 bottom-12 w-1.5 -translate-x-1/2 bg-gradient-to-b from-indigo-500 via-purple-500 to-slate-800 rounded-full opacity-60 shadow-[0_0_12px_rgba(99,102,241,0.5)]" />

        <div className="space-y-12 relative z-10">
          {nodes.map((node, idx) => {
            const isCompleted = node.status === 'completed';
            const isInProgress = node.status === 'in_progress';
            const isLocked = node.status === 'locked';

            // Alternating zigzag offset for visual rhythm
            const isLeft = idx % 2 === 0;

            return (
              <div
                key={node.id}
                className={`flex items-center gap-4 sm:gap-8 ${
                  isLeft ? 'flex-row' : 'flex-row-reverse'
                }`}
              >
                {/* Node Milestone Card */}
                <div
                  onClick={() => {
                    if (!isLocked) {
                      sfx.playTileClick();
                      onSelectNode(node);
                    }
                  }}
                  className={`flex-1 group cursor-pointer transition-all duration-300 ${
                    isLocked
                      ? 'opacity-60 cursor-not-allowed'
                      : 'hover:scale-[1.02] hover:-translate-y-0.5'
                  }`}
                >
                  <div
                    className={`rounded-2xl p-4 sm:p-5 border transition-all ${
                      isInProgress
                        ? 'bg-gradient-to-br from-indigo-950/90 via-slate-900/90 to-purple-950/90 border-indigo-500/50 shadow-xl shadow-indigo-500/10 ring-2 ring-indigo-500/40'
                        : isCompleted
                        ? 'bg-slate-900/80 border-emerald-500/30 hover:border-emerald-500/50'
                        : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${
                              isInProgress
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                : isCompleted
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-slate-800 text-slate-500'
                            }`}
                          >
                            Level {node.level} • {node.status.replace('_', ' ')}
                          </span>
                        </div>
                        <h3 className="text-base sm:text-lg font-bold text-white mt-1 group-hover:text-indigo-200 transition-colors">
                          {node.title}
                        </h3>
                        <p className="text-xs text-indigo-300 font-devanagari font-medium mt-0.5">
                          {node.marathi_title}
                        </p>
                      </div>

                      {/* Stars Rating */}
                      <div className="flex items-center gap-0.5 shrink-0">
                        {[1, 2, 3].map((starIdx) => (
                          <Star
                            key={starIdx}
                            className={`w-3.5 h-3.5 ${
                              starIdx <= node.stars
                                ? 'fill-amber-400 text-amber-400 drop-shadow-[0_0_6px_rgba(251,191,36,0.6)]'
                                : 'text-slate-700'
                            }`}
                          />
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                      {node.description}
                    </p>

                    {/* Key Concept Chips */}
                    <div className="flex flex-wrap items-center gap-1.5 mt-3 pt-3 border-t border-slate-800/80">
                      {node.key_concepts.map((concept, cIdx) => (
                        <span
                          key={cIdx}
                          className="text-[10px] px-2 py-0.5 rounded-md bg-slate-800/80 text-slate-300 font-mono"
                        >
                          {concept}
                        </span>
                      ))}
                    </div>

                    {/* Progress Bar */}
                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Exercises</span>
                      <span className="font-semibold text-white">
                        {node.completed_count}/{node.exercises_count}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full mt-1 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isCompleted
                            ? 'bg-emerald-500'
                            : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                        }`}
                        style={{
                          width: `${Math.round(
                            (node.completed_count / Math.max(1, node.exercises_count)) * 100
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Central Circle Node Marker */}
                <div
                  onClick={() => {
                    if (!isLocked) {
                      sfx.playTileClick();
                      onSelectNode(node);
                    }
                  }}
                  className={`relative shrink-0 w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center font-bold text-xl sm:text-2xl shadow-xl transition-all duration-300 cursor-pointer ${
                    isInProgress
                      ? 'bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 text-white ring-4 ring-indigo-500/40 shadow-indigo-500/50 scale-110 animate-pulse'
                      : isCompleted
                      ? 'bg-gradient-to-tr from-emerald-600 to-teal-500 text-white ring-2 ring-emerald-500/40'
                      : 'bg-slate-900 border border-slate-800 text-slate-600'
                  }`}
                >
                  {isLocked ? (
                    <Lock className="w-5 h-5 text-slate-600" />
                  ) : isCompleted ? (
                    <CheckCircle2 className="w-6 h-6 text-white" />
                  ) : (
                    <span>{node.icon}</span>
                  )}

                  {/* Level Number Pill */}
                  <div className="absolute -bottom-2 px-2 py-0.5 rounded-full text-[9px] font-bold bg-slate-950 border border-slate-700 text-slate-300">
                    L{node.level}
                  </div>
                </div>

                {/* Empty Balancing Spacer for Flex row */}
                <div className="flex-1 hidden sm:block" />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
