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
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import {
  Sparkles, Play, ChevronRight, User, Zap, Shield, Heart,
  Moon, Sun, Star, RefreshCw, Award, Swords, Eye, Brain, Footprints,
  RotateCcw
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import { message, Tooltip } from 'antd';

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
  name?: string;
  description?: string;
  blessing_theme?: string;
  blessings_count: number;
  blessings?: string[];
  stat_changes?: Partial<Record<StatKey, number>>;
  frequency_before?: number;
  frequency_after?: number;
  completed_at?: string;
}

// Mirrors STAGE_CONFIG entries in core/character_journey.py. Surfaced through
// the journey status API so the frontend can render dharmic commentary
// (significance, duration_hint, blessing_theme, etc.) without duplication.
interface StageMetadata {
  stage: string;
  name: string;
  description: string;
  significance: string;
  frequency_shift: number;
  blessing_theme: string;
  duration_hint: string;
  stat_growth: Partial<Record<StatKey, number>>;
}

interface JourneyStatus {
  active: boolean;
  character_name?: string;
  stage_index?: number;
  current_stage?: StageKey | string;
  is_complete?: boolean;
  character?: CharacterSheet;
  stage_results?: StageResult[];
  stages_metadata?: StageMetadata[];
  stat_meanings?: Partial<Record<StatKey, string>>;
}

