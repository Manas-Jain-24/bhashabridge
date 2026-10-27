import React, { useState } from 'react';
import { StreetScenarioItem, StreetScenarioStepItem, StreetScenarioChoiceItem } from '../../types';
import { sfx } from '../../utils/soundEffects';
import { triggerConfetti } from '../../utils/confetti';
import {
  MapPin,
  Award,
  CheckCircle2,
  Sparkles,
  MessageSquare,
  ArrowRight,
  RotateCcw,
  Check,
  Flame,
} from 'lucide-react';

interface StreetScenarioRoleplayProps {
  scenarios: StreetScenarioItem[];
  unlockedBadges: string[];
  onCompleteScenario: (scenarioId: string, choiceIds: string[]) => Promise<{ xp: number; badge: boolean }>;
  onHeartLost: () => void;
}

export const StreetScenarioRoleplay: React.FC<StreetScenarioRoleplayProps> = ({
  scenarios,
  unlockedBadges,
  onCompleteScenario,
  onHeartLost,
}) => {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [selectedChoice, setSelectedChoice] = useState<StreetScenarioChoiceItem | null>(null);
  const [isCompleted, setIsCompleted] = useState(false);
  const [choices, setChoices] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState({ xp: 0, badge: false });
  const [saveError, setSaveError] = useState<string | null>(null);

  const activeScenario = scenarios.find((s) => s.id === selectedScenarioId);
  const activeStep: StreetScenarioStepItem | undefined =
    activeScenario?.steps[currentStepIdx];

  const handleStartScenario = (id: string) => {
    sfx.playTileClick();
    setSelectedScenarioId(id);
    setChoices([]);
    setSaveError(null);
    setCurrentStepIdx(0);
    setSelectedChoice(null);
    setIsCompleted(false);
  };

  const handleSelectChoice = (choice: StreetScenarioChoiceItem) => {
    setSelectedChoice(choice);
    if (choice.is_best) {
      sfx.playSuccessChime();
    } else if (choice.is_hindi_slip) {
      sfx.playErrorBuzz();
      onHeartLost();
    } else {
      sfx.playTileClick();
    }
  };

  const handleNextStep = async () => {
    if (!activeScenario || !activeStep || !selectedChoice || saving) return;
    const nextChoices = [...choices, selectedChoice.id];

    sfx.playTileClick();
    const nextIdx = currentStepIdx + 1;
    if (nextIdx < activeScenario.steps.length) {
      setChoices(nextChoices);
      setCurrentStepIdx(nextIdx);
      setSelectedChoice(null);
    } else {
      setSaving(true);
      setSaveError(null);
      try { setSaved(await onCompleteScenario(activeScenario.id, nextChoices)); }
      catch { setSaveError('Could not save your scenario. Please retry.'); return; }
      finally { setSaving(false); }
      // Completed entire scenario!
      setIsCompleted(true);
      sfx.playVictoryFanfare();
      triggerConfetti();

    }
  };

  // Scenario Cards Grid View
  if (!selectedScenarioId || !activeScenario) {
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Interactive Pune & Mumbai Simulations</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
            Street Scenarios Roleplay
          </h2>
          <p className="text-sm text-slate-400">
            Put your Marathi into real conversation. Choose authentic phrasing to earn respect and unlock collectible city badges!
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {scenarios.map((sc) => {
            const hasBadge = unlockedBadges.includes(sc.badge_id);

            return (
              <div
                key={sc.id}
                onClick={() => handleStartScenario(sc.id)}
                className="group cursor-pointer rounded-3xl p-6 bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-purple-500/40 shadow-xl transition-all hover:scale-[1.02] flex flex-col justify-between"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-3xl p-3 rounded-2xl bg-slate-800 border border-slate-700 shadow-md">
                      {sc.badge_icon}
                    </span>
                    {hasBadge && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        <Award className="w-3.5 h-3.5" />
                        <span>Badge Earned</span>
                      </span>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-1.5 text-xs text-purple-400 font-medium">
                      <MapPin className="w-3.5 h-3.5" />
                      <span>{sc.location}</span>
                    </div>
                    <h3 className="text-lg font-bold text-white mt-1 group-hover:text-purple-200 transition-colors">
                      {sc.title}
                    </h3>
                    <p className="text-xs text-slate-400 font-devanagari mt-0.5">
                      {sc.marathi_title}
                    </p>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">
                    {sc.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-xs text-slate-500 font-mono">
                    Reward: {sc.badge_name}
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-bold text-indigo-400 group-hover:translate-x-1 transition-transform">
                    <span>Start</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Completed Victory Modal View
  if (isCompleted) {
    return (
      <div className="max-w-xl mx-auto rounded-3xl p-8 sm:p-10 bg-slate-900/90 border border-purple-500/40 text-center space-y-6 shadow-2xl backdrop-blur-xl animate-in zoom-in-95">
        <div className="w-24 h-24 mx-auto rounded-3xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-5xl shadow-xl shadow-purple-500/30">
          {activeScenario.badge_icon}
        </div>

        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30 text-xs font-bold uppercase tracking-wider">
            <Award className="w-3.5 h-3.5" />
            <span>{saved.badge ? "Badge Earned" : "Scenario Complete"}</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
            {activeScenario.badge_name}
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Your choices are saved. Review the feedback and try another conversation.
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-indigo-300">
          Saved <span className="font-bold text-white">+{saved.xp} XP</span>. A badge is earned when every choice uses the best phrasing. Replays do not award more XP.
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => setSelectedScenarioId(null)}
            className="px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition-all"
          >
            Back to Scenarios
          </button>
        </div>
      </div>
    );
  }

  // Active Dialogue Flow
  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-in fade-in duration-300">
      {saveError && <p role="alert" className="text-sm text-rose-300">{saveError}</p>}
      {/* Top Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <button
            onClick={() => setSelectedScenarioId(null)}
            className="text-xs text-slate-400 hover:text-white transition-colors mb-1"
          >
            ← Back to all scenarios
          </button>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-white">{activeScenario.title}</h2>
            <span className="text-xs text-slate-500">•</span>
            <span className="text-xs text-purple-400 font-mono">
              Step {currentStepIdx + 1} of {activeScenario.steps.length}
            </span>
          </div>
        </div>

        <span className="text-3xl p-2 rounded-xl bg-slate-900 border border-slate-800">
          {activeScenario.badge_icon}
        </span>
      </div>

      {/* NPC Dialogue Box */}
      {activeStep && (
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-800 border border-slate-700 flex items-center justify-center text-2xl">
              {activeStep.avatar}
            </div>
            <div>
              <div className="font-bold text-white text-sm">{activeStep.speaker}</div>
              <div className="text-xs text-slate-400 flex items-center gap-1">
                <MapPin className="w-3 h-3 text-purple-400" />
                <span>{activeScenario.location}</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/80 border border-indigo-500/20 space-y-2">
            <p className="text-lg sm:text-xl font-bold text-white font-devanagari leading-relaxed">
              "{activeStep.dialogue_devanagari}"
            </p>
            <p className="text-xs text-indigo-300 font-mono">
              {activeStep.dialogue_roman}
            </p>
            <p className="text-xs text-slate-400 italic">
              Meaning: "{activeStep.english_meaning}"
            </p>
          </div>
        </div>
      )}

      {/* Player Response Choices */}
      <div className="space-y-3">
        <div className="text-xs font-semibold text-slate-400 px-1">
          Choose your response:
        </div>

        <div className="space-y-3">
          {activeStep?.choices.map((choice) => {
            const isSelected = selectedChoice?.id === choice.id;

            return (
              <button
                key={choice.id}
                onClick={() => handleSelectChoice(choice)}
                className={`w-full text-left p-4 sm:p-5 rounded-2xl border transition-all ${
                  isSelected
                    ? choice.is_best
                      ? 'bg-emerald-950/40 border-emerald-500/50 ring-2 ring-emerald-500/30'
                      : choice.is_hindi_slip
                      ? 'bg-rose-950/40 border-rose-500/50 ring-2 ring-rose-500/30'
                      : 'bg-indigo-950/40 border-indigo-500/50'
                    : 'bg-slate-900/70 hover:bg-slate-850 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-base sm:text-lg font-bold text-white font-devanagari">
                      {choice.text_devanagari}
                    </p>
                    <p className="text-xs text-indigo-300 font-mono">
                      {choice.text_roman}
                    </p>
                    <p className="text-xs text-slate-400 italic">
                      "{choice.english}"
                    </p>
                  </div>

                  <div className="shrink-0 mt-1">
                    {isSelected && choice.is_best && (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Reaction and Feedback Drawer */}
      {selectedChoice && (
        <div
          className={`p-5 rounded-2xl border animate-in slide-in-from-bottom-2 duration-200 ${
            selectedChoice.is_best
              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
              : selectedChoice.is_hindi_slip
              ? 'bg-rose-950/30 border-rose-500/40 text-rose-200'
              : 'bg-slate-900/90 border-slate-700 text-slate-200'
          }`}
        >
          <div className="space-y-3">
            <div className="flex items-center gap-2 font-bold text-sm">
              <span>{activeStep?.speaker}'s Reaction:</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <p className="font-bold text-white font-devanagari text-base">
                "{selectedChoice.reaction_devanagari}"
              </p>
              <p className="text-xs text-indigo-300 font-mono">
                {selectedChoice.reaction_roman}
              </p>
            </div>

            <p className="text-xs leading-relaxed opacity-90">{selectedChoice.feedback}</p>

            <div className="pt-2 flex justify-end">
              <button
                disabled={saving} onClick={handleNextStep}
                className="px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95 flex items-center gap-2"
              >
                <span>Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
