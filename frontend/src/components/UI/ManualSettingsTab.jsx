import React from 'react';
import ControlPanel from './ControlPanel';
import RateTuner from './RateTuner';
import AutomationControl from './AutomationControl';
import RadionicsBroadcastPanel from './RadionicsBroadcastPanel';
import { Sliders, Volume2, Cpu, Zap } from 'lucide-react';

export default function ManualSettingsTab({
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
  audioStatus,
  startSession,
  attunedRate
}) {
  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 space-y-6 scrollbar-thin scrollbar-thumb-purple-900/50 scrollbar-track-transparent">
      {/* Tab Header Banner */}
      <div className="bg-gradient-to-r from-cyan-900/40 via-purple-900/40 to-indigo-900/40 border border-white/10 rounded-xl p-6 backdrop-blur-md shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
            <Sliders className="w-7 h-7 text-vajra-cyan animate-pulse" />
            Manual Control & Tuning Board
          </h2>
          <p className="text-sm text-purple-300 mt-1">Configure frequencies, tune rates, set up automation rules, and manage hardware overrides manually.</p>
        </div>
        <div className="flex gap-2">
          <span className="px-3 py-1 bg-cyan-950/80 border border-cyan-500/30 text-cyan-400 text-xs font-bold rounded-full flex items-center gap-1.5 font-mono">
            <Volume2 className="w-3.5 h-3.5 text-cyan-400" />
            AUDIO ACTIVE: {isPlaying ? 'YES' : 'NO'}
          </span>
          <span className="px-3 py-1 bg-purple-950/80 border border-purple-500/30 text-purple-300 text-xs font-bold rounded-full flex items-center gap-1.5 font-mono">
            <Zap className="w-3.5 h-3.5 text-purple-400" />
            TUNING: {attunedRate || '0.00'}
          </span>
        </div>
      </div>

      {/* Grid Layout for settings panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        
        {/* Column 1: Audio carrier & broadcast settings */}
        <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl flex flex-col justify-between">
          <ControlPanel
            isPlaying={isPlaying}
            frequency={frequency}
            volume={volume}
            prayerBowlMode={prayerBowlMode}
            harmonicStrength={harmonicStrength}
            modulationDepth={modulationDepth}
            duration={duration}
            onSettingsChange={updateSettings}
            onGenerateAudio={generateAudio}
            onPlayAudio={playAudio}
            onStopAudio={stopAudio}
            audioStatus={audioStatus}
            onStartSession={startSession}
            attunedRate={attunedRate}
          />
        </div>

        {/* Column 2: Radionics rate tuning */}
        <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
          <RateTuner className="h-full" />
        </div>

        {/* Column 3: Automation laws & active broadcast display */}
        <div className="space-y-6">
          
          {/* Active Broadcast panel */}
          <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl overflow-hidden">
            <div className="bg-gradient-to-r from-cyan-900/20 to-purple-900/20 p-4 border-b border-white/10">
              <h3 className="text-sm font-bold text-white tracking-wide uppercase flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                Live Broadcast Stream
              </h3>
            </div>
            <RadionicsBroadcastPanel />
          </div>

          {/* Automation Control rules */}
          <div className="bg-gray-900/60 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
            <h3 className="text-sm font-bold text-white mb-4 tracking-wide uppercase flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              Round-Robin Automation
            </h3>
            <AutomationControl />
          </div>

        </div>

      </div>
    </div>
  );
}
