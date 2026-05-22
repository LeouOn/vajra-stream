import React, { useState, useEffect } from 'react';
import { Radio, Play, Pause, Square } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';

const FREQUENCIES = [
  { name: 'Schumann', hz: 7.83, color: '#22d3ee' },
  { name: 'OM', hz: 136.1, color: '#a855f7' },
  { name: 'Love', hz: 528, color: '#22c55e' },
  { name: 'Connection', hz: 639, color: '#f59e0b' },
  { name: 'Awakening', hz: 741, color: '#ef4444' },
];

const RadionicsBroadcastPanel = () => {
  const { sessions, scalarStatus, crystalStatus, stopSession } = useWebSocket();
  const { isPlaying } = useWebSocket();
  const [progress, setProgress] = useState(0);

  const activeSessions = Object.values(sessions || {}).filter(s => s.status === 'running');
  const activeSession = activeSessions[0];

  useEffect(() => {
    if (!activeSession) {
      setProgress(0);
      return;
    }
    const interval = setInterval(() => {
      const elapsed = (Date.now() / 1000) - (activeSession.start_time || 0);
      const pct = Math.min(100, (elapsed / (activeSession.duration || 3600)) * 100);
      setProgress(pct);
    }, 100);
    return () => clearInterval(interval);
  }, [activeSession]);

  const rate = scalarStatus?.rate || 42.0;
  const r1 = Math.round(((Math.sin(rate * 1.7) + 1) / 2) * 100);
  const r2 = Math.round(((Math.sin(rate * 2.3) + 1) / 2) * 100);
  const r3 = Math.round(((Math.sin(rate * 3.1) + 1) / 2) * 100);

  const showPanel = activeSession || isPlaying;

  if (!showPanel) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No active broadcast — start a session to see radionics data
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
        <span className="text-sm font-semibold text-cyan-400">Radionics Broadcast</span>
      </div>

      {/* Intention */}
      <div className="p-3 bg-purple-900/30 rounded-lg border border-purple-500/30">
        <div className="text-xs text-purple-400 mb-1">Active Intention</div>
        <div className="text-sm text-white font-medium">
          {activeSession?.config?.name || 'General Blessing'}
        </div>
        <div className="text-xs text-purple-300 mt-1 italic">
          {activeSession?.intention || 'Universal Healing'}
        </div>
      </div>

      {/* Rate Bars */}
      <div className="space-y-2">
        <div className="text-xs text-gray-400 mb-1">Rate Attunement</div>
        {[{ label: 'R1', val: r1 }, { label: 'R2', val: r2 }, { label: 'R3', val: r3 }].map(({ label, val }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-4">{label}</span>
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full transition-all duration-300"
                style={{ width: `${val}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 w-8">{val}</span>
          </div>
        ))}
      </div>

      {/* Progress */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Progress</span>
          <span>{progress.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-cyan-500 rounded-full transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Frequency Indicators */}
      <div className="flex justify-between">
        {FREQUENCIES.map(({ name, hz, color }) => (
          <div key={name} className="flex flex-col items-center gap-1">
            <div
              className="w-4 h-4 rounded-full"
              style={{
                backgroundColor: color,
                boxShadow: isPlaying ? `0 0 8px ${color}` : 'none',
                opacity: isPlaying ? 1 : 0.3,
              }}
            />
            <span className="text-[9px] text-gray-500">{hz}</span>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex gap-2">
        <button className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          <Pause className="w-4 h-4" /> Pause
        </button>
        <button
          onClick={() => activeSession && stopSession(activeSession.id)}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-900/50 hover:bg-red-800 rounded text-sm text-red-300"
        >
          <Square className="w-4 h-4" /> Stop
        </button>
      </div>
    </div>
  );
};

export default RadionicsBroadcastPanel;