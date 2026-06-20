/**
 * JourneyCard — character journey arc visualization with full character data.
 *
 * Polls /api/v1/operator/journey/status every 5s. When a journey is active,
 * renders the complete character profile (name, Chinese name, element, role,
 * stats with bars, sigil seed, frequency shifts) alongside the 6-stage
 * progression tracker with per-stage blessing counts.
 *
 * Expanded from ~85 lines to full character sheet display.
 *
 * @component
 */
import React, { useState, useEffect } from 'react';
import {
  Sparkles, Play, ChevronRight, User, Zap, Shield, Heart,
  Moon, Sun, Star, RefreshCw, Award, Swords, Eye, Brain, Footprints
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';

type StageKey = 'initiation' | 'training' | 'working' | 'overcoming' | 'utopia' | 'multiverse';
type StatKey = 'vitality' | 'wisdom' | 'courage' | 'empathy' | 'focus' | 'resonance';

interface CharacterSheet {
  name?: string;
  chinese_name?: string;
  element?: string;
  role?: string;
  role_icon?: string;
  frequency?: number;
  stats?: Partial<Record<StatKey, number>>;
  origin?: string;
  quest?: string;
  sigil_seed?: string;
  role_virtue?: string;
  backstory?: string;
}

interface StageResult {
  stage: StageKey | string;
  blessings_count: number;
  completed_at?: string;
}

interface JourneyStatus {
  active: boolean;
  character_name?: string;
  stage_index?: number;
  current_stage?: StageKey | string;
  is_complete?: boolean;
  character?: CharacterSheet;
  stage_results?: StageResult[];
}

const STAGE_NAMES: Record<StageKey, string> = {
  initiation: 'The Awakening',
  training: 'The Forge',
  working: 'The Great Work',
  overcoming: 'The Shadow Trial',
  utopia: 'The Golden Age',
  multiverse: 'The Infinite Return',
};
const STAGE_COLORS: Record<StageKey, string> = {
  initiation: '#a855f7', training: '#3b82f6', working: '#22c55e',
  overcoming: '#ef4444', utopia: '#fbbf24', multiverse: '#ec4899',
};
const STAGE_ICONS: Record<StageKey, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  initiation: Star, training: Swords, working: Shield,
  overcoming: Moon, utopia: Sun, multiverse: Sparkles,
};

const STAT_META: Record<StatKey, { icon: React.ComponentType<{ className?: string }>; label: string; color: string; bg: string }> = {
  vitality:   { icon: Heart, label: 'Vitality', color: 'text-red-400', bg: 'bg-red-500' },
  wisdom:     { icon: Eye, label: 'Wisdom', color: 'text-blue-400', bg: 'bg-blue-500' },
  courage:    { icon: Swords, label: 'Courage', color: 'text-orange-400', bg: 'bg-orange-500' },
  empathy:    { icon: Heart, label: 'Empathy', color: 'text-pink-400', bg: 'bg-pink-500' },
  focus:      { icon: Brain, label: 'Focus', color: 'text-teal-400', bg: 'bg-teal-500' },
  resonance:  { icon: Zap, label: 'Resonance', color: 'text-purple-400', bg: 'bg-purple-500' },
};

const ELEMENT_EMOJIS: Record<string, string> = { Fire: '🔥', Water: '💧', Earth: '🌍', Air: '💨', Wood: '🌿', Metal: '⚙️' };
const ELEMENT_COLORS: Record<string, string> = {
  Fire: 'border-red-500/30 text-red-400 bg-red-950/20',
  Water: 'border-blue-500/30 text-blue-400 bg-blue-950/20',
  Earth: 'border-green-500/30 text-green-400 bg-green-950/20',
  Air: 'border-purple-500/30 text-purple-400 bg-purple-950/20',
  Wood: 'border-emerald-500/30 text-emerald-400 bg-emerald-950/20',
  Metal: 'border-slate-400/30 text-slate-300 bg-slate-800/40',
};

