import React, { useState, useEffect, useCallback } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioStore } from './stores/audioStore';
import { useUIStore } from './stores/uiStore';
import SacredGeometry from './components/3D/SacredGeometry';
import CrystalGrid from './components/3D/CrystalGrid';
import SacredMandala from './components/3D/SacredMandala';
import RadionicsVisualization from './components/3D/RadionicsVisualization';
import AudioSpectrum from './components/2D/AudioSpectrum';
import LiveWaveVisualizer from './components/2D/LiveWaveVisualizer';
import ScalarWaveVisualizer from './components/2D/ScalarWaveVisualizer';
import ControlPanel from './components/UI/ControlPanel';
import SessionManager from './components/UI/SessionManager';
import VisualizationSelector from './components/UI/VisualizationSelector';
import RNGAttunement from './components/UI/RNGAttunement';
import BlessingSlideshow from './components/UI/BlessingSlideshow';
import PopulationManager from './components/UI/PopulationManager';
import AutomationControl from './components/UI/AutomationControl';
import DharmaTales from './components/UI/DharmaTales';
import ChakraHealing from './components/UI/ChakraHealing';
import RadionicsNarrative from './components/UI/RadionicsNarrative';
import RateTuner from './components/UI/RateTuner';
import CrystalProgramming from './components/UI/CrystalProgramming';
import RadionicsBroadcastPanel from './components/UI/RadionicsBroadcastPanel';
import Dashboard from './components/UI/Dashboard';
import LLMInsightsPanel from './components/UI/LLMInsightsPanel';
import { ToastContainer } from './components/UI/Toast';
import { SidebarSection } from './components/UI/SidebarSection';
import ChakraAlignmentStrip from './components/UI/ChakraAlignmentStrip';
import CommandCenter from './components/UI/CommandCenter';
import ManualSettingsTab from './components/UI/ManualSettingsTab';
import { audioFeedback } from './utils/audioFeedback';
import {
  Volume2, Clock, Heart, Sparkles, Zap, Users, Radio, BookOpen,
  Sliders, Gem, LayoutDashboard, Search, Command, TrendingUp,
  ChevronDown, ChevronRight, Monitor
} from 'lucide-react';

const VIEWS = {
  visualization: 'visualization',
  dashboard: 'dashboard'
};

