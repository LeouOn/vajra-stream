import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Gem, Sparkles, CheckCircle, Play, Square } from 'lucide-react';
import { useCrystalStore } from '../../stores/crystalStore';
import { useUIStore } from '../../stores/uiStore';

const PROGRAMMING_STEPS = [
  { title: 'Set Intention', description: 'Focus your mind and set a clear intention for this crystal' },
  { title: 'Cleanse', description: 'Visualize white light purifying the crystal' },
  { title: 'Connect', description: 'Hold the crystal in your mind and feel its energy' },
  { title: 'Imprint', description: 'Send your intention into the crystal with focused will' },
  { title: 'Seal', description: 'Affirm the programming with a blessing or mantra' },
  { title: 'Activate', description: 'The crystal is now programmed and active' }
];

const MEDITATION_PROMPTS = {
  root: 'Ground yourself. Feel your connection to the earth.',
  sacral: 'Open to flow and creativity. Feel the water element.',
  solar_plexus: 'Ignite your inner fire. Feel your personal power.',
  heart: 'Open your heart. Radiate love and compassion.',
  throat: 'Speak your truth. Feel the vibration of sound.',
  third_eye: 'See with inner vision. Open to wisdom.',
  crown: 'Connect to the infinite. Feel universal consciousness.'
};

