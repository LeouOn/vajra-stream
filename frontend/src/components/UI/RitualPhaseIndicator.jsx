/**
 * RitualPhaseIndicator — animated 4-phase ritual progression bar.
 *
 * Displays the current ritual phase (PREPARATION → INVOCATION →
 * BROADCAST → DEDICATION) with animated transitions, phase timers,
 * blessing count, and carrier frequency. Reads state from the
 * WebSocket scalar status and active sessions.
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import {
  Sparkles, Zap, Radio, Heart, Activity, Clock, Waves
} from 'lucide-react';

const PHASES = [
  { key: 'preparation', label: 'Preparation', icon: Sparkles, color: 'text-purple-400', bg: 'bg-purple-500', desc: 'Gathering intention & aligning energies' },
  { key: 'invocation', label: 'Invocation', icon: Zap, color: 'text-cyan-400', bg: 'bg-cyan-500', desc: 'Calling forth the sacred frequencies' },
  { key: 'broadcast', label: 'Broadcast', icon: Radio, color: 'text-emerald-400', bg: 'bg-emerald-500', desc: 'Transmitting scalar waves & blessings' },
  { key: 'dedication', label: 'Dedication', icon: Heart, color: 'text-amber-400', bg: 'bg-amber-500', desc: 'Sealing merit & dedicating to all beings' },
];

export default function RitualPhaseIndicator({ sessions, scalarStatus, frequency }) {
  const [phaseIndex, setPhaseIndex] = useState(-1);
  const [blessingCount, setBlessingCount] = useState(0);

  // Derive active phase from sessions
  useEffect(() => {
    const activeSessions = Object.values(sessions || {});
    const running = activeSessions.filter(s => s.status === 'running');
    
    if (running.length > 0 && scalarStatus?.active) {
      // Cycle through phases every ~15s for visual effect
      // In production, this would be driven by actual ritual phase data
      const idx = Math.floor(Date.now() / 15000) % 4;
      setPhaseIndex(idx);
      setBlessingCount(prev => prev + (idx === 2 ? 1 : 0)); // Count broadcasts
    } else {
      setPhaseIndex(-1);
    }
  }, [sessions, scalarStatus]);

  if (phaseIndex < 0) return null;

  const runningSessions = Object.values(sessions || {}).filter(s => s.status === 'running');

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900/70 via-purple-950/30 to-indigo-950/30 border border-purple-500/15 shadow-lg">
      {/* Ambient glow */}
      <div className="absolute top-0 right-0 w-40 h-40 bg-purple-500/5 rounded-full blur-2xl" />

      <div className="relative p-4 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-purple-900/40 border border-purple-500/20 flex items-center justify-center">
              <Activity className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <h3 className="text-xs font-bold text-purple-300 uppercase tracking-wider">
              Ritual in Progress
            </h3>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-slate-500 font-mono">
            {frequency && (
              <span className="flex items-center gap-1">
                <Waves className="w-3 h-3 text-cyan-500/70" />
                {frequency.toFixed(1)} Hz
              </span>
            )}
            <span className="flex items-center gap-1">
              <Heart className="w-3 h-3 text-pink-500/70" />
              {blessingCount} blessings
            </span>
          </div>
        </div>

        {/* Phase Indicators */}
        <div className="grid grid-cols-4 gap-1.5">
          {PHASES.map((phase, i) => {
            const isActive = i === phaseIndex;
            const isCompleted = i < phaseIndex;
            const Icon = phase.icon;

            return (
              <div
                key={phase.key}
                className={`relative flex flex-col items-center gap-1.5 p-2.5 rounded-lg transition-all duration-500 ${
                  isActive
                    ? 'bg-purple-900/30 border border-purple-500/30 scale-105'
                    : isCompleted
                    ? 'bg-emerald-900/10 border border-emerald-500/10'
                    : 'bg-slate-800/30 border border-slate-700/20'
                }`}
              >
                {/* Phase dot with connecting line */}
                <div className="relative">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-500 ${
                    isActive
                      ? `${phase.bg} shadow-[0_0_12px_rgba(168,85,247,0.5)]`
                      : isCompleted
                      ? 'bg-emerald-600'
                      : 'bg-slate-700'
                  }`}>
                    <Icon className={`w-4 h-4 ${isActive || isCompleted ? 'text-white' : 'text-slate-500'}`} />
                  </div>
                  {isActive && (
                    <div className="absolute inset-0 rounded-full animate-ping bg-purple-500/30" />
                  )}
                </div>

                {/* Label */}
                <span className={`text-[9px] font-bold uppercase tracking-wider text-center transition-colors ${
                  isActive ? phase.color : isCompleted ? 'text-emerald-400' : 'text-slate-600'
                }`}>
                  {phase.label}
                </span>

                {/* Description (active only) */}
                {isActive && (
                  <span className="text-[8px] text-slate-400 text-center leading-tight hidden sm:block">
                    {phase.desc}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Progress bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 via-cyan-500 to-emerald-400 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${((phaseIndex + 1) / 4) * 100}%` }}
            />
          </div>
          <span className="text-[9px] text-slate-600 font-mono">
            {phaseIndex + 1}/4
          </span>
        </div>

        {/* Running Session Names */}
        {runningSessions.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {runningSessions.slice(0, 2).map(s => (
              <span key={s.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-950/30 border border-purple-500/15 text-[9px] text-purple-300 font-mono truncate max-w-[180px]">
                <span className="w-1 h-1 rounded-full bg-purple-400 animate-pulse" />
                {s.name || s.id?.slice(0, 12)}
              </span>
            ))}
            {runningSessions.length > 2 && (
              <span className="text-[9px] text-slate-600">+{runningSessions.length - 2} more</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
