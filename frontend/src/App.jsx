import React, { useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioStore } from './stores/audioStore';
import SacredGeometry from './components/3D/SacredGeometry';
import CrystalGrid from './components/3D/CrystalGrid';
import SacredMandala from './components/3D/SacredMandala';
import AudioSpectrum from './components/2D/AudioSpectrum';
import ControlPanel from './components/UI/ControlPanel';
import SessionManager from './components/UI/SessionManager';
import StatusIndicator from './components/UI/StatusIndicator';
import VisualizationSelector from './components/UI/VisualizationSelector';
import RNGAttunement from './components/UI/RNGAttunement';

function App() {
  const [visualizationType, setVisualizationType] = useState('sacred-geometry');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const { 
    audioSpectrum, 
    isConnected, 
    sessions, 
    startSession, 
    stopSession,
    connectionStatus,
    lastUpdate 
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
    audioStatus
  } = useAudioStore();

  useEffect(() => {
    // Initialize with default settings
    updateSettings({
      frequency: 136.1,  // OM frequency
      volume: 0.8,
      prayerBowlMode: true,
      harmonicStrength: 0.3,
      modulationDepth: 0.05
    });
  }, [updateSettings]);

  const handleVisualizationChange = (type) => {
    setVisualizationType(type);
  };

  const handleGenerateAudio = async () => {
    const success = await generateAudio();
    if (success) {
      console.log('Audio generated successfully');
    }
  };

  const handlePlayAudio = async () => {
    const success = await playAudio();
    if (success) {
      console.log('Audio playback started');
    }
  };

  const handleStopAudio = () => {
    stopAudio();
    console.log('Audio playback stopped');
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4 z-10">
        <div className="max-w-full mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-2xl font-bold text-vajra-cyan">Vajra.Stream</h1>
          </div>
          
          <div className="flex items-center space-x-6">
            <StatusIndicator 
              isConnected={isConnected}
              isPlaying={isPlaying}
              frequency={frequency}
              lastUpdate={lastUpdate}
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
        {/* Left Sidebar - Controls */}
        <div className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-gray-800 border-r border-gray-700 transition-all duration-300 overflow-hidden flex flex-col`}>
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <ControlPanel
              isPlaying={isPlaying}
              frequency={frequency}
              volume={volume}
              prayerBowlMode={prayerBowlMode}
              harmonicStrength={harmonicStrength}
              modulationDepth={modulationDepth}
              onSettingsChange={updateSettings}
              onGenerateAudio={handleGenerateAudio}
              onPlayAudio={handlePlayAudio}
              onStopAudio={handleStopAudio}
              audioStatus={audioStatus}
            />
            
            <SessionManager
              sessions={sessions}
              onStartSession={startSession}
              onStopSession={stopSession}
              isConnected={isConnected}
            />

            <RNGAttunement className="mt-6" />
          </div>
        </div>

        {/* Center - Visualization */}
        <div className="flex-1 relative visualization-container">
          {visualizationType === 'sacred-geometry' ? (
            <Canvas
              camera={{ position: [0, 0, 20], fov: 60 }}
              className="w-full h-full"
            >
              <ambientLight intensity={0.5} />
              <pointLight position={[10, 10, 10]} intensity={1} />
              <Stars
                radius={100}
                depth={50}
                count={5000}
                factor={4}
                saturation={0}
                fade
                speed={1}
              />
              <SacredGeometry
                audioSpectrum={audioSpectrum}
                isPlaying={isPlaying}
                frequency={frequency}
              />
              <OrbitControls
                enableZoom={true}
                enablePan={false}
                enableRotate={true}
                autoRotate={true}
                autoRotateSpeed={0.5}
              />
              <Environment preset="sunset" />
            </Canvas>
          ) : visualizationType === 'crystal-grid' ? (
            <Canvas
              camera={{ position: [0, -8, 12], fov: 60 }}
              className="w-full h-full"
            >
              <ambientLight intensity={0.4} />
              <pointLight position={[10, 10, 10]} intensity={1} />
              <Stars
                radius={150}
                depth={60}
                count={3000}
                factor={3}
                saturation={0}
                fade
                speed={0.5}
              />
              <CrystalGrid
                audioSpectrum={audioSpectrum}
                isPlaying={isPlaying}
                frequency={frequency}
                gridType="double-hexagon"
                crystalType="quartz"
                showEnergyField={true}
                intention="May all beings be happy"
              />
              <OrbitControls
                enableZoom={true}
                enablePan={true}
                enableRotate={true}
                autoRotate={true}
                autoRotateSpeed={0.3}
              />
              <Environment preset="night" />
            </Canvas>
          ) : visualizationType === 'sacred-mandala' ? (
            <Canvas
              camera={{ position: [0, 0, 15], fov: 60 }}
              className="w-full h-full"
            >
              <ambientLight intensity={0.5} />
              <pointLight position={[10, 10, 10]} intensity={1} />
              <Stars
                radius={120}
                depth={50}
                count={4000}
                factor={3}
                saturation={0.1}
                fade
                speed={0.8}
              />
              <SacredMandala
                audioSpectrum={audioSpectrum}
                isPlaying={isPlaying}
                frequency={frequency}
                pattern="sri-yantra"
                chakra="heart"
                complexity="medium"
              />
              <OrbitControls
                enableZoom={true}
                enablePan={false}
                enableRotate={true}
                autoRotate={true}
                autoRotateSpeed={0.4}
              />
              <Environment preset="sunset" />
            </Canvas>
          ) : visualizationType === 'audio-spectrum' ? (
            <div className="w-full h-full flex items-center justify-center p-8">
              <AudioSpectrum
                spectrum={audioSpectrum}
                isPlaying={isPlaying}
                frequency={frequency}
              />
            </div>
          ) : visualizationType === 'planetary-system' ? (
            <Canvas
              camera={{ position: [0, 0, 30], fov: 60 }}
              className="w-full h-full"
            >
              <ambientLight intensity={0.3} />
              <pointLight position={[10, 10, 10]} intensity={2} />
              <Stars radius={200} depth={100} count={10000} factor={4} saturation={0.2} fade />
              {/* Planetary system component - coming soon */}
              <OrbitControls enableZoom={true} enablePan={false} enableRotate={true} />
            </Canvas>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <div className="text-center">
                <h2 className="text-2xl font-bold mb-4">Visualization Coming Soon</h2>
                <p className="text-gray-400">This visualization type is under development</p>
              </div>
            </div>
          )}
          
          {/* Floating Info Panel */}
          <div className="absolute top-4 left-4 bg-gray-800 bg-opacity-90 p-4 rounded-lg max-w-sm">
            <h3 className="text-sm font-semibold mb-2 text-vajra-cyan">Active Session</h3>
            {Object.keys(sessions).length > 0 ? (
              <div className="space-y-2 text-sm">
                {Object.values(sessions).slice(0, 3).map((session) => (
                  <div key={session.id} className="flex justify-between items-center">
                    <span className="truncate mr-2">{session.name}</span>
                    <span className={`px-2 py-1 text-xs rounded ${
                      session.status === 'running' 
                        ? 'bg-green-600 text-white' 
                        : 'bg-gray-600 text-gray-300'
                    }`}>
                      {session.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No active sessions</p>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 p-4">
        <div className="max-w-full mx-auto flex justify-between items-center text-sm text-gray-400">
          <div>
            © 2024 Vajra.Stream - Sacred Technology Platform
          </div>
          <div className="flex items-center space-x-4">
            <span>Frequency: <span className="frequency-display">{frequency.toFixed(1)} Hz</span></span>
            <span>Volume: <span className="text-vajra-cyan">{Math.round(volume * 100)}%</span></span>
            <span>Mode: <span className="text-vajra-purple">{prayerBowlMode ? 'Prayer Bowl' : 'Sine Wave'}</span></span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;