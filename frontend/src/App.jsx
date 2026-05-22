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
import StatusIndicator from './components/UI/StatusIndicator';
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
import Dashboard from './components/UI/Dashboard';
import { ToastContainer } from './components/UI/Toast';
import { SidebarSection } from './components/UI/SidebarSection';
import ChakraAlignmentStrip from './components/UI/ChakraAlignmentStrip';
import {
  Volume2, Clock, Heart, Sparkles, Zap, Users, Radio, BookOpen,
  Sliders, Gem, LayoutDashboard, Search, Command
} from 'lucide-react';

const VIEWS = {
  visualization: 'visualization',
  dashboard: 'dashboard'
};

function App() {
  const [visualizationType, setVisualizationType] = useState('sacred-geometry');
  const [currentView, setCurrentView] = useState(VIEWS.visualization);
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);
  
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  
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
            toggleSidebar();
            break;
          case 'd':
            e.preventDefault();
            setCurrentView(prev => prev === VIEWS.dashboard ? VIEWS.visualization : VIEWS.dashboard);
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  const handleVisualizationChange = (type) => {
    setVisualizationType(type);
    setCurrentView(VIEWS.visualization);
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

  const runningSessionCount = Object.values(sessions).filter(s => s.status === 'running').length;

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Toast Notifications */}
      <ToastContainer />
      
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-3 z-20 glassmorphism mystical-border">
        <div className="max-w-full mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-lg hover:bg-purple-700/30 transition-all duration-300 glassmorphism"
              title="Toggle sidebar (Ctrl+B)"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-bold text-vajra-cyan glow-cyan">Vajra.Stream</h1>
            
            {/* View Toggle */}
            <div className="flex items-center bg-gray-900/50 rounded-lg p-0.5 ml-2">
              <button
                onClick={() => setCurrentView(VIEWS.visualization)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  currentView === VIEWS.visualization
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Visualization
              </button>
              <button
                onClick={() => setCurrentView(VIEWS.dashboard)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  currentView === VIEWS.dashboard
                    ? 'bg-purple-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <LayoutDashboard className="w-3 h-3 inline mr-1" />
                Dashboard
              </button>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <StatusIndicator
              isConnected={isConnected}
              isPlaying={isPlaying}
              frequency={frequency}
              lastUpdate={lastUpdate}
              crystalStatus={crystalStatus}
              scalarStatus={scalarStatus}
            />
            
            <VisualizationSelector
              currentType={visualizationType}
              onChange={handleVisualizationChange}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-gray-800/95 border-r border-gray-700 transition-all duration-300 overflow-hidden flex flex-col`}>
          <div className="flex-1 overflow-y-auto p-3 space-y-0.5">
            {/* Audio & Broadcasting */}
            <div className="text-xs text-gray-500 uppercase tracking-wider px-3 py-1 mt-1">Audio & Broadcasting</div>
            
            <SidebarSection title="Audio Control" icon={Volume2} defaultOpen={true}>
              <ControlPanel
                isPlaying={isPlaying}
                frequency={frequency}
                volume={volume}
                prayerBowlMode={prayerBowlMode}
                harmonicStrength={harmonicStrength}
                modulationDepth={modulationDepth}
                duration={duration}
                onSettingsChange={updateSettings}
                onGenerateAudio={handleGenerateAudio}
                onPlayAudio={handlePlayAudio}
                onStopAudio={handleStopAudio}
                audioStatus={audioStatus}
                onStartSession={startSession}
                attunedRate={scalarStatus?.rate}
              />
            </SidebarSection>

            <SidebarSection title="Sessions" icon={Clock} defaultOpen={false} badge={runningSessionCount || null}>
              <SessionManager
                sessions={sessions}
                onStartSession={startSession}
                onStopSession={stopSession}
                isConnected={isConnected}
              />
            </SidebarSection>

            {/* Radionics & Healing */}
            <div className="text-xs text-gray-500 uppercase tracking-wider px-3 py-1 mt-3">Radionics & Healing</div>
            
            <SidebarSection title="Rate Tuner" icon={Sliders} defaultOpen={false}>
              <RateTuner />
            </SidebarSection>

            <SidebarSection title="RNG Attunement" icon={Radio} defaultOpen={false}>
              <RNGAttunement />
            </SidebarSection>

            <SidebarSection title="Chakra Healing" icon={Heart} defaultOpen={false}>
              <ChakraHealing />
            </SidebarSection>

            <SidebarSection title="Healing Narratives" icon={Sparkles} defaultOpen={false}>
              <RadionicsNarrative />
            </SidebarSection>

            {/* Sacred Content */}
            <div className="text-xs text-gray-500 uppercase tracking-wider px-3 py-1 mt-3">Sacred Content</div>
            
            <SidebarSection title="Crystal Work" icon={Gem} defaultOpen={false}>
              <CrystalProgramming />
            </SidebarSection>

            <SidebarSection title="Dharma Tales" icon={BookOpen} defaultOpen={false}>
              <DharmaTales />
            </SidebarSection>

            <SidebarSection title="Blessing Slideshow" icon={Sparkles} defaultOpen={false}>
              <BlessingSlideshow />
            </SidebarSection>

            {/* Advanced */}
            <div className="text-xs text-gray-500 uppercase tracking-wider px-3 py-1 mt-3">Advanced</div>
            
            <SidebarSection title="Populations" icon={Users} defaultOpen={false}>
              <PopulationManager />
            </SidebarSection>

            <SidebarSection title="Automation" icon={Zap} defaultOpen={false}>
              <AutomationControl />
            </SidebarSection>
          </div>
          
          {/* Sidebar Footer */}
          <div className="p-3 border-t border-gray-700 bg-gray-900/50">
            <div className="text-xs text-gray-500 text-center">
              <kbd className="px-1 py-0.5 bg-gray-700 rounded text-xs">Ctrl+K</kbd> Search
              <span className="mx-2">|</span>
              <kbd className="px-1 py-0.5 bg-gray-700 rounded text-xs">Ctrl+B</kbd> Toggle
            </div>
          </div>
        </div>

        {/* Center Content */}
        <div className="flex-1 relative overflow-hidden">
          {currentView === VIEWS.dashboard ? (
            <div className="h-full overflow-y-auto p-6">
              <Dashboard />
            </div>
          ) : (
            <>
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
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold mb-4">Visualization Coming Soon</h2>
                    <p className="text-gray-400">This visualization type is under development</p>
                  </div>
                </div>
              )}
              
              {currentView === VIEWS.visualization && <ChakraAlignmentStrip />}
              
              {/* Floating Info Panel */}
              <div className="absolute top-4 left-4 mystical-card max-w-sm">
                <h3 className="text-sm font-semibold mb-3 text-vajra-cyan glow-cyan">Active Session</h3>
                {Object.keys(sessions).length > 0 ? (
                  <div className="space-y-2 text-sm">
                    {Object.values(sessions).slice(0, 3).map((session) => (
                      <div key={session.id} className="flex justify-between items-center p-2 glassmorphism rounded-lg">
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
                  <p className="text-sm text-purple-400">No active sessions</p>
                )}
              </div>
            </>
          )}
        </div>
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
                { icon: LayoutDashboard, label: 'Dashboard', shortcut: 'Ctrl+D', action: () => { setCurrentView(VIEWS.dashboard); setQuickSearchOpen(false); } },
                { icon: Volume2, label: 'Toggle Sidebar', shortcut: 'Ctrl+B', action: () => { toggleSidebar(); setQuickSearchOpen(false); } },
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
          <div className="text-purple-300">
            Vajra.Stream - Sacred Technology Platform
          </div>
          <div className="flex items-center space-x-4">
            <span>Frequency: <span className="frequency-display">{frequency.toFixed(1)} Hz</span></span>
            <span>Volume: <span className="text-vajra-cyan glow-cyan">{Math.round(volume * 100)}%</span></span>
            <span>Mode: <span className="text-vajra-purple glow-text">{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</span></span>
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span>{isConnected ? 'Connected' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
