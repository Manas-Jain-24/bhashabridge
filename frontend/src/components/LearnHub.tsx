import React, { useState, useEffect } from 'react';
import {
  GamificationProfile,
  SkillTreeNodeItem,
  ScrambleQuestionItem,
  BlitzQuestionItem,
  StreetScenarioItem,
} from '../types';
import { api } from '../services/api';
import { sfx } from '../utils/soundEffects';
import { BridgeQuestMap } from './learn/BridgeQuestMap';
import { SentenceScrambleGame } from './learn/SentenceScrambleGame';
import { ChaiTapriBlitzGame } from './learn/ChaiTapriBlitzGame';
import { StreetScenarioRoleplay } from './learn/StreetScenarioRoleplay';
import { SrsFlashcardsDeck } from './learn/SrsFlashcardsDeck';
import { DailyQuestsAndPronunciation } from './learn/DailyQuestsAndPronunciation';
import {
  Flame,
  Heart,
  Volume2,
  VolumeX,
  Compass,
  Puzzle,
  Zap,
  MessagesSquare,
  BookOpen,
  Mic,
  Sparkles,
  Loader2,
  Plus,
} from 'lucide-react';

type LearnTabMode = 'quest' | 'scramble' | 'blitz' | 'scenarios' | 'flashcards' | 'voice_studio';