export default function JourneyCard() {
  const [journey, setJourney] = useState<JourneyStatus | null>(null);
  const [character, setCharacter] = useState<CharacterSheet | null>(null);
  const [advancing, setAdvancing] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`/api/v1/operator/journey/status`);
        if (res.ok) {
          const data: JourneyStatus = await res.json();
          if (data.active) {
            setJourney(data);
            // Fetch full character if not already loaded
            if (!character || character.name !== data.character_name) {
              fetchCharacter();
            }
          } else {
            setJourney(null);
            setCharacter(null);
          }
        }
      } catch {}
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchCharacter = async () => {
    try {
      // The journey status includes character data inline
      const res = await fetch(`/api/v1/operator/journey/generate-character`, { method: 'POST' });
    } catch {}
    // Character data comes from the journey status poll
  };

  const handleAdvance = async () => {
    setAdvancing(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/operator/journey/advance`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setJourney(prev => ({ ...prev, ...data } as JourneyStatus));
      }
    } catch {}
    setAdvancing(false);
  };

  // Character data is embedded in stage_results or we derive from the journey
  // For now, use what the journey endpoint gives us
  const charData: CharacterSheet = character || journey?.character || {};

  if (!journey) return null;

  const stageIdx = journey.stage_index || 0;
  const currentStage = (journey.current_stage || 'initiation') as StageKey;
  const stageName = STAGE_NAMES[currentStage] || currentStage;
  const color = STAGE_COLORS[currentStage] || '#a855f7';
  const StageIcon = STAGE_ICONS[currentStage] || Star;
  const progress = Math.round((stageIdx / 6) * 100);

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-950/40 via-slate-900/60 to-pink-950/30 border border-purple-500/20 shadow-xl">
      <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/3 rounded-full blur-3xl" />

      <div className="relative p-5 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-900/40 border border-purple-500/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-purple-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-purple-300">Character Journey</h3>
              <p className="text-[10px] text-slate-500 font-mono">
                {stageIdx}/6 stages · {journey.stage_results?.length || 0} completed
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-[9px] text-purple-400 font-mono font-bold uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
              ACTIVE
            </span>
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-[10px] text-slate-500 hover:text-purple-400 transition-colors"
            >
              {expanded ? 'Collapse' : 'Details'}
            </button>
          </div>
        </div>

        {/* Character Identity */}
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-[0_0_15px_rgba(168,85,247,0.3)]">
            <User className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-base font-bold text-white">{charData.name || 'Unknown Hero'}</h4>
              {charData.chinese_name && (
                <span className="text-xs text-slate-400 font-mono">{charData.chinese_name}</span>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {charData.element && (
                <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium border ${ELEMENT_COLORS[charData.element] || 'border-slate-500/30 text-slate-400 bg-slate-800/20'}`}>
                  {ELEMENT_EMOJIS[charData.element] || ''} {charData.element}
                </span>
              )}
              {charData.role && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-medium border border-cyan-500/20 bg-cyan-950/20 text-cyan-300">
                  {charData.role_icon || ''} {charData.role}
                </span>
              )}
              {charData.frequency && (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono border border-amber-500/20 bg-amber-950/20 text-amber-300">
                  <Zap className="w-2.5 h-2.5" /> {charData.frequency} Hz
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="space-y-4 border-t border-white/5 pt-4">
            {/* Stat Bars */}
            {charData.stats && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                {(Object.entries(STAT_META) as [StatKey, typeof STAT_META[StatKey]]).map(([key, meta]) => {
                  const val = charData.stats?.[key] || 0;
                  const Icon = meta.icon;
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-[9px] text-slate-500 font-mono uppercase">
                          <Icon className={`w-2.5 h-2.5 ${meta.color}`} />
                          {meta.label}
                        </span>
                        <span className={`text-[9px] font-bold font-mono ${meta.color}`}>{val}/10</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${meta.bg} transition-all duration-700`}
                          style={{ width: `${val * 10}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Character Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {charData.origin && (
                <div className="flex items-start gap-1.5">
                  <Footprints className="w-3 h-3 text-purple-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-400">
                    <span className="text-slate-600">Origin: </span>
                    {charData.origin}
                  </span>
                </div>
              )}
              {charData.quest && (
                <div className="flex items-start gap-1.5">
                  <Award className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-400">
                    <span className="text-slate-600">Quest: </span>
                    {charData.quest}
                  </span>
                </div>
              )}
              {charData.sigil_seed && (
                <div className="flex items-start gap-1.5">
                  <Sparkles className="w-3 h-3 text-cyan-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-400">
                    <span className="text-slate-600">Sigil Seed: </span>
                    <span className="font-mono text-cyan-300">{charData.sigil_seed}</span>
                  </span>
                </div>
              )}
              {charData.role_virtue && (
                <div className="flex items-start gap-1.5">
                  <Shield className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-400">
                    <span className="text-slate-600">Virtue: </span>
                    {charData.role_virtue}
                  </span>
                </div>
              )}
            </div>

            {/* Backstory */}
            {charData.backstory && (
              <div className="bg-purple-950/10 rounded-lg border border-purple-500/10 p-3">
                <p className="text-[10px] text-slate-400 italic leading-relaxed line-clamp-3">
                  {charData.backstory}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Stage Progression */}
        <div className="space-y-3">
          {/* Current Stage */}
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: `${color}20`, border: `1px solid ${color}40` }}>
              <StageIcon className="w-5 h-5" style={{ color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white">Stage {stageIdx + 1}</span>
                <span className="text-xs font-medium" style={{ color }}>{stageName}</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 mt-1.5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${progress}%`,
                    background: `linear-gradient(90deg, ${color}80, ${color})`,
                  }}
                />
              </div>
            </div>
            {!journey.is_complete && (
              <button
                onClick={handleAdvance}
                disabled={advancing}
                className="flex-shrink-0 flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200"
                style={{
                  backgroundColor: `${color}30`,
                  border: `1px solid ${color}40`,
                  color,
                }}
              >
                {advancing ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Play className="w-3 h-3" />
                )}
                {advancing ? '...' : 'Advance'}
              </button>
            )}
          </div>

          {/* Stage Dots */}
          <div className="flex items-center gap-1.5">
            {(Object.entries(STAGE_NAMES) as [StageKey, string][]).map(([key, name], i) => {
              const isComplete = i <= stageIdx;
              return (
                <div
                  key={key}
                  className="flex-1 group relative"
                  title={`${name}${isComplete ? ' ✓' : ''}`}
                >
                  <div
                    className={`w-full h-1.5 rounded-full transition-all duration-300 ${
                      isComplete ? 'opacity-100' : 'opacity-30'
                    }`}
                    style={{ backgroundColor: isComplete ? STAGE_COLORS[key] : '#374151' }}
                  />
                </div>
              );
            })}
          </div>
        </div>

        {/* Stage Results History */}
        {journey.stage_results && journey.stage_results.length > 0 && (
          <div className="border-t border-white/5 pt-3 space-y-1.5">
            <span className="text-[9px] text-slate-600 font-mono uppercase tracking-wider">Stage Log</span>
            {journey.stage_results.slice(-3).reverse().map((r, i) => {
              const sColor = STAGE_COLORS[r.stage as StageKey] || '#6b7280';
              const sName = STAGE_NAMES[r.stage as StageKey] || r.stage;
              return (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: sColor }} />
                  <span className="text-slate-400">{sName}</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-purple-300 font-mono">{r.blessings_count} blessings</span>
                  {r.completed_at && (
                    <>
                      <span className="text-slate-600">·</span>
                      <span className="text-slate-600 text-[9px]">
                        {new Date(r.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Total Blessings */}
        {journey.stage_results && journey.stage_results.length > 0 && (
          <div className="flex items-center justify-center gap-2 py-1.5 rounded-lg bg-purple-950/20 border border-purple-500/10">
            <Heart className="w-3 h-3 text-pink-400" />
            <span className="text-[10px] text-purple-300 font-mono font-bold">
              {journey.stage_results.reduce((sum, r) => sum + (r.blessings_count || 0), 0)} total blessings generated
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
