import React, { useState, useEffect } from 'react';
import { Sparkles, Play, ChevronRight, User } from 'lucide-react';
import { API_BASE } from '../../utils/api';

const STAGE_NAMES = {
  initiation: 'The Awakening',
  training: 'The Forge',
  working: 'The Great Work',
  overcoming: 'The Shadow Trial',
  utopia: 'The Golden Age',
  multiverse: 'The Infinite Return',
};
const STAGE_COLORS = {
  initiation: '#a855f7', training: '#3b82f6', working: '#22c55e',
  overcoming: '#ef4444', utopia: '#fbbf24', multiverse: '#ec4899',
};

export default function JourneyCard() {
  const [journey, setJourney] = useState(null);
  const [advancing, setAdvancing] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/operator/journey/status`);
        if (res.ok) {
          const data = await res.json();
          if (data.active) setJourney(data);
          else setJourney(null);
        }
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAdvance = async () => {
    setAdvancing(true);
    try {
      const res = await fetch(`${API_BASE}/operator/journey/advance`, { method: 'POST' });
      if (res.ok) setJourney(await res.json());
    } catch {}
    setAdvancing(false);
  };

  if (!journey) return null;

  const stageIdx = journey.stage_index || 0;
  const currentStage = journey.current_stage || 'initiation';
  const stageName = STAGE_NAMES[currentStage] || currentStage;
  const color = STAGE_COLORS[currentStage] || '#a855f7';
  const progress = Math.round((stageIdx / 6) * 100);

  return (
    <div className="bg-gradient-to-r from-purple-900/20 to-pink-900/20 rounded-lg p-4 border border-purple-500/20 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-bold text-purple-300">Character Journey</span>
          <span className="text-[10px] px-1.5 py-0.5 bg-purple-950 rounded text-purple-400 font-mono">ACTIVE</span>
        </div>
        <span className="text-xs text-gray-500">{stageIdx}/6 stages</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-purple-800 flex items-center justify-center">
          <User className="w-4 h-4 text-purple-300" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-white font-bold">Stage {stageIdx+1}: {stageName}</span>
            <ChevronRight className="w-3 h-3 text-gray-600" />
          </div>
          <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1.5">
            <div className="h-1.5 rounded-full transition-all" style={{ width: `${progress}%`, backgroundColor: color }} />
          </div>
          <div className="flex gap-2 mt-1">
            {Object.entries(STAGE_NAMES).slice(0,6).map(([key, name], i) => (
              <div key={key} className="w-2.5 h-2.5 rounded-full transition-colors" style={{
                backgroundColor: i <= stageIdx ? STAGE_COLORS[key] : '#374151'
              }} title={name} />
            ))}
          </div>
        </div>
        {!journey.is_complete && (
          <button onClick={handleAdvance} disabled={advancing}
            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded text-xs font-bold flex items-center gap-1">
            <Play className="w-3 h-3" /> {advancing ? '...' : 'Advance'}
          </button>
        )}
      </div>

      {journey.stage_results?.length > 0 && (
        <div className="text-[10px] text-gray-500 border-t border-white/5 pt-2">
          {journey.stage_results.slice(-2).map((r, i) => (
            <span key={i} className="mr-3">{STAGE_NAMES[r.stage]}: {r.blessings_count} blessings</span>
          ))}
        </div>
      )}
    </div>
  );
}
