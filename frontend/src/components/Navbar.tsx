import React from 'react';
import { Sparkles, BarChart2, BookOpen, Layers, Gamepad2, ArrowRightLeft } from 'lucide-react';

interface NavbarProps {
  currentView: 'translate' | 'learn';
  onChangeView: (view: 'translate' | 'learn') => void;
  onOpenDashboard: () => void;
  onOpenPractice: () => void;
  reviewCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  onChangeView,
  onOpenDashboard,
  onOpenPractice,
  reviewCount,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Brand Logo */}
        <div
          onClick={() => onChangeView('translate')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-amber-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/20 group-hover:scale-105 transition-transform">
            <Layers className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-200 bg-clip-text text-transparent">
                BhashaBridge
              </span>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Bridge Mode
              </span>
            </div>
            <p className="text-xs text-slate-400">Hindi ⇄ Marathi without script barriers</p>
          </div>
        </div>

        {/* Center: Main View Navigation */}
        <div className="hidden sm:flex items-center gap-1.5 p-1 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-inner">
          <button
            id="nav-tab-translate"
            onClick={() => onChangeView('translate')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-bold transition-all ${
              currentView === 'translate'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <ArrowRightLeft className="w-3.5 h-3.5" />
            <span>Translate & Bridge</span>
          </button>

          <button
            id="nav-tab-learn"
            onClick={() => onChangeView('learn')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-xl text-xs font-bold transition-all relative ${
              currentView === 'learn'
                ? 'bg-gradient-to-r from-purple-600 via-indigo-600 to-amber-500 text-white shadow-md shadow-purple-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5 text-amber-300" />
            <span>Learn & Play Hub</span>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
          </button>
        </div>

        {/* Right: Practice, Progress */}
        <div className="flex items-center gap-2.5">
          {/* Mobile view switch pill */}
          <button
            onClick={() => onChangeView(currentView === 'translate' ? 'learn' : 'translate')}
            className="sm:hidden flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
          >
            {currentView === 'translate' ? '🎮 Learn' : '🔄 Translate'}
          </button>

          <button
            id="practice-btn-nav"
            onClick={onOpenPractice}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 hover:text-white bg-slate-900/80 hover:bg-slate-800 border border-slate-700/80 transition-all shadow-sm"
          >
            <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden md:inline">Practice</span>
          </button>

          <button
            id="dashboard-btn-nav"
            onClick={onOpenDashboard}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 hover:text-white bg-gradient-to-r from-indigo-950/40 to-slate-900/60 hover:from-indigo-900/60 hover:to-slate-800 border border-indigo-500/30 transition-all shadow-sm group"
          >
            <BarChart2 className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform" />
            <span className="hidden md:inline">Progress</span>
            {reviewCount > 0 && (
              <span className="bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.2 rounded-full font-semibold border border-amber-500/30">
                {reviewCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