const STAGE_NAMES: Record<StageKey, string> = {
  initiation: 'The Awakening',
  training: 'The Forge',
  working: 'The Great Work',
  overcoming: 'The Shadow Trial',
  utopia: 'The Golden Age',
  multiverse: 'The Infinite Return',
};
const STAGE_DESCRIPTIONS: Record<StageKey, string> = {
  initiation: 'The character awakens to their calling. First contact with the sacred.',
  training: 'Rigorous training. The character hones their gifts through discipline.',
  working: 'The character applies their power. Real quests, real consequences.',
  overcoming: 'The darkest hour. The character faces their greatest fear or enemy.',
  utopia: 'Victory achieved. The character basks in the light of accomplishment.',
  multiverse: 'The character transcends form. Their story echoes across all timelines.',
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
  // WebSocket slow-data broadcast replaces HTTP polling for journey status.
  const { journeyStatus, isConnected } = useWebSocketStable();
  const [journey, setJourney] = useState<JourneyStatus | null>(null);
  const [advancing, setAdvancing] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [hasInitialFetch, setHasInitialFetch] = useState(false);

  // Sync from WS (primary source of truth for journey status).
  useEffect(() => {
    const fromWs = journeyStatus as JourneyStatus | null;
    if (!fromWs) return; // No WS data yet — keep current/fallback.
    setJourney(fromWs.active ? fromWs : null);
  }, [journeyStatus]);

  // HTTP recovery fetch — runs once on mount + whenever the WS reconnects
  // after being disconnected. This fixes the post-restart stale "6/6 complete"
  // bug where the old polling was removed in commit a329ada.
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/operator/journey/status`);
      if (res.ok) {
        const data: JourneyStatus = await res.json();
        setJourney((prev) => {
          // Prefer WS data if it's fresher (stage_results populated)
          if (prev && prev.stage_results && prev.stage_results.length > 0 && !data.stage_results) {
            return prev;
          }
          return data.active ? data : null;
        });
      }
    } catch {
      /* swallow — WS will provide data on reconnect */
    } finally {
      setHasInitialFetch(true);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Refetch on WS reconnect — closes the post-restart stale window
  // (was 10-40s after a329ada removed the 5s poll).
  useEffect(() => {
    if (isConnected) {
      fetchStatus();
    }
  }, [isConnected, fetchStatus]);

  const handleAdvance = async () => {
    setAdvancing(true);
    audioFeedback.playTelemetry();
    try {
      const res = await fetch(`/api/v1/operator/journey/advance`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setJourney(prev => ({ ...prev, ...data } as JourneyStatus));
        message.success('Stage advanced');
      } else {
        message.error('Failed to advance stage');
      }
    } catch {
      message.error('Network error during advance');
    }
    setAdvancing(false);
  };

  // Start a brand-new journey — calls POST /journey/start which resets the
  // in-memory CharacterJourney to stage 0 and seeds a new character.
  const handleStartNew = async (mode: 'fresh' | 'full') => {
    setRestarting(true);
    audioFeedback.playTelemetry();
    try {
      const endpoint = mode === 'full'
        ? `/api/v1/operator/journey/run-full`
        : `/api/v1/operator/journey/start`;
      const res = await fetch(endpoint, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setJourney((data && typeof data === 'object' && (data.active || data.stage_results))
          ? (data as JourneyStatus)
          : null);
        message.success(mode === 'full' ? 'New 6-stage journey begun' : 'New journey started');
        // Immediately refetch to pull the full character data
        fetchStatus();
      } else {
        message.error('Failed to start new journey');
      }
    } catch {
      message.error('Network error starting journey');
    }
    setRestarting(false);
  };

  // Character data is embedded in the journey status payload.
  const charData: CharacterSheet = journey?.character || {};

  // Show a placeholder while waiting for first fetch OR when journey is null
  // (was: returned null and the card disappeared entirely — see line 159 in
  // pre-fix code; now renders a Start button so user can begin a journey).
  if (!journey) {
    return (
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-purple-950/40 via-slate-900/60 to-pink-950/30 border border-purple-500/20 shadow-xl">
        <div className="absolute top-0 right-0 w-48 h-48 bg-purple-500/3 rounded-full blur-3xl" />
        <div className="relative p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-purple-900/40 border border-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-purple-300">Character Journey</h3>
                <p className="text-[10px] text-slate-500 font-mono">
                  {hasInitialFetch ? 'No active journey' : 'Loading...'}
                </p>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-center justify-center gap-3 py-6 text-center">
            <Sparkles className="w-8 h-8 text-purple-400/40" />
            <div>
              <p className="text-sm font-medium text-purple-300">
                {hasInitialFetch ? 'No active journey' : 'Connecting to backend...'}
              </p>
              <p className="text-[10px] text-slate-500 mt-1 max-w-xs">
                {hasInitialFetch
                  ? 'Begin the 6-stage character arc. Each stage generates unique blessings and attunements.'
                  : 'Wait a moment while the system loads.'}
              </p>
            </div>
            {hasInitialFetch && (
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => handleStartNew('fresh')}
                  disabled={restarting}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all duration-200"
                  style={{
                    backgroundColor: 'rgba(168, 85, 247, 0.2)',
                    border: '1px solid rgba(168, 85, 247, 0.4)',
                    color: '#c084fc',
                  }}
                >
                  {restarting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                  {restarting ? 'Starting...' : 'Start Journey'}
                </button>
                <button
                  onClick={() => handleStartNew('full')}
                  disabled={restarting}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold transition-all duration-200"
                  style={{
                    backgroundColor: 'rgba(236, 72, 153, 0.2)',
                    border: '1px solid rgba(236, 72, 153, 0.4)',
                    color: '#f9a8d4',
                  }}
                >
                  {restarting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <RotateCcw className="w-3 h-3" />}
                  {restarting ? 'Starting...' : 'Run Full 6-Stage'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  const stageIdx = journey.stage_index || 0;
  const currentStage = (journey.current_stage || 'initiation') as StageKey;
  const stageName = STAGE_NAMES[currentStage] || currentStage;
  const color = STAGE_COLORS[currentStage] || '#a855f7';
  const StageIcon = STAGE_ICONS[currentStage] || Star;
  const isComplete = journey.is_complete || stageIdx >= 6;
  // Clamp progress to [0, 100] — stageIdx can exceed 6 after completion.
  const progress = Math.min(100, Math.round((Math.min(stageIdx, 6) / 6) * 100));

  // Dharmic commentary lookup — surface STAGE_CONFIG entries (significance,
  // duration_hint, blessing_theme, etc.) from the API for the current and
  // next stages. Both fall back to undefined when the backend hasn't yet
  // supplied the new metadata, which lets the contemplative UI gracefully
  // degrade to the existing dashboard-style descriptions.
  const stagesMeta = journey.stages_metadata;
  const currentStageMeta = !isComplete && stagesMeta
    ? stagesMeta[Math.min(stageIdx, stagesMeta.length - 1)]
    : undefined;
  const nextStageMeta = !isComplete && stagesMeta && stageIdx + 1 < stagesMeta.length
    ? stagesMeta[stageIdx + 1]
    : undefined;

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
            {isComplete && (
              <button
                onClick={() => handleStartNew('fresh')}
                disabled={restarting}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full border border-pink-500/30 bg-pink-950/20 text-[9px] text-pink-300 font-mono font-bold uppercase hover:bg-pink-950/30 hover:border-pink-500/50 transition-colors"
                title="Begin a brand new journey from stage 1"
              >
                {restarting ? <RefreshCw className="w-2.5 h-2.5 animate-spin" /> : <RotateCcw className="w-2.5 h-2.5" />}
                New
              </button>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full border border-slate-700/50 bg-slate-800/40 text-[10px] text-slate-300 hover:text-purple-300 hover:border-purple-500/40 hover:bg-slate-800/60 transition-colors"
              title={expanded ? 'Collapse details' : 'Expand details'}
            >
              {expanded ? 'Collapse' : 'Details'}
              <ChevronRight className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} />
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
              <h4 className="text-base font-bold text-white">
                  {charData.name || (isComplete ? 'Ascended Being' : 'Generating...')}
                </h4>
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
                  // Dharmic meaning for this stat from the journey API. Falls
                  // back to undefined on older payloads — the bar + value
                  // render exactly as before in that case. The `as StatKey`
                  // assertion re-asserts the literal-union type after the
                  // upstream Object.entries cast widens `key` to `any`.
                  const meaning = journey.stat_meanings?.[key as StatKey];
                  // Shared stat row: label/value header, the progress bar, and
                  // an italic dharmic subtitle (only when a meaning exists).
                  const statContent = (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="flex items-center gap-1 text-[9px] text-slate-500 font-mono uppercase">
                          <Icon className={`w-2.5 h-2.5 ${meta.color}`} />
                          {meta.label}
                        </span>
                        <span className={`text-[9px] font-bold font-mono ${meta.color}`}>{val}/10</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${meta.bg} transition-[width] duration-700 ease-out`}
                          style={{ width: `${Math.min(100, val * 10)}%` }}
                        />
                      </div>
                      {meaning && (
                        <p className="text-[9px] text-slate-500 italic leading-snug">
                          {meaning}
                        </p>
                      )}
                    </div>
                  );
                  // Wrap with antd Tooltip only when a meaning exists so we
                  // don't surface empty tooltips on legacy payloads.
                  return meaning ? (
                    <Tooltip
                      key={key}
                      title={meaning}
                      placement="top"
                      mouseEnterDelay={0.3}
                    >
                      {statContent}
                    </Tooltip>
                  ) : (
                    <div key={key}>{statContent}</div>
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
                <span className="text-sm font-bold text-white">
                  {isComplete ? 'Journey Complete' : `Stage ${Math.min(stageIdx + 1, 6)}`}
                </span>
                {!isComplete && (
                  <span className="text-xs font-medium" style={{ color }}>{stageName}</span>
                )}
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
              {/* Stage description */}
              <div className="text-[10px] text-slate-500 leading-relaxed mt-1">
                {isComplete
                  ? 'All 6 stages complete. The character has transcended.'
                  : (journey.stage_results?.[journey.stage_results.length - 1]?.description
                    || STAGE_DESCRIPTIONS[currentStage])}
              </div>
              {/* Stage significance — contemplative dharma commentary from the
                  journey API. Rendered as a sacred aside below the dashboard-
                  style description so the UI feels like scripture, not a log. */}
              {currentStageMeta?.significance && (
                <p
                  className="font-serif italic text-[11px] text-slate-300/90 leading-relaxed mt-2 pl-3 border-l-2 tracking-wide"
                  style={{ borderLeftColor: color }}
                >
                  {currentStageMeta.significance}
                </p>
              )}
              {/* What's Next preview — a single contemplative line pointing
                  toward the next stage (icon + name + 1-line description), or
                  the closing mantra when the journey is complete. */}
              {isComplete ? (
                <p className="font-serif italic text-[10px] text-slate-500 mt-2 leading-relaxed">
                  Journey complete. The circle begins again.
                </p>
              ) : nextStageMeta ? (
                <div className="flex items-center gap-1.5 mt-2 text-[10px] flex-wrap min-w-0">
                  <span className="text-[8px] uppercase tracking-widest text-slate-600 font-mono flex-shrink-0">
                    Next
                  </span>
                  {(() => {
                    const nextKey = nextStageMeta.stage as StageKey;
                    const NextIcon = STAGE_ICONS[nextKey] || Sparkles;
                    const nextColor = STAGE_COLORS[nextKey] || '#a855f7';
                    return (
                      <>
                        <NextIcon
                          className="w-3 h-3 flex-shrink-0"
                          style={{ color: nextColor }}
                        />
                        <span className="font-medium text-slate-300 flex-shrink-0">
                          {nextStageMeta.name}
                        </span>
                        <span className="text-slate-700 flex-shrink-0">·</span>
                        <span className="italic font-serif text-slate-500 truncate">
                          {nextStageMeta.description}
                        </span>
                      </>
                    );
                  })()}
                </div>
              ) : null}
            </div>
            {!isComplete && (
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
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              {(Object.entries(STAGE_NAMES) as [StageKey, string][]).map(([key, name], i) => {
                // Off-by-one fix: a stage is complete only when stageIdx > i
                // (was `i <= stageIdx` which lit 7 dots when stageIdx=6).
                const dotComplete = i < stageIdx || (i === stageIdx && isComplete);
                const isCurrent = i === stageIdx && !isComplete;
                return (
                  <div
                    key={key}
                    className="flex-1 group relative"
                    title={name}
                  >
                    <div
                      className={`w-full h-1.5 rounded-full transition-[opacity,background-color] duration-300 ${
                        dotComplete ? 'opacity-100' : isCurrent ? 'opacity-70' : 'opacity-25'
                      } ${isCurrent ? 'animate-pulse' : ''}`}
                      style={{ backgroundColor: (dotComplete || isCurrent) ? STAGE_COLORS[key] : '#374151' }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-1.5">
              {(Object.entries(STAGE_NAMES) as [StageKey, string][]).map(([key, name], i) => {
                const dotComplete = i < stageIdx || (i === stageIdx && isComplete);
                const isCurrent = i === stageIdx && !isComplete;
                const shortName = name.replace(/^The\s+/, ''); // "Awakening", "Forge", etc.
                return (
                  <div
                    key={`label-${key}`}
                    className={`flex-1 text-center text-[8px] font-mono uppercase tracking-wider truncate ${
                      dotComplete ? 'text-slate-400' : isCurrent ? 'text-purple-300 font-bold' : 'text-slate-600'
                    }`}
                    title={name}
                  >
                    {shortName.slice(0, 4)}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Stage Results History */}
        {journey.stage_results && journey.stage_results.length > 0 && (
          <div className="border-t border-white/5 pt-3 space-y-2">
            <span className="text-[9px] text-slate-600 font-mono uppercase tracking-wider">Stage Log</span>
            {journey.stage_results.slice(-3).reverse().map((r, i) => {
              const sColor = STAGE_COLORS[r.stage as StageKey] || '#6b7280';
              const sName = r.name || STAGE_NAMES[r.stage as StageKey] || r.stage;
              const timestamp = r.completed_at
                ? new Date(r.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '';
              const freqShift = r.frequency_before != null
                && r.frequency_after != null
                && r.frequency_before !== r.frequency_after;
              // Group all stat changes + frequency shift into a single "delta pill"
              // so the line reads as: [stage name] [stat+freq pill] [blessings]
              // instead of everything running together in one flex row.
              const hasDeltas = (r.stat_changes && Object.keys(r.stat_changes).length > 0) || freqShift;
              return (
                <div key={i} className="space-y-1">
                  <div className="flex items-center gap-2 text-[10px] flex-wrap">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: sColor }} />
                    <span className="text-slate-300 font-medium">{sName}</span>
                    {hasDeltas && (
                      <>
                        <span className="text-slate-600">·</span>
                        <span className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-slate-900/50 border border-slate-700/30">
                          {r.stat_changes && Object.entries(r.stat_changes).map(([stat, val]) => {
                            const meta = STAT_META[stat as StatKey];
                            if (!meta || !val) return null;
                            return (
                              <span
                                key={stat}
                                className={`text-[9px] font-mono ${meta.color}`}
                              >
                                +{val} {meta.label}
                              </span>
                            );
                          })}
                          {freqShift && (
                            <span className="text-[9px] font-mono text-amber-400 border-l border-slate-700/50 pl-1.5">
                              {r.frequency_before}→{r.frequency_after} Hz
                            </span>
                          )}
                        </span>
                      </>
                    )}
                    <span className="text-slate-500 ml-auto font-mono">
                      {r.blessings_count} blessings{timestamp ? ` · ${timestamp}` : ''}
                    </span>
                  </div>
                  {/* Blessing narrative text — filter out error messages and render as a
                      contemplative blockquote in the stage's sacred color. */}
                  {r.blessings && r.blessings.length > 0 && (() => {
                    const cleanBlessing = r.blessings.find(b =>
                      b && !b.includes('generation failed') && !b.includes('Error code:')
                    );
                    return cleanBlessing ? (
                      <blockquote
                        className="font-serif italic text-[11px] text-slate-300/90 leading-loose pl-4 pr-2 py-1 border-l-2 my-1 tracking-wide"
                        style={{ borderLeftColor: sColor }}
                      >
                        {cleanBlessing}
                      </blockquote>
                    ) : null;
                  })()}
                </div>
              );
            })}
          </div>
        )}

        {/* Total Blessings */}
        {journey.stage_results && journey.stage_results.length > 0 && (() => {
          const total = journey.stage_results.reduce((sum, r) => sum + (r.blessings_count || 0), 0);
          return (
            <div className="flex items-center justify-center gap-2 py-1.5 rounded-lg bg-purple-950/20 border border-purple-500/10">
              <Heart className="w-3 h-3 text-pink-400" />
              <span
                className="text-[10px] font-mono font-bold"
                style={total > 0 ? { color: '#fbbf24' } : { color: '#d8b4fe' }}
              >
                {total} total blessings generated{total > 0 ? ' ✨' : ''}
              </span>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