function App() {
  const [visualizationType, setVisualizationType] = useState('sacred-geometry');
  const [activeTab, setActiveTab] = useState('command-center');
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);
  const [crtEnabled, setCrtEnabled] = useState(true);
  
  const { 
    audioSpectrum, 
    isConnected, 
    sessions, 
    startSession, 
    stopSession,
    connectionStatus,
    lastUpdate,
    crystalStatus,
    scalarStatus
  } = useWebSocket();
  
  const {
    isPlaying,
    frequency,
    volume,
    prayerBowlMode,
    harmonicStrength,
    modulationDepth,
    duration,
    updateSettings,
    generateAudio,
    playAudio,
    stopAudio,
    audioStatus
  } = useAudioStore();

  useEffect(() => {
    updateSettings({
      frequency: 136.1,
      volume: 0.8,
      prayerBowlMode: true,
      harmonicStrength: 0.3,
      modulationDepth: 0.05
    });
  }, [updateSettings]);

  const isFirstRender = React.useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    audioFeedback.playTabChange();
  }, [activeTab]);

  useEffect(() => {
    if (isFirstRender.current) return;
    audioFeedback.playClick();
  }, [visualizationType]);

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
            setActiveTab(prev => prev === 'command-center' ? 'visualizers' : 'command-center');
            break;
          case 'd':
            e.preventDefault();
            setActiveTab('visualizers');
            setVisualizationType('trends');
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleVisualizationChange = (type) => {
    setVisualizationType(type);
    setActiveTab('visualizers');
  };

  const handleGenerateAudio = async () => {
    const success = await generateAudio();
    if (success) console.log('Audio generated successfully');
  };

  const handlePlayAudio = async () => {
    const success = await playAudio();
    if (success) console.log('Audio playback started');
  };

  const handleStopAudio = () => {
    stopAudio();
  };

  return (
    <div className={`min-h-screen bg-gray-900 text-white flex flex-col font-sans relative overflow-hidden ${crtEnabled ? 'crt-screen' : ''}`}>
      {/* Cyberdeck HUD layers */}
      {crtEnabled && <div className="scanline absolute inset-0 pointer-events-none z-[100]" />}
      {crtEnabled && <div className="scanline-sweep" />}
      <div className="cyber-grid animate-pulse-glow" />

      {/* Toast Notifications */}
      <ToastContainer />
      
      {/* Header - Mobile Responsive */}
      <header className="bg-gray-800 border-b border-gray-700 p-2 md:p-3 z-20 glassmorphism mystical-border relative">
        <div className="max-w-full mx-auto flex flex-col md:flex-row justify-between items-center gap-3">
          
          {/* Logo & Mobile status */}
          <div className="flex items-center space-x-2 md:space-x-3 w-full md:w-auto justify-between md:justify-start">
            <h1 className="text-lg md:text-xl font-bold text-vajra-cyan glow-cyan tracking-wider flex items-center gap-2">
              🔮 Vajra.Stream
            </h1>
            <div className="md:hidden flex items-center space-x-2 px-2.5 py-1 bg-black/40 border border-white/10 rounded-full select-none">
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
                onClick={() => setActiveTab('command-center')}
                onMouseEnter={() => audioFeedback.playTick()}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'command-center'
                    ? 'bg-purple-600/90 text-white shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Command className="w-3.5 h-3.5 text-vajra-purple" />
                <span>Command Center</span>
              </button>
              
              <button
                onClick={() => setActiveTab('visualizers')}
                onMouseEnter={() => audioFeedback.playTick()}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'visualizers'
                    ? 'bg-purple-600/90 text-white shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Visualizers</span>
              </button>

              <button
                onClick={() => setActiveTab('manual')}
                onMouseEnter={() => audioFeedback.playTick()}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'manual'
                    ? 'bg-purple-600/90 text-white shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Sliders className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Manual Controls</span>
              </button>

              <button
                onClick={() => setActiveTab('targets')}
                onMouseEnter={() => audioFeedback.playTick()}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'targets'
                    ? 'bg-purple-600/90 text-white shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Users className="w-3.5 h-3.5 text-vajra-cyan" />
                <span>Targets</span>
              </button>

              <button
                onClick={() => setActiveTab('lore')}
                onMouseEnter={() => audioFeedback.playTick()}
                className={`px-3 py-1.5 rounded-lg text-xs md:text-sm font-semibold transition-all duration-300 flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === 'lore'
                    ? 'bg-purple-600/90 text-white shadow-lg shadow-purple-500/20'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <BookOpen className="w-3.5 h-3.5 text-vajra-purple" />
                <span>Lore & Wisdom</span>
              </button>
            </nav>
          </div>
          
          {/* Desktop Status Indicator & Visualizer Selector */}
          <div className="flex items-center space-x-4 w-full md:w-auto justify-between md:justify-end">
            <button
              onClick={() => { setCrtEnabled(prev => !prev); audioFeedback.playClick(); }}
              onMouseEnter={() => audioFeedback.playTick()}
              className={`p-2 rounded-lg border transition-all duration-300 flex items-center gap-1.5 ${
                crtEnabled
                  ? 'bg-purple-950 border-purple-500 text-vajra-cyan shadow-[0_0_10px_rgba(0,255,255,0.3)]'
                  : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-white'
              }`}
              title="Toggle Cyberdeck CRT HUD Overlay"
            >
              <Monitor className="w-4 h-4" />
              <span className="hidden xl:inline text-xs font-semibold">CONSOLE HUD</span>
            </button>

            <div className="hidden md:flex items-center space-x-2 px-3 py-1 bg-black/40 border border-white/10 rounded-full select-none">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`} />
              <span className="text-xs font-bold font-serif uppercase tracking-wider text-gray-300">
                {isConnected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
            
            {activeTab === 'visualizers' && (
              <VisualizationSelector
                currentType={visualizationType}
                onChange={handleVisualizationChange}
              />
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-1 overflow-hidden relative">
        {activeTab === 'command-center' && (
          <div className="flex-1 h-full overflow-hidden">
            <CommandCenter
              isConnected={isConnected}
              isPlaying={isPlaying}
              frequency={frequency}
              crystalStatus={crystalStatus}
              scalarStatus={scalarStatus}
              sessions={sessions}
            />
          </div>
        )}
        
        {activeTab === 'visualizers' && (
          <div className="flex-1 relative w-full h-full min-h-[500px]">
            {visualizationType === 'sacred-geometry' ? (
              <Canvas camera={{ position: [0, 0, 20], fov: 60 }} className="w-full h-full">
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1} />
                <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                <SacredGeometry audioSpectrum={audioSpectrum} isPlaying={isPlaying} frequency={frequency} />
                <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.5} />
                <Environment preset="sunset" />
              </Canvas>
            ) : visualizationType === 'radionics' ? (
              <RadionicsVisualization attunedRate={scalarStatus?.rate} isPlaying={isPlaying} />
            ) : visualizationType === 'crystal-grid' ? (
              <Canvas camera={{ position: [0, -8, 12], fov: 60 }} className="w-full h-full">
                <ambientLight intensity={0.4} />
                <pointLight position={[10, 10, 10]} intensity={1} />
                <Stars radius={150} depth={60} count={3000} factor={3} saturation={0} fade speed={0.5} />
                <CrystalGrid
                  audioSpectrum={audioSpectrum}
                  isPlaying={isPlaying}
                  frequency={frequency}
                  gridType="double-hexagon"
                  crystalType="quartz"
                  showEnergyField={true}
                  intention="May all beings be happy"
                />
                <OrbitControls enableZoom={true} enablePan={true} enableRotate={true} autoRotate={true} autoRotateSpeed={0.3} />
                <Environment preset="night" />
              </Canvas>
            ) : visualizationType === 'sacred-mandala' ? (
              <Canvas camera={{ position: [0, 0, 15], fov: 60 }} className="w-full h-full">
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} intensity={1} />
                <Stars radius={120} depth={50} count={4000} factor={3} saturation={0.1} fade speed={0.8} />
                <SacredMandala audioSpectrum={audioSpectrum} isPlaying={isPlaying} frequency={frequency} pattern="sri-yantra" chakra="heart" complexity="medium" />
                <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.4} />
                <Environment preset="sunset" />
              </Canvas>
            ) : visualizationType === 'audio-spectrum' ? (
              <div className="w-full h-full flex items-center justify-center p-8">
                <AudioSpectrum spectrum={audioSpectrum} isPlaying={isPlaying} frequency={frequency} />
              </div>
            ) : visualizationType === 'live-wave' ? (
              <div className="w-full h-full">
                <LiveWaveVisualizer />
              </div>
            ) : visualizationType === 'scalar-wave' ? (
              <div className="w-full h-full">
                <ScalarWaveVisualizer />
              </div>
            ) : visualizationType === 'trends' ? (
              <div className="w-full h-full overflow-auto p-6 bg-gray-900">
                <Dashboard />
              </div>
            ) : visualizationType === 'chakra-trend' ? (
              <div className="w-full h-full flex flex-col">
                <div className="flex-1 flex items-center justify-center">
                  <ChakraAlignmentStrip />
                </div>
              </div>
            ) : visualizationType === 'radionics-panel' ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <h2 className="text-2xl font-bold mb-4">Radionics Panel</h2>
                  <p className="text-gray-400">Select a geometric viz or wave type in the header dropdown to visualize.</p>
                </div>
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <h2 className="text-2xl font-bold mb-4">Visualization Coming Soon</h2>
                  <p className="text-gray-400">This visualization type is under development</p>
                </div>
              </div>
            )}
            
            <ChakraAlignmentStrip />
            
            {/* Floating Info Panel */}
            <div className="absolute top-4 left-4 bg-gray-900/80 backdrop-blur-md border border-white/10 rounded-xl p-4 max-w-sm shadow-2xl z-10">
              <h3 className="text-sm font-semibold mb-3 text-vajra-cyan glow-cyan">Active Session</h3>
              {Object.keys(sessions).length > 0 ? (
                <div className="space-y-2 text-sm">
                  {Object.values(sessions).slice(0, 3).map((session) => (
                    <div key={session.id} className="flex justify-between items-center p-2 bg-white/5 border border-white/5 rounded-lg">
                      <span className="truncate mr-2 text-purple-300">{session.name}</span>
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        session.status === 'running' ? 'bg-green-600 text-white pulse-glow' : 'bg-gray-600 text-gray-300'
                      }`}>
                        {session.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-purple-400 italic">No active sessions</p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'manual' && (
          <div className="flex-1 h-full overflow-hidden">
            <ManualSettingsTab
              isPlaying={isPlaying}
              frequency={frequency}
              volume={volume}
              prayerBowlMode={prayerBowlMode}
              harmonicStrength={harmonicStrength}
              modulationDepth={modulationDepth}
              duration={duration}
              updateSettings={updateSettings}
              generateAudio={handleGenerateAudio}
              playAudio={handlePlayAudio}
              stopAudio={handleStopAudio}
              audioStatus={audioStatus}
              startSession={startSession}
              attunedRate={scalarStatus?.rate}
            />
          </div>
        )}

        {activeTab === 'targets' && (
          <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 bg-gray-900/40 backdrop-blur-md rounded-xl border border-white/10 m-4 shadow-2xl">
            <div className="bg-gradient-to-r from-teal-900/40 via-blue-900/40 to-cyan-900/40 border border-white/10 rounded-xl p-6 mb-6">
              <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
                <Users className="w-7 h-7 text-teal-400 animate-pulse" />
                Broadcast Targets & Population Manager
              </h2>
              <p className="text-sm text-teal-200 mt-1">
                Define individual targets, coordinate locations, or collective groups to direct focal blessings and resonance tuning.
              </p>
            </div>
            <PopulationManager />
          </div>
        )}

        {activeTab === 'lore' && (
          <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
            <div className="bg-gradient-to-r from-purple-900/40 via-indigo-900/40 to-blue-900/40 border border-white/10 rounded-xl p-6">
              <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
                <BookOpen className="w-7 h-7 text-vajra-purple animate-pulse" />
                Lore, Wisdom & Energetic Alignment
              </h2>
              <p className="text-sm text-purple-200 mt-1">
                Explore spiritual teaching stories, program virtual crystals, attune to quantum RNG, and align subtle energy bodies.
              </p>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
                <DharmaTales />
              </div>
              
              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
                <RadionicsNarrative />
              </div>
              
              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
                <ChakraHealing />
              </div>

              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl flex flex-col justify-between">
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-vajra-cyan flex items-center gap-2">
                    <Gem className="w-5 h-5 text-cyan-400" />
                    Crystal Grid Programming
                  </h3>
                  <p className="text-xs text-gray-400">Calibrate focus crystal nodes with specific intentions, frequencies, and charging structures.</p>
                  <CrystalProgramming />
                </div>
              </div>

              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
                <RNGAttunement />
              </div>

              <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
                <h3 className="text-lg font-semibold text-vajra-purple mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-400" />
                  Sacred Slideshow & Mantras
                </h3>
                <BlessingSlideshow />
              </div>
            </div>
          </div>
        )}
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
                { icon: LayoutDashboard, label: 'Dashboard / Trends', shortcut: 'Ctrl+D', action: () => { setActiveTab('visualizers'); setVisualizationType('trends'); setQuickSearchOpen(false); } },
                { icon: Volume2, label: 'AI Command Center', shortcut: 'Ctrl+B', action: () => { setActiveTab('command-center'); setQuickSearchOpen(false); } },
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
      <footer className="bg-gray-800 border-t border-gray-700 px-4 py-2 glassmorphism mystical-border">
        <div className="max-w-full mx-auto flex justify-between items-center text-xs text-gray-400">
          <div className="text-purple-300 font-semibold">
            Vajra.Stream - Sacred Technology Platform
          </div>
          <div className="flex items-center space-x-4">
            <span>Frequency: <span className="frequency-display text-vajra-cyan font-bold">{frequency.toFixed(1)} Hz</span></span>
            <span>Volume: <span className="text-vajra-cyan glow-cyan font-bold">{Math.round(volume * 100)}%</span></span>
            <span>Mode: <span className="text-vajra-purple glow-text font-bold">{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</span></span>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className="font-semibold">{isConnected ? 'Connected' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