export const LearnHub: React.FC = () => {
  const [activeTab, setActiveTab] = useState<LearnTabMode>('quest');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Gamification Data
  const [profile, setProfile] = useState<GamificationProfile | null>(null);
  const [skillTree, setSkillTree] = useState<SkillTreeNodeItem[]>([]);
  const [scrambleQuestions, setScrambleQuestions] = useState<ScrambleQuestionItem[]>([]);
  const [blitzQuestions, setBlitzQuestions] = useState<BlitzQuestionItem[]>([]);
  const [scenarios, setScenarios] = useState<StreetScenarioItem[]>([]);
  const [isMuted, setIsMuted] = useState(sfx.getIsMuted());

  // Load all gamification assets
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profData, treeData, scrambleData, blitzData, scenarioData] =
        await Promise.all([
          api.getGamificationProfile(),
          api.getSkillTree(),
          api.getScrambleQuestions(),
          api.getBlitzQuestions(),
          api.getStreetScenarios(),
        ]);

      setProfile(profData);
      setSkillTree(treeData);
      setScrambleQuestions(scrambleData);
      setBlitzQuestions(blitzData);
      setScenarios(scenarioData);
    } catch (err: any) {
      console.error(err);
      setError('Failed to load gamified learn hub. Ensure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleMute = () => {
    const muted = sfx.toggleMute();
    setIsMuted(muted);
    if (!muted) sfx.playTileClick();
  };

  const handleXpEarned = async (amount: number) => {
    try {
      const updated = await api.recordGamificationAction({
        action_type: 'xp_gain',
        xp_amount: amount,
      });
      setProfile(updated);
    } catch (e) {
      console.error(e);
    }
  };

  const handleHeartLost = async () => {
    try {
      const updated = await api.recordGamificationAction({
        action_type: 'heart_lost',
      });
      setProfile(updated);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRefillHearts = async () => {
    sfx.playTileClick();
    try {
      const updated = await api.recordGamificationAction({
        action_type: 'heart_refill',
      });
      setProfile(updated);
      sfx.playSuccessChime();
    } catch (e) {
      console.error(e);
    }
  };

  const handleBlitzEnd = async (finalScore: number) => {
    try {
      const updated = await api.recordGamificationAction({
        action_type: 'blitz_score',
        score: finalScore,
      });
      setProfile(updated);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCompleteScenario = async (
    scenarioId: string,
    badgeId: string,
    xpEarned: number
  ) => {
    try {
      const updated = await api.recordGamificationAction({
        action_type: 'complete_scenario',
        scenario_id: scenarioId,
        badge_id: badgeId,
        xp_amount: xpEarned,
      });
      setProfile(updated);
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-4 text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        <p className="text-sm font-medium">Loading Gamified Marathi Learning Hub...</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 rounded-3xl bg-rose-950/40 border border-rose-500/30 text-rose-200 text-center space-y-4">
        <p className="text-sm">{error || 'Could not load gamification state.'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  const xpPercent = Math.min(100, Math.round((profile.xp / profile.next_level_xp) * 100));

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Gamification Top Status Bar */}
      <div className="rounded-3xl p-5 sm:p-6 bg-slate-900/90 border border-slate-800 shadow-xl backdrop-blur-xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* User Rank Title & Level */}
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-amber-500 flex items-center justify-center text-xl shadow-lg shadow-indigo-500/20 ring-2 ring-white/10">
              {profile.level === 1
                ? '🌱'
                : profile.level === 2
                ? '☕'
                : profile.level === 3
                ? '⚡'
                : profile.level === 4
                ? '🏛️'
                : '👑'}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase font-extrabold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">
                  Level {profile.level}
                </span>
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs text-slate-400 font-semibold">Marathi Rank</span>
              </div>
              <h2 className="text-lg sm:text-xl font-extrabold text-white font-devanagari">
                {profile.rank_title}
              </h2>
            </div>
          </div>

          {/* Stats Badges: XP, Streak, Hearts, Mute */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Streak Flame */}
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-2xl bg-orange-500/10 border border-orange-500/30 text-orange-400 text-sm font-extrabold shadow-sm">
              <Flame className="w-4 h-4 fill-current animate-pulse text-orange-400" />
              <span>{profile.streak_days} Day Streak</span>
            </div>

            {/* Hearts Counter */}
            <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-sm font-bold shadow-sm">
              {[1, 2, 3].map((hIdx) => (
                <Heart
                  key={hIdx}
                  className={`w-4 h-4 transition-all ${
                    hIdx <= profile.hearts
                      ? 'fill-rose-500 text-rose-500 drop-shadow-[0_0_6px_rgba(244,63,94,0.6)]'
                      : 'text-slate-700'
                  }`}
                />
              ))}
              {profile.hearts === 0 && (
                <button
                  onClick={handleRefillHearts}
                  title="Refill Hearts"
                  className="ml-1 p-1 rounded-md bg-rose-500/30 text-white hover:bg-rose-500 transition-colors"
                >
                  <Plus className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* XP Total */}
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-sm font-extrabold font-mono shadow-sm">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>{profile.xp} XP</span>
            </div>

            {/* Audio Toggle */}
            <button
              onClick={handleToggleMute}
              title={isMuted ? 'Unmute Game Sounds' : 'Mute Game Sounds'}
              className="p-2 rounded-2xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 hover:text-white transition-all shadow-sm"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4 text-indigo-400" />}
            </button>
          </div>
        </div>

        {/* XP Progress Bar towards Next Rank */}
        <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Next Rank Progress</span>
            <span className="font-mono text-indigo-300">
              {profile.xp} / {profile.next_level_xp} XP ({xpPercent}%)
            </span>
          </div>
          <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-amber-400 transition-all duration-700"
              style={{ width: `${xpPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Mode Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md">
        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('quest');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'quest'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Compass className="w-4 h-4" />
          <span>Bridge Quest</span>
        </button>

        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('scramble');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'scramble'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Puzzle className="w-4 h-4" />
          <span>Sentence Builder</span>
        </button>

        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('blitz');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'blitz'
              ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-lg shadow-orange-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Zap className="w-4 h-4 fill-current text-amber-300" />
          <span>Chai Tapri Blitz</span>
        </button>

        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('scenarios');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'scenarios'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <MessagesSquare className="w-4 h-4" />
          <span>Street Roleplay</span>
        </button>

        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('flashcards');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'flashcards'
              ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Vocabulary Gym</span>
        </button>

        <button
          onClick={() => {
            sfx.playTileClick();
            setActiveTab('voice_studio');
          }}
          className={`flex-1 min-w-[130px] flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl text-xs sm:text-sm font-bold transition-all ${
            activeTab === 'voice_studio'
              ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Mic className="w-4 h-4 text-amber-300" />
          <span>Voice & Quests</span>
        </button>
      </div>

      {/* Active Tab Content Area */}
      <div>
        {activeTab === 'quest' && (
          <BridgeQuestMap
            nodes={skillTree}
            onSelectNode={() => setActiveTab('scramble')}
            onLaunchScramble={() => setActiveTab('scramble')}
            onLaunchBlitz={() => setActiveTab('blitz')}
            onLaunchScenarios={() => setActiveTab('scenarios')}
          />
        )}

        {activeTab === 'scramble' && (
          <SentenceScrambleGame
            questions={scrambleQuestions}
            onCompleteExercise={handleXpEarned}
            onHeartLost={handleHeartLost}
          />
        )}

        {activeTab === 'blitz' && (
          <ChaiTapriBlitzGame
            questions={blitzQuestions}
            highScore={profile.blitz_high_score}
            onGameEnd={handleBlitzEnd}
          />
        )}

        {activeTab === 'scenarios' && (
          <StreetScenarioRoleplay
            scenarios={scenarios}
            unlockedBadges={profile.unlocked_badges}
            onCompleteScenario={handleCompleteScenario}
            onHeartLost={handleHeartLost}
          />
        )}

        {activeTab === 'flashcards' && (
          <SrsFlashcardsDeck onXpEarned={handleXpEarned} />
        )}

        {activeTab === 'voice_studio' && (
          <DailyQuestsAndPronunciation onXpEarned={handleXpEarned} />
        )}
      </div>
    </div>
  );
};
