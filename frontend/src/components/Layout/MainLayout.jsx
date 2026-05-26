import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ToastContainer } from '../UI/Toast';
import VisualizationSelector from '../UI/VisualizationSelector';
import { audioFeedback } from '../../utils/audioFeedback';
import {
  Command, Compass, Clock, Scroll, Radio, Sparkles, BookOpen, Search, LayoutDashboard, Volume2
} from 'lucide-react';

export default function MainLayout({
  children,
  crtEnabled,
  setCrtEnabled,
  isConnected,
  isPlaying,
  frequency,
  volume,
  prayerBowlMode,
  generateAudio,
  playAudio,
  stopAudio,
  mopsData,
  visualizationType,
  handleVisualizationChange
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTab = location.pathname.split('/')[1] || 'command-center';

  const [quickSearchOpen, setQuickSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 'k':
            e.preventDefault();
            setQuickSearchOpen(prev => !prev);
            break;
          case 'b':
            e.preventDefault();
            navigate(activeTab === 'command-center' ? '/visualizers' : '/command-center');
            break;
          case 'd':
            e.preventDefault();
            handleVisualizationChange('trends');
            navigate('/visualizers');
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, navigate, handleVisualizationChange]);

  const handleTabClick = (tab) => {
    audioFeedback.playTick();
    navigate(`/${tab}`);
  };

  return (
    <div className={`min-h-screen bg-transparent text-white flex flex-col font-sans relative overflow-hidden ${crtEnabled ? 'crt-screen' : ''}`}>
      {/* Cyberdeck HUD layers */}
      {crtEnabled && <div className="scanline absolute inset-0 pointer-events-none z-[100]" />}
      {crtEnabled && <div className="scanline-sweep" />}
      <div className="cyber-grid" />

      {/* Toast Notifications */}
      <ToastContainer />
      
      {/* Header - Mobile Responsive */}
      <header className="p-2 md:p-3 z-20 glassmorphism mystical-border relative">
        <div className="max-w-full mx-auto flex flex-col md:flex-row justify-between items-center gap-3">
          
          {/* Logo & status */}
          <div className="flex items-center space-x-2 md:space-x-3 w-full md:w-auto justify-between md:justify-start">
            <h1 className="text-lg md:text-xl font-bold text-vajra-cyan glow-cyan tracking-wider flex items-center gap-2">
              🔮 Vajra.Stream
            </h1>
            <div className="flex items-center space-x-2 px-2.5 py-1 bg-black/40 border border-white/10 rounded-full select-none">
              <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`} />
              <span className="text-[10px] font-bold font-serif uppercase tracking-wider text-gray-300">
                {isConnected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
          
          {/* Tab Navigation in Center */}
          <div className="flex-1 flex justify-center w-full md:w-auto">
            <nav className="flex items-center space-x-1 bg-gray-900/60 rounded-xl p-1 border border-white/5 overflow-x-auto max-w-full scrollbar-none">
              <button
                onClick={() => handleTabClick('command-center')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'command-center'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Command className="w-3.5 h-3.5 text-vajra-purple" />
                <span>Command Center</span>
              </button>
              
              <button
                onClick={() => handleTabClick('operations')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'operations'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Compass className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Operations</span>
              </button>

              <button
                onClick={() => handleTabClick('astrology')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'astrology'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Clock className="w-3.5 h-3.5 text-vajra-cyan animate-pulse" />
                <span>Cosmic Clock</span>
              </button>

              <button
                onClick={() => handleTabClick('outlook')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'outlook'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Scroll className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Outlook</span>
              </button>

              <button
                onClick={() => handleTabClick('broadcast')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'broadcast'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Radio className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Broadcast</span>
              </button>

              <button
                onClick={() => handleTabClick('visualizers')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'visualizers'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-vajra-purple" />
                <span>Visualizer</span>
              </button>

              <button
                onClick={() => handleTabClick('grimoire')}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'grimoire'
                    ? 'bg-gradient-to-r from-purple-600/90 to-indigo-600/90 text-white shadow-[0_0_12px_rgba(139,92,246,0.3)] border border-purple-400/30'
                    : 'text-gray-400 hover:text-purple-300 hover:bg-purple-900/10'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5 text-vajra-purple" />
                <span>Grimoire</span>
              </button>
            </nav>
          </div>
          
          {/* Desktop Status Indicator & Visualizer Selector */}
          <div className="flex items-center space-x-4 w-full md:w-auto justify-between md:justify-end">
            {activeTab === 'visualizers' && (
              <VisualizationSelector
                currentType={visualizationType}
                onChange={handleVisualizationChange}
              />
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex flex-1 overflow-hidden relative">
        {children}
      </main>

      {/* Quick Search / Command Palette */}
      {quickSearchOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]"
          onClick={() => setQuickSearchOpen(false)}
        >
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-lg bg-gray-800 border border-gray-600 rounded-xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
              <Search className="w-5 h-5 text-gray-400" />
              <input
                autoFocus
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  audioFeedback.playType();
                }}
                placeholder="Search commands..."
                className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none text-sm"
                onKeyDown={(e) => {
                  if (e.key === 'Escape') setQuickSearchOpen(false);
                }}
              />
              <kbd className="px-1.5 py-0.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-400">Esc</kbd>
            </div>
            <div className="p-2 max-h-72 overflow-y-auto">
              {[
                { icon: LayoutDashboard, label: 'Dashboard / Trends', shortcut: 'Ctrl+D', action: () => { handleVisualizationChange('trends'); navigate('/visualizers'); setQuickSearchOpen(false); } },
                { icon: Volume2, label: 'AI Command Center', shortcut: 'Ctrl+B', action: () => { navigate('/command-center'); setQuickSearchOpen(false); } },
              ].map((item) => (
                <button
                  key={item.label}
                  onClick={item.action}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-700/70 text-left transition-colors"
                >
                  <item.icon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-200 flex-1">{item.label}</span>
                  <span className="text-xs text-gray-500">{item.shortcut}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="px-4 py-2 glassmorphism mystical-border z-10">
        <div className="max-w-full mx-auto flex flex-col md:flex-row justify-between items-center text-xs text-gray-400 gap-2">
          <div className="text-purple-300 font-semibold flex items-center gap-2">
            <span>Vajra.Stream - Sacred Technology Platform</span>
            {mopsData && (
              <span className="text-[10px] text-cyan-400 font-mono px-2 py-0.5 bg-cyan-950/40 rounded border border-cyan-800/20 select-none">
                MOPS: Scalar {(mopsData.scalar_pulses?.["1s"] / 1000000 || 0).toFixed(2)}M/s | Mantra {Math.round(mopsData.mantras?.["10s"] || 0)}/s | Crystals {Math.round(mopsData.crystals?.["10s"] || 0)}/s | Divination {mopsData.divination?.["60s"] || 0}/s
              </span>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <button onClick={async () => { if (!isPlaying) { await generateAudio(); await playAudio(); } else { stopAudio(); } }} className="hover:text-white transition-colors">
              <span>Frequency: <span className="frequency-display text-vajra-cyan font-bold">{frequency.toFixed(1)} Hz</span></span>
              <span className="ml-1 text-[10px]">{isPlaying ? '⏹' : '▶'}</span>
            </button>
            <span>Volume: <span className="text-vajra-cyan glow-cyan font-bold">{Math.round(volume * 100)}%</span></span>
            <span>Mode: <span className="text-vajra-purple glow-text font-bold">{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</span></span>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="font-semibold">{isConnected ? 'Connected' : 'Offline'}</span>
            </div>
            <button
              onClick={() => { setCrtEnabled(prev => !prev); audioFeedback.playClick(); }}
              className={`text-[10px] px-2 py-0.5 rounded border transition-all ${
                crtEnabled
                  ? 'bg-purple-950 border-purple-500 text-vajra-cyan'
                  : 'bg-white/5 border-white/10 text-gray-500 hover:text-white'
              }`}
              title="Toggle CRT overlay"
            >
              📺 HUD
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
