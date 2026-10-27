import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ProgressData, MilestoneRoadmapItem, BridgeLevel } from '../types';
import {
  X,
  Award,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  TrendingUp,
  Layers,
  Sparkles,
  Lock,
  ArrowRight,
  Compass,
  Check
} from 'lucide-react';

interface ProgressDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  onBridgeLevelChange?: (level: BridgeLevel) => void;
}

export const ProgressDashboard: React.FC<ProgressDashboardProps> = ({
  isOpen,
  onClose,
  onBridgeLevelChange,
}) => {
  const [data, setData] = useState<ProgressData | null>(null);
  const [milestones, setMilestones] = useState<MilestoneRoadmapItem[]>([]);
  const [activeTab, setActiveTab] = useState<'proficiency' | 'roadmap'>('proficiency');
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [updatingMode, setUpdatingMode] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setLoadError(null);
    Promise.all([api.getProgress(), api.getMilestones()])
      .then(([progRes, mileRes]) => {
        setData(progRes);
        setMilestones(mileRes);
      })
      .catch(() => setLoadError('Could not load your progress. Please retry.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) {
      fetchData();
      setUpdateSuccess(null);
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onClose();
        }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  const [updateError, setUpdateError] = useState<string | null>(null);

  const handleApplyRecommendation = async (recMode: string) => {
    try {
      setUpdatingMode(true);
      setUpdateError(null);
      await api.updateBridgeMode(recMode);
      setUpdateSuccess(`Successfully switched to ${recMode.toUpperCase()} mode!`);
      if (onBridgeLevelChange) {
        onBridgeLevelChange(recMode as BridgeLevel);
      }
      fetchData();
    } catch (err) {
      console.error(err);
      setUpdateError(`Failed to switch bridge mode to ${recMode}. Please check connection.`);
      setTimeout(() => setUpdateError(null), 4000);
    } finally {
      setUpdatingMode(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Learner Milestones and Proficiency Dashboard"
      className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4"
    >
      <div className="w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl relative max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-slate-950 font-bold shadow-md shadow-amber-500/20">
              <Award className="w-6 h-6 text-slate-950" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Learner Milestones & Proficiency</h2>
              <p className="text-xs text-slate-400">
                Principle 2: Language Proficiency and Script Mastery tracked independently
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

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800/80 pb-2">
          <button
            onClick={() => setActiveTab('proficiency')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'proficiency'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            <span>Dual Proficiency & Skills</span>
          </button>

          <button
            onClick={() => setActiveTab('roadmap')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'roadmap'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            <Compass className="w-4 h-4" />
            <span>Milestone Roadmap (Levels 0–5)</span>
          </button>
        </div>

        {loadError ? <div role="alert" className="text-rose-300 text-sm">{loadError} <button onClick={fetchData} className="underline">Retry</button></div> : loading || !data ? (
          <div className="py-16 flex flex-col items-center justify-center space-y-3">
            <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin" />
            <span className="text-sm text-slate-400">Fetching skill breakdown and roadmap...</span>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Script Recommendation Banner (Principle 2 Engine) */}
            {data.script_recommendation && (
              <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-950/70 via-slate-900 to-amber-950/40 border border-indigo-500/30 shadow-lg space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-4 h-4 text-indigo-300" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                          Script Progression Recommendation
                        </span>
                        <span className="text-[10px] font-mono bg-indigo-500/20 px-2 py-0.5 rounded text-indigo-200 border border-indigo-500/30">
                          Score: {data.script_recommendation.composite_script_score}%
                        </span>
                      </div>
                      <p className="text-xs text-slate-200 mt-1 leading-relaxed">
                        {data.script_recommendation.recommendation_message}
                      </p>
                    </div>
                  </div>

                  {data.script_recommendation.current_mode !== data.script_recommendation.recommended_mode && (
                    <button
                      onClick={() => handleApplyRecommendation(data.script_recommendation!.recommended_mode)}
                      disabled={updatingMode}
                      className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-md transition-all hover:scale-105 active:scale-95 disabled:opacity-50"
                    >
                      {updatingMode ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <ArrowRight className="w-3.5 h-3.5" />
                      )}
                      <span>{data.script_recommendation.action_label}</span>
                    </button>
                  )}
                </div>

                {updateSuccess && (
                  <div className="text-xs text-emerald-400 flex items-center gap-1.5 pt-1">
                    <Check className="w-3.5 h-3.5" />
                    <span>{updateSuccess}</span>
                  </div>
                )}
                {updateError && (
                  <div className="text-xs text-rose-400 flex items-center gap-1.5 pt-1">
                    <span>{updateError}</span>
                  </div>
                )}
              </div>
            )}

            {/* TAB 1: Dual Proficiency & Skills */}
            {activeTab === 'proficiency' && (
              <div className="space-y-6 animate-in fade-in duration-200">
                {/* Top Cards: Overall & Milestone */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Overall Language Progress */}
                  <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                        Overall Language Progress
                      </span>
                      <span className="text-xs font-semibold text-indigo-400 bg-indigo-500/10 px-2.5 py-0.5 rounded-full border border-indigo-500/20">
                        {data.target_language}
                      </span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-extrabold text-white">{data.overall_percentage}%</span>
                      <span className="text-xs text-slate-400">mastery achieved</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-indigo-500 to-amber-500 h-2.5 rounded-full transition-all duration-1000"
                        style={{ width: `${data.overall_percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Current Milestone */}
                  <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
                        Current Milestone
                      </span>
                      <span className="text-xs font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        {data.current_milestone.level}
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white">
                      {data.current_milestone.title}
                    </div>
                    <div className="flex items-center justify-between text-xs text-slate-300">
                      <span>Progress:</span>
                      <span className="font-semibold text-white">
                        {data.current_milestone.completed_exercises} / {data.current_milestone.total_exercises} exercises
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                      <div
                        className="bg-amber-500 h-2.5 rounded-full transition-all duration-1000"
                        style={{
                          width: `${(data.current_milestone.completed_exercises / data.current_milestone.total_exercises) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Split Skills: Language Proficiency vs Script Proficiency */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Language Proficiency */}
                  <div className="bg-slate-950/50 p-5 rounded-2xl border border-slate-800/80 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-indigo-400" />
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                          Language Skills
                        </h3>
                      </div>
                      <span className="text-[11px] text-slate-400">Meaning & Expression</span>
                    </div>

                    <div className="space-y-3">
                      {data.language_skills.map((skill, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-medium">{skill.name}</span>
                            <span className="text-slate-400 font-mono font-semibold">{skill.percentage}%</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-indigo-500 h-2 rounded-full"
                              style={{ width: `${skill.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Script Proficiency */}
                  <div className="bg-slate-950/50 p-5 rounded-2xl border border-slate-800/80 space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <Layers className="w-4 h-4 text-amber-400" />
                        <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                          Script Skills
                        </h3>
                      </div>
                      <span className="text-[11px] text-slate-400">Devanagari vs Roman</span>
                    </div>

                    <div className="space-y-3">
                      {data.script_skills.map((skill, idx) => (
                        <div key={idx} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-medium">{skill.name}</span>
                            <span className="text-slate-400 font-mono font-semibold">{skill.percentage}%</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-amber-500/80 h-2 rounded-full"
                              style={{ width: `${skill.percentage}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bottom Row: Weak Areas & Review Queue */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-slate-950/70 p-4 rounded-xl border border-rose-500/20 space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                      Identified Weak Areas
                    </span>
                    <ul className="text-xs text-slate-300 space-y-1">
                      {data.weak_areas.map((area, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0" />
                          <span>{area}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-slate-950/70 p-4 rounded-xl border border-amber-500/20 space-y-2 flex flex-col justify-between">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-amber-400" />
                        Vocabulary Revision Queue
                      </span>
                      <p className="text-xs text-slate-300 mt-1">
                        Spaced-repetition queue has <strong className="text-white">{data.review_due_count} words</strong> scheduled for review today.
                      </p>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      Bridge Level: {data.bridge_mode_level}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Milestones Roadmap */}
            {activeTab === 'roadmap' && (
              <div className="space-y-4 animate-in fade-in duration-200">
                <div className="text-xs text-slate-400 pb-1">
                  Complete exercises to progress through the 6 stages of spoken fluency and Devanagari literacy.
                </div>

                <div className="space-y-3">
                  {milestones.map((m) => (
                    <div
                      key={m.id}
                      className={`p-4 rounded-2xl border transition-all ${
                        m.is_active
                          ? 'bg-indigo-950/30 border-indigo-500/40 shadow-lg shadow-indigo-500/5 ring-1 ring-indigo-500/20'
                          : m.status === 'completed'
                          ? 'bg-slate-950/60 border-emerald-500/30'
                          : 'bg-slate-950/40 border-slate-800 opacity-60'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 font-bold text-xs ${
                              m.status === 'completed'
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : m.is_active
                                ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/30'
                                : 'bg-slate-800 text-slate-500'
                            }`}
                          >
                            {m.status === 'completed' ? (
                              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                            ) : m.status === 'locked' ? (
                              <Lock className="w-4 h-4 text-slate-500" />
                            ) : (
                              m.level_number
                            )}
                          </div>

                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono font-semibold text-slate-400">
                                {m.level}
                              </span>
                              {m.is_active && (
                                <span className="text-[10px] uppercase font-bold bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/30">
                                  Current Goal
                                </span>
                              )}
                              {m.status === 'completed' && (
                                <span className="text-[10px] uppercase font-bold bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30">
                                  Completed
                                </span>
                              )}
                            </div>
                            <h4 className="text-sm font-bold text-white mt-0.5">{m.title}</h4>
                            {m.description && (
                              <p className="text-xs text-slate-400 mt-0.5">{m.description}</p>
                            )}
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <div className="text-xs font-mono font-semibold text-white">
                            {m.completed_exercises} / {m.total_exercises}
                          </div>
                          <div className="text-[10px] text-slate-400">
                            {m.progress_percentage}% completed
                          </div>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all duration-700 ${
                            m.status === 'completed'
                              ? 'bg-emerald-500'
                              : m.is_active
                              ? 'bg-gradient-to-r from-indigo-500 to-amber-500'
                              : 'bg-slate-700'
                          }`}
                          style={{ width: `${m.progress_percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
