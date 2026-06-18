import React, { useState, useEffect, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import { useWebSocketStable as useWebSocket } from './hooks/useWebSocketStable';
import { useAudioStore } from './stores/audioStore';
import { DEFAULT_LAT, DEFAULT_LNG } from './lib/geo';

// Ant Design
import { ConfigProvider, theme, Result } from 'antd';

import SacredGeometry from './components/3D/SacredGeometry';
import TTSSettingsPanel from './components/UI/TTSSettingsPanel';
import CrystalGrid from './components/3D/CrystalGrid';
import SacredMandala from './components/3D/SacredMandala';
import RadionicsVisualization from './components/3D/RadionicsVisualization';
import Astrocartography from './components/3D/Astrocartography';
import AudioSpectrum from './components/2D/AudioSpectrum';
import LiveWaveVisualizer from './components/2D/LiveWaveVisualizer';
import ScalarWaveVisualizer from './components/2D/ScalarWaveVisualizer';
import CrystalGridControls from './components/UI/CrystalGridControls';
import MandalaControls from './components/UI/MandalaControls';
import RadionicsGlobe from './components/3D/RadionicsGlobe';
import FrequencyWaterfall from './components/2D/FrequencyWaterfall';
import RothkoGenerator from './components/2D/RothkoGenerator';
import ChakraBodyMap from './components/2D/ChakraBodyMap';

import MainLayout from './components/Layout/MainLayout';
import CommandCenter from './components/UI/CommandCenter';
import BuddhasPage from './routes/Buddhas';
import ProviderSettings from './components/Settings/ProviderSettings';
import OperationsPanel from './components/UI/OperationsPanel';
import AstrologyPanel from './components/UI/AstrologyPanel';
import BroadcastPanel from './components/UI/BroadcastPanel';
import GrimoirePanel from './components/UI/GrimoirePanel';
import OutlookDashboard from './components/UI/OutlookDashboard';
import Dashboard from './components/UI/Dashboard';
import ChakraAlignmentStrip from './components/UI/ChakraAlignmentStrip';
import ErrorBoundary from './components/UI/ErrorBoundary';
import { audioFeedback } from './utils/audioFeedback';
import { COLORS } from './lib/colors';
import { antdTheme } from './theme/antdTheme';
import { DEFAULT_ROUTE } from './lib/routes';

function AppContent() {
  const [visualizationType, setVisualizationType] = useState('sacred-geometry');
  const [mopsData, setMopsData] = useState(null);
  // Settings for the viz control panels (lifted state so the viz
  // components and the panels stay in sync via the parent).
  const [crystalGridSettings, setCrystalGridSettings] = useState({
    gridType: 'double-hexagon',
    crystalType: 'quartz',
    showEnergyField: true,
    intention: 'May all beings be happy',
  });
  const [mandalaSettings, setMandalaSettings] = useState({
    pattern: 'sri-yantra',
    chakra: 'heart',
    complexity: 'medium',
  });
  const location = useLocation();
  const activeTab = location.pathname.split('/')[1] || DEFAULT_ROUTE;
  
  useEffect(() => {
    const fetchMops = async () => {
      try {
        const res = await fetch('/api/v1/mops/current');
        if (res.ok) {
          const data = await res.json();
          setMopsData(data.mops);
        }
      } catch (e) {
        // Ignore connectivity warnings
      }
    };
    fetchMops();
    const interval = setInterval(fetchMops, 2000);
    return () => clearInterval(interval);
  }, []);
  
  const { 
    audioSpectrum, 
    isConnected, 
    sessions, 
    startSession, 
    stopSession,
    connectionStatus,
    crystalStatus,
    scalarStatus,
    buddhaStatus,
    sakaDawa
  } = useWebSocket();
  
  const {
    isPlaying,
    frequency,
    volume,
    prayerBowlMode,
    harmonicStrength,
    modulationDepth,
    updateSettings,
    generateAudio,
    playAudio,
    stopAudio,
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

  const handleVisualizationChange = (type) => {
    setVisualizationType(type);
  };

  return (
    <MainLayout
      isConnected={isConnected}
      isPlaying={isPlaying}
      frequency={frequency}
      volume={volume}
      prayerBowlMode={prayerBowlMode}
      generateAudio={generateAudio}
      playAudio={playAudio}
      stopAudio={stopAudio}
      mopsData={mopsData}
      visualizationType={visualizationType}
      handleVisualizationChange={handleVisualizationChange}
    >
      <Routes>
        <Route path="/" element={<Navigate to={`/${DEFAULT_ROUTE}`} replace />} />
        
        <Route path="/command-center" element={
          <div className="flex-1 h-full overflow-hidden">
            <CommandCenter
              isConnected={isConnected}
              isPlaying={isPlaying}
              frequency={frequency}
              crystalStatus={crystalStatus}
              scalarStatus={scalarStatus}
              sessions={sessions}
              buddhaStatus={buddhaStatus}
              sakaDawa={sakaDawa}
            />
          </div>
        } />
        
        <Route path="/buddhas" element={
          <div className="flex-1 h-full overflow-y-auto">
            <BuddhasPage />
          </div>
        } />
        
        <Route path="/settings" element={
          <div className="flex-1 h-full overflow-y-auto">
            <ProviderSettings />
          </div>
        } />
        
        <Route path="/operations" element={
          <div className="flex-1 h-full overflow-hidden">
            <OperationsPanel />
          </div>
        } />
        
        <Route path="/astrology" element={
          <div className="flex-1 h-full overflow-hidden">
            <AstrologyPanel />
          </div>
        } />
        
        <Route path="/broadcast" element={
          <div className="flex-1 h-full overflow-hidden">
            <BroadcastPanel />
          </div>
        } />
        
        <Route path="/outlook" element={
          <div className="flex-1 h-full overflow-hidden">
            <OutlookDashboard />
          </div>
        } />
        
        <Route path="/grimoire" element={
          <div className="flex-1 h-full overflow-hidden">
            <GrimoirePanel />
          </div>
        } />

        <Route path="/tts" element={
          <div className="flex-1 h-full overflow-y-auto p-6">
            <TTSSettingsPanel />
          </div>
        } />
        
        <Route path="/meditation" element={
          <div className="fixed inset-0 z-50 bg-black">
            <RothkoGenerator
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              palette="compassion"
              transitionSpeed={30}
              fullscreen
            />
            <button
              onClick={() => window.history.back()}
              className="absolute top-4 right-4 z-50 bg-white/10 hover:bg-white/20 text-white/70 hover:text-white px-4 py-2 rounded-lg text-sm backdrop-blur-sm transition-colors"
            >
              Exit Meditation
            </button>
          </div>
        } />

        <Route path="/visualizers" element={
          <div className="flex-1 relative w-full h-full min-h-[500px]">
            {visualizationType === 'sacred-geometry' ? (
              <Suspense fallback={<div className="w-full h-full flex items-center justify-center bg-gray-900/50"><div className="text-purple-400 animate-pulse text-sm">Loading Sacred Geometry...</div></div>}>
                <Canvas key="sacred-geometry" camera={{ position: [0, 0, 20], fov: 60 }} className="w-full h-full">
                  <ambientLight intensity={0.5} />
                  <pointLight position={[10, 10, 10]} intensity={1} />
                  <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                  <SacredGeometry
                    audioSpectrum={audioSpectrum}
                    isPlaying={isPlaying}
                    frequency={frequency}
                    pattern="flower-of-life"
                    colorTheme="cyan-gold"
                    particleCount={200}
                  />
                  <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.5} />
                  <Environment preset="sunset" />
                </Canvas>
              </Suspense>
            ) : visualizationType === 'radionics' ? (
              <RadionicsVisualization attunedRate={scalarStatus?.rate} isPlaying={isPlaying} />
            ) : visualizationType === 'crystal-grid' ? (
              <>
                <Suspense fallback={<div className="w-full h-full flex items-center justify-center bg-gray-900/50"><div className="text-cyan-400 animate-pulse text-sm">Loading Crystal Grid...</div></div>}>
                  <Canvas key="crystal-grid" camera={{ position: [0, -8, 12], fov: 60 }} className="w-full h-full">
                    <ambientLight intensity={0.4} />
                    <pointLight position={[10, 10, 10]} intensity={1} />
                    <Stars radius={150} depth={60} count={3000} factor={3} saturation={0.5} />
                    <CrystalGrid
                      audioSpectrum={audioSpectrum}
                      isPlaying={isPlaying}
                      frequency={frequency}
                      gridType={crystalGridSettings.gridType}
                      crystalType={crystalGridSettings.crystalType}
                      showEnergyField={crystalGridSettings.showEnergyField}
                      intention={crystalGridSettings.intention}
                    />
                    <OrbitControls enableZoom={true} enablePan={true} enableRotate={true} autoRotate={true} autoRotateSpeed={0.3} />
                    <Environment preset="night" />
                  </Canvas>
                </Suspense>
                <div className="absolute top-4 right-4 w-80 max-h-[calc(100vh-100px)] overflow-y-auto bg-gray-900/85 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl z-10 pointer-events-auto">
                  <CrystalGridControls
                    gridType={crystalGridSettings.gridType}
                    crystalType={crystalGridSettings.crystalType}
                    showEnergyField={crystalGridSettings.showEnergyField}
                    intention={crystalGridSettings.intention}
                    onSettingsChange={setCrystalGridSettings}
                  />
                </div>
              </>
            ) : visualizationType === 'sacred-mandala' ? (
              <Suspense fallback={<div className="w-full h-full flex items-center justify-center bg-gray-900/50"><div className="text-amber-400 animate-pulse text-sm">Loading Sacred Mandala...</div></div>}>
                <Canvas key="sacred-mandala" camera={{ position: [0, 0, 15], fov: 60 }} className="w-full h-full">
                  <ambientLight intensity={0.5} />
                  <pointLight position={[10, 10, 10]} intensity={1} />
                  <Stars radius={120} depth={50} count={4000} factor={3} saturation={0.1} fade speed={0.8} />
                  <SacredMandala
                    audioSpectrum={audioSpectrum}
                    isPlaying={isPlaying}
                    frequency={frequency}
                    pattern={mandalaSettings.pattern}
                    chakra={mandalaSettings.chakra}
                    complexity={mandalaSettings.complexity}
                  />
                  <MandalaControls
                    pattern={mandalaSettings.pattern}
                    chakra={mandalaSettings.chakra}
                    complexity={mandalaSettings.complexity}
                    onSettingsChange={setMandalaSettings}
                  />
                  <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.4} />
                  <Environment preset="sunset" />
                </Canvas>
              </Suspense>
            ) : visualizationType === 'astrocartography' ? (
              <Suspense fallback={<div className="w-full h-full flex items-center justify-center bg-gray-900/50"><div className="text-cyan-400 animate-pulse text-sm">Loading Astrocartography...</div></div>}>
                <Canvas key="astrocartography" camera={{ position: [0, 0, 15], fov: 60 }} className="w-full h-full">
                  <ambientLight intensity={0.3} />
                  <pointLight position={[20, 20, 20]} intensity={1.5} />
                  <pointLight position={[-20, -20, -20]} intensity={0.5} color="#4488ff" />
                  <Stars radius={200} depth={100} count={8000} factor={5} saturation={0.3} fade speed={0.5} />
                  <Astrocartography
                    audioSpectrum={audioSpectrum}
                    isPlaying={isPlaying}
                    frequency={frequency}
                    birthLocation={{ lat: DEFAULT_LAT, lon: DEFAULT_LNG, name: 'San Francisco' }}
                    showPowerSpots={true}
                    autoRotate={true}
                  />
                  <OrbitControls
                    enableZoom={true}
                    enablePan={true}
                    enableRotate={true}
                    autoRotate={false}
                    minDistance={8}
                    maxDistance={30}
                  />
                  <Environment preset="night" />
                </Canvas>
              </Suspense>
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
            ) : visualizationType === 'rothko' ? (
              <div className="w-full h-full">
                <RothkoGenerator
                  audioSpectrum={audioSpectrum}
                  isPlaying={isPlaying}
                  palette="compassion"
                  transitionSpeed={30}
                />
              </div>
            ) : visualizationType === 'chakra-body' ? (
              <div className="w-full h-full flex items-center justify-center bg-gray-950 p-8">
                <ChakraBodyMap
                  audioSpectrum={audioSpectrum}
                  isPlaying={isPlaying}
                  height={450}
                  onSelectChakra={(chakra) => {
                    updateSettings({ frequency: chakra.frequency });
                  }}
                />
              </div>
            ) : visualizationType === 'chakra-trend' ? (
              <div className="w-full h-full flex flex-col bg-gray-950">
                <div className="flex-1 flex items-center justify-center">
                  <ChakraBodyMap
                    audioSpectrum={audioSpectrum}
                    isPlaying={isPlaying}
                    height={350}
                  />
                </div>
                <ChakraAlignmentStrip
                  activeChakras={Object.values(sessions || {}).filter(s => s.status === 'running').flatMap(s => s.config?.chakras_enabled || [])}
                  onSelectChakra={(chakra) => {
                    updateSettings({ frequency: chakra.frequency });
                  }}
                />
              </div>
            ) : visualizationType === 'globe' ? (
              <div className="w-full h-full">
                <RadionicsGlobe disasters={[]} broadcastTargets={Object.values(sessions || {}).filter(s => s.status === 'running').map(s => ({ name: s.name, location: s.intention }))} />
              </div>
            ) : visualizationType === 'waterfall' ? (
              <div className="w-full h-full p-4">
                <FrequencyWaterfall frequency={frequency} isPlaying={isPlaying} />
              </div>
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <h2 className="text-2xl font-bold mb-4">Radionics Panel</h2>
                  <p className="text-gray-400">Select a geometric viz or wave type in the header dropdown to visualize.</p>
                </div>
              </div>
            )}
            
            <ChakraAlignmentStrip />
            
            {/* Floating Info Panel */}
            <div className="absolute top-4 left-4 bg-gray-900/80 backdrop-blur-md border border-white/10 rounded-xl p-4 max-w-sm shadow-2xl z-10 pointer-events-none">
              <h3 className="text-sm font-semibold mb-3 text-vajra-cyan glow-cyan">Active Session</h3>
              {Object.keys(sessions || {}).length > 0 ? (
                <div className="space-y-2 text-sm">
                  {Object.values(sessions).slice(0, 3).map((session) => (
                    <div key={session.id} className="flex justify-between items-center p-2 bg-white/5 border border-white/5 rounded-lg pointer-events-auto">
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
        } />

        <Route path="*" element={
          <div className="flex-1 flex items-center justify-center bg-gray-900">
            <Result
              status="404"
              title="404"
              subTitle="The path you requested does not match any known route."
              extra={
                <a
                  href={`/${DEFAULT_ROUTE}`}
                  className="inline-block px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
                >
                  Return to Command Center
                </a>
              }
            />
          </div>
        } />
      </Routes>
    </MainLayout>
  );
}

function App() {
  return (
    <ConfigProvider
      theme={{
        ...antdTheme,
        algorithm: theme.darkAlgorithm,
        token: {
          ...antdTheme.token,
          colorPrimary: COLORS.primary, // vajra-purple (--primary in globals.css)
          colorInfo: COLORS.secondary, // vajra-cyan (--secondary in globals.css)
        },
      }}
    >
      <ErrorBoundary fallbackTitle="Application failed to render">
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </ErrorBoundary>
    </ConfigProvider>
  );
}

export default App;