const CrystalProgramming = ({ className = '' }) => {
  const {
    crystalLibrary,
    gridConfig,
    programming,
    attunement,
    meditation,
    startProgramming,
    advanceProgrammingStep,
    completeProgramming,
    startAttunement,
    advanceAttunementStep,
    stopAttunement,
    startMeditation,
    stopMeditation,
    updateMeditation,
    setIntention
  } = useCrystalStore();
  
  const { addToast } = useUIStore();
  
  const [selectedCrystal, setSelectedCrystal] = useState(null);
  const [intentionInput, setIntentionInput] = useState('');
  const [activeTab, setActiveTab] = useState('program');
  const timerRef = useRef(null);
  const elapsedRef = useRef(0);
  
  const stopMeditationTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);
  
  useEffect(() => {
    if (meditation.isActive) {
      elapsedRef.current = meditation.elapsed;
      timerRef.current = setInterval(() => {
        elapsedRef.current += 1;
        updateMeditation(elapsedRef.current);
        if (elapsedRef.current >= meditation.duration) {
          stopMeditationTimer();
          stopMeditation();
          addToast({
            type: 'success',
            title: 'Meditation Complete',
            message: `Completed ${Math.floor(meditation.duration / 60)} minute crystal meditation`,
            duration: 5000
          });
        }
      }, 1000);
    } else {
      stopMeditationTimer();
    }
    
    return () => stopMeditationTimer();
  }, [meditation.isActive, meditation.duration]);
  
  const handleStartProgramming = useCallback(() => {
    if (!intentionInput.trim()) {
      addToast({ type: 'warning', title: 'Intention Required', message: 'Please enter an intention first', duration: 3000 });
      return;
    }
    startProgramming(selectedCrystal?.id || 0, intentionInput);
    addToast({ type: 'info', title: 'Programming Started', message: 'Follow the steps to program your crystal', duration: 3000 });
  }, [intentionInput, selectedCrystal, startProgramming, addToast]);
  
  const handleAdvanceStep = useCallback(() => {
    if (programming.step >= PROGRAMMING_STEPS.length - 2) {
      completeProgramming();
      addToast({ type: 'success', title: 'Crystal Programmed!', message: `Programmed with intention: "${programming.intention}"`, duration: 5000 });
    } else {
      advanceProgrammingStep();
    }
  }, [programming, completeProgramming, advanceProgrammingStep, addToast]);
  
  const handleStartAttunement = useCallback(() => {
    startAttunement();
    addToast({ type: 'info', title: 'Attunement Started', message: 'Working through each chakra...', duration: 3000 });
  }, [startAttunement, addToast]);
  
  const handleStartMeditation = useCallback((duration = 300) => {
    startMeditation(duration);
    addToast({ type: 'info', title: 'Meditation Started', message: `${Math.floor(duration / 60)} minute crystal meditation`, duration: 3000 });
  }, [startMeditation, addToast]);
  
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <h3 className="text-lg font-semibold text-vajra-purple flex items-center gap-2">
        <Gem className="w-5 h-5" />
        Crystal Work
      </h3>
      
      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {[
          { id: 'program', label: 'Program', icon: Sparkles },
          { id: 'attune', label: 'Attune', icon: Gem },
          { id: 'meditate', label: 'Meditate', icon: Play }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-purple-300 border-b-2 border-purple-500'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
          {tab.icon && <tab.icon className="w-3 h-3" />}
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Program Tab */}
      {activeTab === 'program' && (
        <div className="space-y-4">
          {/* Crystal Selection */}
          <div>
            <label className="block text-xs text-gray-400 mb-2">Select Crystal Type</label>
            <div className="grid grid-cols-2 gap-2">
              {crystalLibrary.slice(0, 6).map(crystal => (
                <button
                  key={crystal.id}
                  onClick={() => setSelectedCrystal(crystal)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-all ${
                    selectedCrystal?.id === crystal.id
                      ? 'bg-purple-900/50 border border-purple-500'
                      : 'bg-gray-700/30 border border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: crystal.color }}
                  />
                  <span className="text-gray-300 truncate">{crystal.name}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Intention Input */}
          <div>
            <label className="block text-xs text-gray-400 mb-1">Programming Intention</label>
            <textarea
              value={intentionInput}
              onChange={(e) => setIntentionInput(e.target.value)}
              placeholder="Enter the intention to program into the crystal..."
              rows={3}
              className="w-full bg-gray-700/30 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none resize-none"
            />
          </div>
          
          {/* Programming Steps */}
          {!programming.isActive ? (
            <button
              onClick={handleStartProgramming}
              disabled={!intentionInput.trim()}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white py-3 px-4 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Begin Programming
            </button>
          ) : (
            <div className="space-y-3">
              {/* Progress */}
              <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                <span>Step {programming.step + 1} of {PROGRAMMING_STEPS.length}</span>
                <span>{Math.round(((programming.step + 1) / PROGRAMMING_STEPS.length) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${((programming.step + 1) / PROGRAMMING_STEPS.length) * 100}%` }}
                />
              </div>
              
              {/* Current Step */}
              <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
                <h4 className="text-sm font-semibold text-purple-300 mb-1">
                  {PROGRAMMING_STEPS[programming.step].title}
                </h4>
                <p className="text-xs text-gray-400">
                  {PROGRAMMING_STEPS[programming.step].description}
                </p>
              </div>
              
              {/* Steps list */}
              <div className="space-y-1">
                {PROGRAMMING_STEPS.map((step, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${
                      i < programming.step ? 'text-green-400' :
                      i === programming.step ? 'text-purple-300 bg-purple-900/20' :
                      'text-gray-600'
                    }`}
                  >
                    {i < programming.step ? (
                      <CheckCircle className="w-3 h-3 text-green-400" />
                    ) : (
                      <div className={`w-3 h-3 rounded-full border ${
                        i === programming.step ? 'border-purple-400' : 'border-gray-600'
                      }`} />
                    )}
                    <span>{step.title}</span>
                  </div>
                ))}
              </div>
              
              <button
                onClick={handleAdvanceStep}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg font-semibold text-sm transition-colors"
              >
                {programming.step >= PROGRAMMING_STEPS.length - 2 ? 'Complete Programming' : 'Next Step →'}
              </button>
            </div>
          )}
          
          {/* Selected crystal info */}
          {selectedCrystal && (
            <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
              <div className="flex items-center gap-2 mb-2">
                <div
                  className="w-6 h-6 rounded-full"
                  style={{ backgroundColor: selectedCrystal.color }}
                />
                <span className="text-sm font-medium text-white">{selectedCrystal.name}</span>
              </div>
              <p className="text-xs text-gray-400">{selectedCrystal.description}</p>
              <div className="flex flex-wrap gap-1 mt-2">
                {selectedCrystal.properties.map(prop => (
                  <span key={prop} className="text-xs px-2 py-0.5 bg-gray-700 rounded-full text-gray-300">
                    {prop}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Attune Tab */}
      {activeTab === 'attune' && (
        <div className="space-y-4">
          {!attunement.isActive ? (
            <>
              <p className="text-sm text-gray-400">
                Attune your crystals through each chakra, aligning their energy with your subtle body.
              </p>
              <button
                onClick={handleStartAttunement}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2"
              >
                <Gem className="w-4 h-4" />
                Begin Attunement
              </button>
            </>
          ) : (
            <div className="space-y-4">
              {/* Progress */}
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Chakra {attunement.step + 1} of {attunement.totalSteps}</span>
                <span>{Math.round(((attunement.step + 1) / attunement.totalSteps) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${((attunement.step + 1) / attunement.totalSteps) * 100}%` }}
                />
              </div>
              
              {/* Current chakra */}
              <div className="text-center py-4">
                <div className="text-2xl mb-2">
                  {['🔴', '🟠', '🟡', '💚', '🔵', '🟣', '⚪'][attunement.step]}
                </div>
                <h4 className="text-lg font-semibold text-white capitalize">
                  {attunement.currentChakra.replace('_', ' ')} Chakra
                </h4>
                <p className="text-sm text-gray-400 mt-2">
                  {MEDITATION_PROMPTS[attunement.currentChakra]}
                </p>
              </div>
              
              {/* Chakra dots */}
              <div className="flex justify-center gap-2">
                {attunement.chakras.map((chakra, i) => (
                  <div
                    key={chakra}
                    className={`w-3 h-3 rounded-full transition-all ${
                      i < attunement.step ? 'bg-green-500' :
                      i === attunement.step ? 'bg-purple-400 scale-125' :
                      'bg-gray-600'
                    }`}
                  />
                ))}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={advanceAttunementStep}
                  className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg font-semibold text-sm transition-colors"
                >
                  {attunement.step >= attunement.totalSteps - 1 ? 'Complete' : 'Next Chakra →'}
                </button>
                <button
                  onClick={stopAttunement}
                  className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                >
                  <Square className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Meditate Tab */}
      {activeTab === 'meditate' && (
        <div className="space-y-4">
          {!meditation.isActive ? (
            <>
              <p className="text-sm text-gray-400">
                Guided crystal meditation with breath synchronization.
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[300, 600, 900].map(duration => (
                  <button
                    key={duration}
                    onClick={() => handleStartMeditation(duration)}
                    className="px-3 py-3 bg-gray-700/50 hover:bg-gray-600/50 rounded-lg text-sm text-gray-300 hover:text-white transition-colors"
                  >
                    {Math.floor(duration / 60)} min
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="space-y-4">
              {/* Timer */}
              <div className="text-center py-4">
                <div className="text-4xl font-bold text-white font-mono">
                  {formatTime(meditation.duration - meditation.elapsed)}
                </div>
                <div className="text-sm text-gray-400 mt-2">
                  {meditation.breathPhase === 'inhale' ? '↑ Breathe In' :
                   meditation.breathPhase === 'hold' ? '■ Hold' :
                   '↓ Breathe Out'}
                </div>
              </div>
              
              {/* Progress */}
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all"
                  style={{ width: `${(meditation.elapsed / meditation.duration) * 100}%` }}
                />
              </div>
              
              {/* Stats */}
              <div className="flex justify-between text-xs text-gray-400">
                <span>Breaths: {meditation.breathCount}</span>
                <span>Elapsed: {formatTime(meditation.elapsed)}</span>
              </div>
              
              {/* Intention */}
              <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700 text-center">
                <p className="text-sm text-purple-300 italic">"{gridConfig.intention}"</p>
              </div>
              
              <button
                onClick={() => {
                  stopMeditationTimer();
                  stopMeditation();
                }}
                className="w-full bg-red-600 hover:bg-red-700 text-white py-3 px-4 rounded-lg font-semibold text-sm transition-colors flex items-center justify-center gap-2"
              >
                <Square className="w-4 h-4" />
                End Meditation
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CrystalProgramming;
