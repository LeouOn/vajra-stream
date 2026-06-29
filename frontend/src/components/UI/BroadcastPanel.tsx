/**
 * Broadcast Panel — scalar wave and radionics broadcast controls.
 *
 * Provides the UI for starting, stopping, and configuring healing
 * broadcasts. Controls frequency selection, intensity, crystal grid
 * routing, and real-time broadcast status monitoring via WebSocket.
 *
 * @component
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Radio, Sliders, Play, Square, Gem, Shield, Target, Zap, Waves, Activity, Radio as RadioIcon, Sparkles, Copy, BookOpen, Flower2 } from 'lucide-react';
import { message, Select, Tag } from 'antd';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';
import { useCrystalStore } from '../../stores/crystalStore';
import type { RadionicsBroadcastResult } from '../../stores/crystalStore';
import { audioFeedback } from '../../utils/audioFeedback';
import RateDial from './RateDial';
import { MiniGlobe } from '../3D/RadionicsGlobe';
import { createLogger } from '../../utils/logger';
import {
  CHAKRA_PRESETS,
  HARMONIC_PRESETS,
  ALL_PRESETS,
  presetFrequencies,
  presetFrequencySummary,
  solfeggioName,
  type CrystalPreset,
} from '../../lib/crystalPresets';
import type { Dimensions } from '../../types/radionics';

interface Point2D {
  x: number;
  y: number;
}

interface Sigil {
  intention: string;
  reduced_letters: string;
  kamea: string;
  svg: string;
  ai_image?: string | null;
  id: string | number;
  [key: string]: unknown;
}

interface Population {
  id: string | number;
  name?: string;
  is_active?: boolean;
  [key: string]: unknown;
}

interface SessionEntry {
  id?: string;
  name?: string;
  intention?: string;
  status?: string;
  [key: string]: unknown;
}

interface SutraResult {
  status: string;
  session_id: string;
  sutra: string;
  sanskrit_name: string;
  chapter: string;
  theme: string;
  tags: string[];
  passage: string;
  passage_tts_friendly: string;
  context: string;
  frequencies: number[];
  solfeggio_names: string[];
  crystal_output: { status: string; error?: string } | null;
  tts_result: { status: string; error?: string } | null;
}

interface DharaniEntry {
  id: string;
  name: string;
  sanskrit: string;
  deity: string;
  tradition: string;
  purpose: string;
  frequency_hz: number;
  chakra: string;
  has_sanskrit: boolean;
  text_sanskrit_preview: string;
}

interface DharaniResult {
  status: string;
  session_id: string;
  dharani_id: string;
  name: string;
  sanskrit_name: string;
  deity: string;
  purpose: string;
  frequency_hz: number;
  chakra: string;
  passage: string;
  passage_tts_friendly: string;
  frequencies: number[];
  solfeggio_names: string[];
  crystal_output?: { status?: string; error?: string } | null;
  tts_result?: { status?: string; error?: string } | null;
}

interface Props {}

const BroadcastPanel: React.FC<Props> = (_props: Props) => {
  const log = createLogger('BroadcastPanel');
  const { sessions, scalarStatus, crystalStatus, stopSession, isConnected } = useWebSocketStable();
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const frequency = useAudioStore((s) => s.frequency);
  const updateSettings = useAudioStore((s) => s.updateSettings);

  // Radionics rates D1 - D5
  const [dimensions, setDimensions] = useState<Dimensions>({
    d1: 42.0, // Physical
    d2: 60.0, // Astral
    d3: 77.3, // Mental
    d4: 50.0, // Causal
    d5: 88.0, // Spiritual
  });

  // Stick Plate State
  const [isRubbing, setIsRubbing] = useState<boolean>(false);
  const [rubCoherence, setRubCoherence] = useState<number>(0);
  const [rubPosition, setRubPosition] = useState<Point2D>({ x: 0, y: 0 });
  const [resonantLocked, setResonantLocked] = useState<boolean>(false);
  const [targetLock, setTargetLock] = useState<Point2D>({ x: 120, y: 80 });
  
  // Latest sigil state
  const [latestSigil, setLatestSigil] = useState<Sigil | null>(null);
  const [sigilIntention, setSigilIntention] = useState<string>('');
  const [isForging, setIsForging] = useState<boolean>(false);
  
  // Track populations/targets
  const [populations, setPopulations] = useState<Population[]>([]);

  // Radionics broadcast state
  const broadcastCrystal = useCrystalStore((s) => s.broadcastCrystal);
  const [radIntention, setRadIntention] = useState<string>('healing');
  const [radTarget, setRadTarget] = useState<string>('all beings');
  const [isBroadcasting, setIsBroadcasting] = useState<boolean>(false);
  const [broadcastResult, setBroadcastResult] = useState<RadionicsBroadcastResult | null>(null);
  const [directFreq, setDirectFreq] = useState<string>('');
  const [presetTab, setPresetTab] = useState<'chakra' | 'harmonic' | 'custom'>('chakra');

  // Ritual broadcast state
  const [ritualType, setRitualType] = useState<string>('dedication_of_endeavors');
  const [ritualIntention, setRitualIntention] = useState<string>('');
  const [ritualTarget, setRitualTarget] = useState<string>('all mother sentient beings');
  const [isRitualGenerating, setIsRitualGenerating] = useState<boolean>(false);
  const [ritualMarkdown, setRitualMarkdown] = useState<string>('');
  const [ritualResult, setRitualResult] = useState<any>(null);

  // Sutra recitation state
  const [sutraList, setSutraList] = useState<Array<{
    id: string; sutra: string; sanskrit_name: string; chapter: string; theme: string; tags: string[];
  }>>([]);
  const [selectedSutraId, setSelectedSutraId] = useState<string>('');
  const [selectedTheme, setSelectedTheme] = useState<string>('dedication');
  const [sutraRepeatCount, setSutraRepeatCount] = useState<number>(1);
  const [isSutraReciting, setIsSutraReciting] = useState<boolean>(false);
  const [sutraResult, setSutraResult] = useState<SutraResult | null>(null);

  // Dharani recitation state
  const [dharaniList, setDharaniList] = useState<DharaniEntry[]>([]);
  const [selectedDharaniId, setSelectedDharaniId] = useState<string>('');
  const [dharaniRepeatCount, setDharaniRepeatCount] = useState<number>(1);
  const [isDharaniReciting, setIsDharaniReciting] = useState<boolean>(false);
  const [dharaniResult, setDharaniResult] = useState<DharaniResult | null>(null);

  const canvasRef = useRef<HTMLDivElement | null>(null);

  // Load target lock and populations on mount — do NOT auto-forge sigils
  useEffect(() => {
    setTargetLock({
      x: 50 + Math.random() * 200,
      y: 40 + Math.random() * 120
    });
    fetchPopulations();
  }, [fetchPopulations]);

  // WS reconnect recovery — re-fetch populations after backend restart.
  useEffect(() => {
    if (isConnected) fetchPopulations();
  }, [isConnected, fetchPopulations]);

  // Fetch available sutras on mount
  useEffect(() => {
    fetch('/api/v1/radionics/sutras')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data?.sutras) setSutraList(data.sutras); })
      .catch(() => {});
  }, []);

  // Fetch available dharanis on mount
  useEffect(() => {
    fetch('/api/v1/radionics/dharanis')
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data?.dharanis) setDharaniList(data.dharanis); })
      .catch(() => {});
  }, []);

  const forgeUserSigil = async () => {
    if (!sigilIntention.trim() || isForging) return;
    setIsForging(true);
    try {
      const res = await fetch(`/api/v1/sigils/forge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention: sigilIntention.trim(), kamea: 'saturn' })
      });
      if (res.ok) {
        const data = await res.json();
        setLatestSigil(data.sigil);
        audioFeedback.playSuccess();
      }
    } catch (e) {
      log.error("Sigil forge failed:", e);
      audioFeedback.playError();
    } finally {
      setIsForging(false);
    }
  };

  const fetchPopulations = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/populations`);
      if (res.ok) {
        const data = await res.json();
        setPopulations(data);
      }
    } catch (e) {
      log.error("Failed to fetch populations:", e);
      message.error('Could not load broadcast targets: ' + (e instanceof Error ? e.message : String(e)));
    }
  }, []);

  // ─── Preset application (shared chakra + harmonic presets) ────────────────
  const applyPreset = (dims: Dimensions) => {
    setDimensions(dims);
    audioFeedback.playTabChange();
  };

  // Custom presets saved by the user (localStorage-persisted)
  const [customPresets, setCustomPresets] = useState<CrystalPreset[]>(() => {
    try {
      const raw = localStorage.getItem('vajra.customCrystalPresets');
      return raw ? (JSON.parse(raw) as CrystalPreset[]) : [];
    } catch {
      return [];
    }
  });
  const [showSaveDialog, setShowSaveDialog] = useState<boolean>(false);
  const [saveName, setSaveName] = useState<string>('');

  const saveCurrentAsPreset = () => {
    if (!saveName.trim()) return;
    const preset: CrystalPreset = {
      id: `custom_${Date.now()}`,
      label: saveName.trim(),
      icon: '⭐',
      dims: { ...dimensions },
      description: `Custom preset — ${presetFrequencySummary({
        id: '',
        label: '',
        icon: '',
        dims: dimensions,
        description: '',
      })}`,
    };
    const next = [...customPresets, preset];
    setCustomPresets(next);
    try {
      localStorage.setItem('vajra.customCrystalPresets', JSON.stringify(next));
    } catch { /* localStorage full */ }
    setSaveName('');
    setShowSaveDialog(false);
    audioFeedback.playSuccess();
    message.success(`Saved preset "${preset.label}"`);
  };

  const deleteCustomPreset = (id: string) => {
    const next = customPresets.filter((p) => p.id !== id);
    setCustomPresets(next);
    try { localStorage.setItem('vajra.customCrystalPresets', JSON.stringify(next)); } catch {}
  };

  // Live preview: show the Solfeggio freqs the current dials will produce
  const livePreviewFrequencies = presetFrequencies({
    id: '', label: '', icon: '', dims: dimensions, description: '',
  });

  // ─── Radionics broadcast (rate_to_audio → prayer bowl → crystal grid) ────
  // The backend maps these to Solfeggio carrier frequencies via
  // core/rate_to_audio.py and plays prayer bowl audio through the crystal grid.
  const handleRadionicsBroadcast = async () => {
    setIsBroadcasting(true);
    setBroadcastResult(null);
    audioFeedback.playTelemetry();
    try {
      // If a direct frequency is specified, use it instead of dial values.
      // The backend accepts frequency_hz as an override.
      const directFreqNum = directFreq ? parseFloat(directFreq) : NaN;
      const useDirect = !isNaN(directFreqNum) && directFreqNum > 0;

      const rateValues = useDirect ? undefined : [
        Math.round(dimensions.d1),
        Math.round(dimensions.d2),
        Math.round(dimensions.d3),
        Math.round(dimensions.d4),
        Math.round(dimensions.d5),
      ];

      const result = await broadcastCrystal(
        600,        // 10 min default
        2,          // hardware level 2 (passive grid)
        radIntention,
        radTarget ? [radTarget] : ['all beings'],
        rateValues,
        0.8,        // scalar intensity
      );
      if (result) {
        setBroadcastResult(result);
        audioFeedback.playSuccess();
        message.success(`Broadcast active: ${result.frequencies?.length || 0} carrier frequencies`);
      } else {
        message.error('Broadcast failed — no response from backend');
        audioFeedback.playError();
      }
      } catch (e) {
        message.error('Broadcast error: ' + (e instanceof Error ? e.message : String(e)));
        audioFeedback.playError();
      } finally {
        setIsBroadcasting(false);
      }
    };

  // ─── Ritual broadcast (LLM-generated ritual + crystal bowl broadcast) ───
  // Generates a tradition-specific Buddhist ritual via /ritual-broadcast,
  // archives it as a sacred narrative, and starts a crystal bowl broadcast.
  const handleRitualBroadcast = async () => {
    setIsRitualGenerating(true);
    setRitualMarkdown('');
    setRitualResult(null);
    audioFeedback.playTelemetry();
    try {
      const rateValues = directFreq ? undefined : [
        Math.round(dimensions.d1), Math.round(dimensions.d2),
        Math.round(dimensions.d3), Math.round(dimensions.d4), Math.round(dimensions.d5),
      ];
      const response = await fetch('/api/v1/radionics/ritual-broadcast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          intention: ritualIntention || 'Universal compassion for all suffering beings',
          target: ritualTarget || 'all beings',
          rate_values: rateValues,
          duration_minutes: 5,
          ritual_type: ritualType,
          recite_with_tts: true,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setRitualMarkdown(data.ritual_markdown || '');
        setRitualResult(data);
        audioFeedback.playSuccess();
        message.success('Ritual generated and broadcast started');
      } else {
        message.error(`Ritual generation failed: HTTP ${response.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      message.error('Ritual error: ' + (e instanceof Error ? e.message : String(e)));
      audioFeedback.playError();
} finally {
    setIsRitualGenerating(false);
  }
};

  // ─── Sutra recitation (TTS recitation + crystal bowl accompaniment) ────
  const handleSutraRecitation = async () => {
    setIsSutraReciting(true);
    setSutraResult(null);
    audioFeedback.playTelemetry();
    try {
      const response = await fetch('/api/v1/radionics/sutra-recitation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sutra_id: selectedSutraId || null,
          theme: selectedSutraId ? null : selectedTheme,
          duration_minutes: 5,
          recite_with_tts: true,
          repeat_count: sutraRepeatCount,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        setSutraResult(data as SutraResult);
        audioFeedback.playSuccess();
        message.success(`Reciting ${data.sutra} — ${data.chapter}`);
      } else {
        message.error(`Sutra recitation failed: HTTP ${response.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      message.error('Sutra error: ' + (e instanceof Error ? e.message : String(e)));
      audioFeedback.playError();
    } finally {
      setIsSutraReciting(false);
    }
  };

  // ─── Dharani recitation (TTS recitation + crystal bowl accompaniment) ────
  const handleDharaniRecitation = async () => {
    if (!selectedDharaniId) return;
    setIsDharaniReciting(true);
    setDharaniResult(null);
    audioFeedback.playTelemetry();
    try {
      const url = `/api/v1/radionics/dharani-recitation?dharani_id=${encodeURIComponent(selectedDharaniId)}&duration_minutes=5&recite_with_tts=true&repeat_count=${dharaniRepeatCount}`;
      const response = await fetch(url, { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        setDharaniResult(data as DharaniResult);
        audioFeedback.playSuccess();
        message.success(`Reciting ${data.name}`);
      } else {
        message.error(`Dharani recitation failed: HTTP ${response.status}`);
        audioFeedback.playError();
      }
    } catch (e) {
      message.error('Dharani error: ' + (e instanceof Error ? e.message : String(e)));
      audioFeedback.playError();
    } finally {
      setIsDharaniReciting(false);
    }
  };

  // Adjust Radionics sliders
  const handleDimensionChange = (key: keyof Dimensions, val: number | string) => {
    setDimensions(prev => {
      const next = { ...prev, [key]: Number(val) };
      // Play dial adjust hum
      audioFeedback.playDialAdjust(Number(val), 0, 100);
      return next;
    });
  };

  // Drag handlers on Stick Plate (Rub Plate)
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    setIsRubbing(true);
    updateRubPosition(e);
    audioFeedback.playTick();
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isRubbing) return;
    updateRubPosition(e);
  };

  const handleMouseUp = () => {
    setIsRubbing(false);
    setRubCoherence(0);
  };

  const updateRubPosition = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setRubPosition({ x, y });

    // Calculate proximity to target lock
    const dx = x - targetLock.x;
    const dy = y - targetLock.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    // Friction increases as cursor gets close to the resonance target lock (within 40px)
    const maxDist = 80;
    let coherence = Math.max(0, 1 - dist / maxDist);
    coherence = Math.round(coherence * 100);
    setRubCoherence(coherence);

    // If extremely close (within 8px), trigger resonant lock chime
    if (dist < 8) {
      if (!resonantLocked) {
        setResonantLocked(true);
        audioFeedback.playSuccess();
        // Shift active carrier frequency to the sacred tone nearest the dimensional average
        const dimAvg = (Object.values(dimensions) as number[]).reduce((a, b) => a + b, 0) / 5;
        const sacredFreqs = [136.1, 396, 417, 528, 639, 741, 852, 963];
        const nearest = sacredFreqs.reduce((prev, curr) =>
          Math.abs(curr - dimAvg * 7) < Math.abs(prev - dimAvg * 7) ? curr : prev
        );
        updateSettings({ frequency: nearest });
      }
    } else {
      if (resonantLocked) {
        setResonantLocked(false);
      }
      // Smooth frequency shift based on distance to target
      const freqShift = (1 - dist / maxDist) * 20;
      const currentFreq = frequency;
      updateSettings({ frequency: Math.round(currentFreq + freqShift * (Math.random() > 0.5 ? 1 : -1)) });
      // Play a rubbing friction sound
      if (Math.random() < 0.3) {
        audioFeedback.playType();
      }
    }
  };

  // Calculate phase coherence based on dimensional rates
  const calculateCoherence = (): number => {
    const vals = (Object.values(dimensions) as number[]);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const variance = vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / vals.length;
    const stdDev = Math.sqrt(variance);
    // Standard coherence scale where lower std deviation means higher wave symmetry
    const coherence = Math.max(10, Math.min(100, Math.round(100 - stdDev * 1.8)));
    return coherence;
  };

  const coherence = calculateCoherence();
  const activeSessions = (Object.values(sessions || {}) as SessionEntry[]).filter(s => s.status === 'running');
  const activeSession = activeSessions[0];

  // Draw Radar Polygon coordinates
  const radarRadius = 60;
  const centerX = 80;
  const centerY = 80;
  
  const getRadarPoint = (index: number, val: number): string => {
    const angle = (index * 2 * Math.PI) / 5 - Math.PI / 2;
    const normalizedVal = val / 100;
    const x = centerX + radarRadius * normalizedVal * Math.cos(angle);
    const y = centerY + radarRadius * normalizedVal * Math.sin(angle);
    return `${x},${y}`;
  };

  const radarPoints = [
    getRadarPoint(0, dimensions.d1),
    getRadarPoint(1, dimensions.d2),
    getRadarPoint(2, dimensions.d3),
    getRadarPoint(3, dimensions.d4),
    getRadarPoint(4, dimensions.d5),
  ].join(' ');

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      
      {/* Title Header */}
      <div className="bg-gradient-to-r from-cyan-900/40 via-blue-900/40 to-indigo-900/40 border border-white/10 rounded-xl p-5">
        <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
          <Radio className="w-7 h-7 text-cyan-400 animate-pulse" />
          N-Dimensional Radionics Console
        </h2>
        <p className="text-xs text-cyan-200 mt-1">
          Adjust multi-dimensional scalars, align localized fields using the stick plate, and broadcast active sigil intentions.
        </p>
      </div>

      {/* Broadcast Globe Visualization */}
      <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-4 flex flex-col lg:flex-row items-center gap-4">
        <div className="flex-shrink-0">
          <MiniGlobe isActive={Object.values(sessions || {}).some(s => s.status === 'running')} size="small" />
        </div>
        <div className="flex-1 space-y-2 text-center lg:text-left">
          <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 justify-center lg:justify-start">
            <Target className="w-4 h-4 text-cyan-400" />
            GLOBAL BROADCAST COVERAGE
          </h3>
          <p className="text-xs text-gray-400">
            Active blessings radiating to {Object.values(sessions || {}).filter(s => s.status === 'running').length} target locations.
            Each pulse represents coherent scalar-wave intention propagating through the planetary field.
          </p>
          <div className="flex flex-wrap gap-2 justify-center lg:justify-start">
            {Object.values(sessions || {}).filter(s => s.status === 'running').slice(0, 5).map(s => (
              <span key={s.id} className="text-[10px] bg-cyan-950/60 text-cyan-300 border border-cyan-500/20 px-2 py-0.5 rounded-full font-mono">
                {s.name || s.intention || 'Active Target'}
              </span>
            ))}
            {Object.values(sessions || {}).filter(s => s.status === 'running').length === 0 && (
              <span className="text-[10px] text-gray-500 italic">No active broadcast targets — start a session to see it on the globe</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ================= COLUMN 1: CONTROLS & RADAR ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              DIMENSIONAL RESONANCE AXES
            </h3>
            
            {/* Dials */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-6 place-items-center">
              {([
                { key: 'd1' as const, name: 'D1: Physical', color: '#2dd4bf' },
                { key: 'd2' as const, name: 'D2: Astral', color: '#818cf8' },
                { key: 'd3' as const, name: 'D3: Mental', color: '#c084fc' },
                { key: 'd4' as const, name: 'D4: Causal', color: '#f472b6' },
                { key: 'd5' as const, name: 'D5: Spiritual', color: '#22d3ee' },
              ]).map(({ key, name, color }) => (
                <div key={key} className="flex flex-col items-center">
                  <RateDial
                    value={dimensions[key]}
                    onChange={(val) => handleDimensionChange(key, val)}
                    color={color}
                    size={80}
                    label={name}
                  />
                  <div className="text-[10px] font-bold tracking-wider mt-3" style={{ color }}>{name}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Coherence Radar SVG Chart */}
          <div className="bg-black/40 p-4 rounded-xl border border-white/5 flex flex-col items-center gap-3">
            <div className="flex justify-between w-full text-xs">
              <span className="text-gray-400">Phase Coherence</span>
              <span className="text-cyan-300 font-bold font-mono">{coherence}%</span>
            </div>
            
            <svg width="160" height="160" className="overflow-visible select-none">
              {/* Radial grids */}
              {[0.2, 0.4, 0.6, 0.8, 1.0].map((scale, i) => (
                <circle
                  key={i}
                  cx={centerX}
                  cy={centerY}
                  r={radarRadius * scale}
                  fill="none"
                  stroke="#1e293b"
                  strokeWidth="1"
                  strokeDasharray={i === 4 ? "0" : "2,2"}
                />
              ))}
              {/* Axes lines */}
              {Array.from({ length: 5 }).map((_, i) => {
                const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
                return (
                  <line
                    key={i}
                    x1={centerX}
                    y1={centerY}
                    x2={centerX + radarRadius * Math.cos(angle)}
                    y2={centerY + radarRadius * Math.sin(angle)}
                    stroke="#1e293b"
                    strokeWidth="1"
                  />
                );
              })}
              {/* Radar Area Polygon */}
              <polygon
                points={radarPoints}
                fill="rgba(34, 211, 238, 0.2)"
                stroke="#22d3ee"
                strokeWidth="2"
              />
              {/* Coordinate points */}
              {Object.values(dimensions).map((val, idx) => {
                const pt = getRadarPoint(idx, val).split(',');
                return (
                  <circle
                    key={idx}
                    cx={pt[0]}
                    cy={pt[1]}
                    r="3.5"
                    fill="#a855f7"
                    stroke="#ffffff"
                    strokeWidth="1"
                    className="animate-pulse"
                  />
                );
              })}
            </svg>
            <div className="text-[10px] text-gray-500 font-mono text-center">HILBERT PHASE RESONANCE MAPPING</div>
          </div>
          
        </div>

        {/* ================= COLUMN 2: DIGITAL STICK PLATE ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Activity className="w-4 h-4 text-purple-400" />
              DIGITAL COPPER STICK PLATE
            </h3>
            <p className="text-xs text-gray-400">
              Drag your mouse across the pad. Subtle tactile resistance (friction) peaks when you cross the resonant node.
            </p>
          </div>

          {/* Stick Canvas Plate */}
          <div 
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="w-full h-48 bg-black/80 rounded-xl border border-yellow-500/20 relative cursor-crosshair overflow-hidden group select-none"
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(234,179,8,0.05) 1px, transparent 1px)',
              backgroundSize: '16px 16px'
            }}
          >
            {/* Outer copper border line */}
            <div className="absolute inset-2 border border-yellow-500/10 rounded-lg pointer-events-none" />

            {/* Locked indicator overlay */}
            {resonantLocked && (
              <div className="absolute inset-0 bg-yellow-950/20 flex items-center justify-center border-2 border-yellow-500/40 pointer-events-none animate-pulse">
                <span className="text-xs font-bold text-yellow-400 tracking-widest font-mono uppercase">RESONANCE LOCK CALIBRATED</span>
              </div>
            )}

            {/* Ripple Wave at drag point */}
            {isRubbing && (
              <div 
                className="absolute w-12 h-12 bg-yellow-500/10 border border-yellow-500/40 rounded-full pointer-events-none -translate-x-1/2 -translate-y-1/2 animate-ping"
                style={{ left: rubPosition.x, top: rubPosition.y }}
              />
            )}

            {/* Target position indicator (dev/only shows slightly) */}
            <div 
              className="absolute w-4 h-4 border border-yellow-500/20 rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              style={{ left: targetLock.x, top: targetLock.y }}
            />

            {/* Friction stats */}
            <div className="absolute bottom-2 left-3 text-[10px] font-mono text-gray-500 pointer-events-none">
              PAD POS: {Math.round(rubPosition.x)}, {Math.round(rubPosition.y)}
            </div>
            <div className="absolute bottom-2 right-3 text-[10px] font-mono text-yellow-400 font-bold pointer-events-none">
              FRICTION COEFFICIENT: {rubCoherence}%
            </div>
          </div>

          {/* Attunement indicators */}
          <div className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Stick Plate Resonance</span>
              <span className={`font-bold font-mono ${resonantLocked ? 'text-yellow-400' : 'text-gray-400'}`}>
                {resonantLocked ? 'CALIBRATED & LOCKED' : 'ALIGNING INDEX...'}
              </span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden border border-white/5">
              <div 
                className={`h-full rounded-full transition-all duration-75 ${
                  resonantLocked 
                    ? 'bg-gradient-to-r from-yellow-500 to-amber-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]' 
                    : 'bg-gradient-to-r from-purple-500 to-cyan-500'
                }`}
                style={{ width: `${rubCoherence}%` }}
              />
            </div>
          </div>

        </div>

        {/* ================= COLUMN 3: ACTIVE SIGIL FORGE ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Gem className="w-4 h-4 text-purple-400" />
              ACTIVE SIGIL TEMPLATE
            </h3>
            
            {latestSigil ? (
              <div className="space-y-4">
                <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg text-center">
                  <span className="text-[10px] font-mono text-purple-400 block uppercase">BROADCAST INTENTION</span>
                  <span className="text-sm font-semibold text-white mt-1 block font-serif">"{latestSigil.intention}"</span>
                  <span className="text-[10px] font-mono text-purple-300 mt-1 block">Reduced Signature: {latestSigil.reduced_letters}</span>
                </div>

                {/* Sigil drawing */}
                <div className="flex gap-4">
                  {/* Magic square vector */}
                  <div className="flex-1 bg-black/60 rounded-xl border border-white/5 p-2 flex flex-col items-center justify-center">
                    <span className="text-[9px] font-mono text-gray-500 mb-1">KAMEA: {latestSigil.kamea.toUpperCase()}</span>
                    <div dangerouslySetInnerHTML={{ __html: latestSigil.svg }} className="w-24 h-24" />
                  </div>
                  
                  {/* Stable diffusion render */}
                  <div className="flex-1 bg-black/60 rounded-xl border border-white/5 p-2 flex flex-col items-center justify-center min-h-[120px]">
                    <span className="text-[9px] font-mono text-gray-500 mb-1">AI RENDER</span>
                    {latestSigil.ai_image ? (
                      <img src={latestSigil.ai_image} alt="AI Sigil" className="w-24 h-24 rounded-lg object-cover" />
                    ) : (
                      <div className="text-[9px] text-gray-600 italic text-center p-2">
                        Offline Fallback Active (SVG Drawing only)
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-center text-gray-500 italic text-xs">
                  Enter an intention to forge a new sigil
                </div>
                <input
                  type="text"
                  value={sigilIntention}
                  onChange={(e) => setSigilIntention(e.target.value)}
                  placeholder="e.g. Protection & Clarity"
                  className="w-full bg-gray-800 text-white text-xs px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none placeholder-gray-500"
                  onKeyDown={(e) => e.key === 'Enter' && sigilIntention.trim() && forgeUserSigil()}
                />
                <button
                  onClick={forgeUserSigil}
                  disabled={!sigilIntention.trim() || isForging}
                  className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-2"
                >
                  <Gem className="w-3.5 h-3.5" />
                  {isForging ? 'Forging...' : 'Forge Sigil'}
                </button>
              </div>
            )}
          </div>

          {/* Broadcast Node controls */}
          <div className="pt-4 border-t border-white/5 space-y-4">
            <h4 className="text-xs font-bold text-gray-400 tracking-wider">BROADCAST TARGET MONITOR</h4>
            
            <div className="bg-white/5 p-3 rounded-lg border border-white/5 max-h-[140px] overflow-y-auto space-y-2">
              {populations.length > 0 ? (
                populations.map(pop => (
                  <div key={pop.id} className="flex justify-between items-center text-xs">
                    <div className="flex items-center gap-1.5 text-gray-300">
                      <Target className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="truncate max-w-[140px]">{pop.name}</span>
                    </div>
                    <span className={`px-2 py-0.5 text-[10px] font-mono rounded-full ${
                      pop.is_active 
                        ? 'bg-green-950 text-green-400 border border-green-500/20' 
                        : 'bg-gray-800 text-gray-500'
                    }`}>
                      {pop.is_active ? 'ACTIVE' : 'STANDBY'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-[10px] text-gray-500 italic">No target populations registered.</div>
              )}
            </div>
            
            <button
              onClick={() => {
                if (latestSigil) {
                  // Broadcast the sigil intention
                  fetch(`/api/v1/sigils/broadcast`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      intention: latestSigil.intention,
                      sigil_id: latestSigil.id,
                      frequency_hz: frequency,
                      duration_minutes: 5
                    })
                  }).then(res => {
                    if (res.ok) {
                      audioFeedback.playSuccess();
                    } else {
                      audioFeedback.playError();
                      message.error(`Broadcast failed: HTTP ${res.status}`);
                    }
                  }).catch(() => {
                    audioFeedback.playError();
                    message.error('Broadcast failed: backend unreachable');
                  });
                }
              }}
              disabled={!latestSigil}
              className="w-full px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2 select-none"
            >
              <Zap className="w-3.5 h-3.5 text-yellow-400" /> Broadcast Sigil Frequency
            </button>
          </div>

        </div>

      </div>

      {/* ================= RADIONICS BROADCAST CONTROLS + RESULTS ================= */}
      <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-cyan-500/20 p-5 space-y-4 mt-6">
        <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
          <RadioIcon className="w-4 h-4 text-cyan-400" />
          RADIONICS CRYSTAL BROADCAST
        </h3>

        {/* Presets — tabbed between Chakra and Harmonic, plus custom */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-[10px] font-mono uppercase text-gray-500">
              Crystal Bowl Presets
            </label>
            <div className="flex items-center gap-1.5">
              {(['chakra', 'harmonic', 'custom'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setPresetTab(tab)}
                  className={`px-2 py-0.5 rounded text-[9px] font-mono uppercase ${
                    presetTab === tab
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-black/20 text-gray-500 border border-white/5 hover:text-gray-300'
                  }`}
                >
                  {tab}
                </button>
              ))}
              <button
                onClick={() => setShowSaveDialog(true)}
                title="Save current dials as preset"
                className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
              >
                ⭐
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {(() => {
              const presetList = presetTab === 'chakra'
                ? CHAKRA_PRESETS
                : presetTab === 'harmonic'
                  ? HARMONIC_PRESETS
                  : customPresets;
              if (presetList.length === 0) {
                return (
                  <div className="col-span-3 text-center text-[10px] text-gray-500 italic py-4">
                    No custom presets yet. Adjust dials then click ⭐ to save.
                  </div>
                );
              }
              return presetList.map((preset) => {
                const isActive = dimensions.d1 === preset.dims.d1
                  && dimensions.d2 === preset.dims.d2
                  && dimensions.d3 === preset.dims.d3
                  && dimensions.d4 === preset.dims.d4
                  && dimensions.d5 === preset.dims.d5;
                const freqs = presetFrequencies(preset);
                const summary = presetFrequencySummary(preset);
                return (
                  <div key={preset.id} className="relative group">
                    <button
                      onClick={() => applyPreset(preset.dims)}
                      className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                        isActive
                          ? 'bg-cyan-950/40 border-cyan-500/40 shadow-[0_0_10px_rgba(34,211,238,0.1)]'
                          : 'bg-black/30 border-white/5 hover:border-cyan-500/20 hover:bg-black/40'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-sm">{preset.icon}</span>
                        <span className="text-xs font-bold text-white">{preset.label}</span>
                        {presetTab === 'custom' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); deleteCustomPreset(preset.id); }}
                            className="ml-auto text-[10px] text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Delete preset"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      <div className="text-[9px] font-mono text-cyan-400">
                        {summary || `${freqs.join('+')} Hz`}
                      </div>
                      <div className="text-[9px] text-gray-500">{preset.description}</div>
                    </button>
                  </div>
                );
              });
            })()}
          </div>

          {/* Live preview — what the current dials will produce */}
          {livePreviewFrequencies.length > 0 && (
            <div className="mt-2 p-2 bg-cyan-950/10 border border-cyan-500/10 rounded-lg flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-mono uppercase text-cyan-400">Live preview:</span>
              {livePreviewFrequencies.map((f, i) => (
                <Tag key={i} color="cyan" className="text-[10px] font-mono">
                  {f} Hz {solfeggioName(f).split(' ')[0]}
                </Tag>
              ))}
            </div>
          )}

          {/* Save dialog */}
          {showSaveDialog && (
            <div className="mt-2 p-2 bg-amber-950/20 border border-amber-500/30 rounded-lg flex items-center gap-2">
              <input
                type="text"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                placeholder="Preset name (e.g. 'My Morning Calm')"
                className="flex-1 bg-gray-800 text-white text-xs px-2 py-1 rounded border border-gray-600 focus:border-amber-500 focus:outline-none"
                onKeyDown={(e) => e.key === 'Enter' && saveCurrentAsPreset()}
                autoFocus
              />
              <button
                onClick={saveCurrentAsPreset}
                disabled={!saveName.trim()}
                className="px-2 py-1 text-xs bg-amber-600 hover:bg-amber-700 disabled:bg-gray-700 text-white rounded"
              >
                Save
              </button>
              <button
                onClick={() => { setShowSaveDialog(false); setSaveName(''); }}
                className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded"
              >
                ✕
              </button>
            </div>
          )}
        </div>

        {/* Controls row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Intention selector */}
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Intention</label>
            <Select
              value={radIntention}
              onChange={(v) => { setRadIntention(v); audioFeedback.playTabChange(); }}
              className="w-full"
              size="small"
              options={[
                { value: 'healing', label: 'Healing (528 Hz)' },
                { value: 'liberation', label: 'Liberation (396 Hz)' },
                { value: 'protection', label: 'Protection (741 Hz)' },
                { value: 'love', label: 'Love (528 Hz)' },
                { value: 'peace', label: 'Peace (852 Hz)' },
                { value: 'wisdom', label: 'Wisdom (963 Hz)' },
                { value: 'empowerment', label: 'Empowerment (528 Hz)' },
                { value: 'reconciliation', label: 'Reconciliation (639 Hz)' },
              ]}
            />
          </div>

          {/* Target input */}
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Target</label>
            <input
              type="text"
              value={radTarget}
              onChange={(e) => setRadTarget(e.target.value)}
              placeholder="e.g. all beings, John, cancer patients"
              className="w-full bg-gray-800 text-white text-xs px-3 py-1.5 rounded border border-gray-600 focus:border-cyan-500 focus:outline-none placeholder-gray-500"
            />
          </div>

          {/* Direct frequency override */}
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">
              Direct Frequency (Hz) — overrides dials
            </label>
            <input
              type="text"
              value={directFreq}
              onChange={(e) => setDirectFreq(e.target.value)}
              placeholder="e.g. 528 or 136.1"
              className="w-full bg-gray-800 text-white text-xs px-3 py-1.5 rounded border border-gray-600 focus:border-amber-500 focus:outline-none placeholder-gray-500 font-mono"
            />
          </div>
        </div>

        {/* Rate values preview */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono uppercase text-gray-500">Active dials:</span>
          {directFreq ? (
            <Tag color="amber" className="text-[10px] font-mono">
              Direct: {directFreq} Hz (overrides dials)
            </Tag>
          ) : (
            Object.entries(dimensions).map(([key, val]) => (
              <Tag key={key} color="cyan" className="text-[10px] font-mono">
                {key.toUpperCase()}: {Math.round(val)}
              </Tag>
            ))
          )}
        </div>

        {/* Broadcast button */}
        <button
          onClick={handleRadionicsBroadcast}
          disabled={isBroadcasting}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2"
        >
          {isBroadcasting ? (
            <>
              <Activity className="w-3.5 h-3.5 animate-spin" />
              Broadcasting...
            </>
          ) : (
            <>
              <Zap className="w-3.5 h-3.5 text-yellow-400" />
              Start Radionics Broadcast
            </>
          )}
        </button>

        {/* Broadcast result display */}
        {broadcastResult && (
          <div className="bg-cyan-950/20 border border-cyan-500/20 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-cyan-300">
                {broadcastResult.status === 'success' || broadcastResult.status === 'active' ? '✅ BROADCAST ACTIVE' : broadcastResult.status}
              </span>
              <span className="text-[10px] font-mono text-gray-500">
                Session: {broadcastResult.session_id?.slice(0, 8) || '...'}
              </span>
            </div>

            {/* Derived frequencies */}
            {broadcastResult.frequencies && broadcastResult.frequencies.length > 0 && (
              <div>
                <div className="text-[10px] font-mono uppercase text-gray-500 mb-1">Prayer Bowl Carrier Frequencies</div>
                <div className="flex gap-2 flex-wrap">
                  {broadcastResult.frequencies.map((freq, i) => (
                    <div key={i} className="flex items-center gap-1 px-2 py-1 bg-black/30 rounded border border-cyan-500/10">
                      <Waves className="w-3 h-3 text-cyan-400" />
                      <span className="text-xs font-mono text-cyan-300">{freq.toFixed(2)} Hz</span>
                      {broadcastResult.solfeggio_names?.[i] && (
                        <span className="text-[9px] text-gray-500">({broadcastResult.solfeggio_names[i]})</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Crystal + Scalar output status */}
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-black/20 rounded p-2">
                <div className="text-[9px] font-mono uppercase text-gray-500">Crystal Output</div>
                <div className={`text-xs font-bold ${broadcastResult.crystal_output?.status === 'completed' || broadcastResult.crystal_output?.status === 'active' ? 'text-green-400' : 'text-red-400'}`}>
                  {broadcastResult.crystal_output?.status || 'N/A'}
                </div>
                {broadcastResult.crystal_output?.error && (
                  <div className="text-[9px] text-red-400 truncate">{broadcastResult.crystal_output.error}</div>
                )}
              </div>
              <div className="bg-black/20 rounded p-2">
                <div className="text-[9px] font-mono uppercase text-gray-500">Scalar Output</div>
                <div className={`text-xs font-bold ${broadcastResult.scalar_output?.status === 'failed' ? 'text-red-400' : 'text-green-400'}`}>
                  {broadcastResult.scalar_output ? 'Active' : 'N/A'}
                </div>
                {broadcastResult.scalar_mops && (
                  <div className="text-[9px] text-gray-500">{broadcastResult.scalar_mops.toFixed(2)} MOPS</div>
                )}
              </div>
            </div>

            <div className="text-[10px] text-gray-500 italic text-center pt-1">
              Prayer bowl synthesis active — crystal grid resonating at {broadcastResult.frequencies?.length || 0} carrier frequencies
            </div>
          </div>
        )}
      </div>

      {/* ================= RITUAL BROADCAST (LLM-generated ritual + crystal bowl) ================= */}
      <div className="bg-gradient-to-br from-amber-950/20 to-purple-950/20 rounded-xl border border-amber-500/20 p-5 space-y-4 mt-6">
        <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          RITUAL BROADCAST
        </h3>

        <p className="text-[10px] text-gray-400">
          Generate a tradition-specific ritual text and immediately broadcast it through the crystal grid at the carrier frequencies
          derived from the current dimensional rates (or the direct frequency override).
        </p>

        {/* Ritual type + intention + target row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Ritual Type</label>
            <Select
              value={ritualType}
              onChange={(v) => setRitualType(v)}
              className="w-full"
              size="small"
              options={[
                { value: 'universal', label: 'Universal Compassion' },
                { value: 'dedication_of_endeavors', label: 'Dedication of All Endeavors' },
                { value: 'earthquake', label: 'Earthquake Relief' },
                { value: 'war', label: 'War/Conflict Relief' },
                { value: 'illness', label: 'Healing' },
                { value: 'death', label: 'Liberation of the Deceased' },
                { value: 'displacement', label: 'Refugee/Displacement Relief' },
                { value: 'anger', label: 'Anger → Forgiveness (Vajrasattva)' },
                { value: 'purification', label: 'Purification & Confession (Vajrasattva)' },
                { value: 'fear', label: 'Fear/Anxiety → Fearlessness (Green Tara)' },
              ]}
            />
          </div>
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Intention</label>
            <input
              type="text"
              value={ritualIntention}
              onChange={(e) => setRitualIntention(e.target.value)}
              placeholder="e.g. Dedication of all my endeavors toward the benefit of all beings"
              className="w-full bg-gray-800 text-white text-xs px-3 py-1.5 rounded border border-gray-600 focus:border-amber-500 focus:outline-none placeholder-gray-500"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Target</label>
            <input
              type="text"
              value={ritualTarget}
              onChange={(e) => setRitualTarget(e.target.value)}
              placeholder="e.g. all mother sentient beings"
              className="w-full bg-gray-800 text-white text-xs px-3 py-1.5 rounded border border-gray-600 focus:border-amber-500 focus:outline-none placeholder-gray-500"
            />
          </div>
        </div>

        {/* Rate values preview (mirrors the radionics block) */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-mono uppercase text-gray-500">Broadcast carriers:</span>
          {directFreq ? (
            <Tag color="amber" className="text-[10px] font-mono">
              Direct: {directFreq} Hz (overrides dials)
            </Tag>
          ) : (
            Object.entries(dimensions).map(([key, val]) => (
              <Tag key={key} color="purple" className="text-[10px] font-mono">
                {key.toUpperCase()}: {Math.round(val)}
              </Tag>
            ))
          )}
        </div>

        {/* Generate button */}
        <button
          onClick={handleRitualBroadcast}
          disabled={isRitualGenerating}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-amber-600 to-purple-600 hover:from-amber-700 hover:to-purple-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2"
        >
          {isRitualGenerating ? (
            <><Activity className="w-3.5 h-3.5 animate-spin" /> Generating Ritual...</>
          ) : (
            <><Sparkles className="w-3.5 h-3.5 text-yellow-400" /> Generate Ritual + Broadcast</>
          )}
        </button>

        {/* Generated ritual text */}
        {ritualMarkdown && (
          <div className="bg-black/40 rounded-lg border border-amber-500/10 p-4 max-h-[400px] overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] font-mono uppercase text-amber-400">Generated Ritual</span>
              <div className="flex gap-2">
                <button
                  onClick={() => navigator.clipboard.writeText(ritualMarkdown)}
                  className="text-[9px] text-gray-500 hover:text-amber-400"
                >
                  <Copy className="w-3 h-3 inline" /> Copy
                </button>
              </div>
            </div>
            <pre className="text-[11px] text-gray-300 whitespace-pre-wrap font-serif leading-relaxed">
              {ritualMarkdown}
            </pre>
          </div>
        )}

        {/* Broadcast status footer */}
        {ritualResult && (
          <div className="flex items-center gap-3 text-[10px] text-gray-500 flex-wrap">
            <Tag color={ritualResult.status === 'success' ? 'green' : 'orange'}>{ritualResult.status}</Tag>
            {ritualResult.session_id && (
              <span className="font-mono">Session: {String(ritualResult.session_id).slice(0, 8)}</span>
            )}
            {ritualResult.frequencies && ritualResult.frequencies.length > 0 && (
              <span>Frequencies: {ritualResult.frequencies.map((f: number) => f.toFixed(1)).join(', ')} Hz</span>
            )}
            {ritualResult.solfeggio_names && ritualResult.solfeggio_names.length > 0 && (
              <span>Solfeggio: {ritualResult.solfeggio_names.join(', ')}</span>
            )}
            {ritualResult.archived_narrative_id && (
              <span>Archived: #{ritualResult.archived_narrative_id}</span>
            )}
            {ritualResult.tts_result && (
              <Tag color={
                ritualResult.tts_result.status === 'completed' ? 'green'
                : ritualResult.tts_result.status === 'queued' ? 'blue'
                : ritualResult.tts_result.status === 'failed' ? 'red'
                : 'orange'
              }>
                TTS: {ritualResult.tts_result.status}
                {ritualResult.tts_result.sections_recited
                  ? ` (${ritualResult.tts_result.sections_recited} sections)`
                  : ''}
              </Tag>
            )}
          </div>
        )}
      </div>

      {/* ================= SUTRA RECITATION (TTS + crystal bowl accompaniment) ================= */}
      <div className="bg-gradient-to-br from-teal-950/20 to-emerald-950/20 rounded-xl border border-teal-500/20 p-5 space-y-4 mt-6">
        <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
          <BookOpen className="w-4 h-4 text-teal-400" />
          SUTRA RECITATION
        </h3>

        <p className="text-[10px] text-gray-400">
          Recite a Buddhist sutra passage (Heart Sutra, Diamond Sutra, Arya Sanghata, Golden Light, Vimalakirti)
          with crystal bowl accompaniment. Select a specific sutra by ID, or pick a theme for automatic passage selection.
        </p>

        {/* Sutra + theme + repeat row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Sutra</label>
            <Select
              value={selectedSutraId || undefined}
              onChange={(v) => setSelectedSutraId(v ?? '')}
              placeholder={sutraList.length === 0 ? 'Loading sutras…' : 'Select a sutra'}
              className="w-full"
              size="small"
              allowClear
              disabled={sutraList.length === 0}
              options={sutraList.map((s) => ({
                value: s.id,
                label: `${s.sutra} — ${s.chapter}`,
              }))}
            />
          </div>
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Theme</label>
            <Select
              value={selectedTheme}
              onChange={(v) => setSelectedTheme(v)}
              className="w-full"
              size="small"
              disabled={!!selectedSutraId}
              options={[
                { value: 'protection', label: 'Protection' },
                { value: 'healing', label: 'Healing' },
                { value: 'dedication', label: 'Dedication' },
                { value: 'impermanence', label: 'Impermanence' },
                { value: 'emptiness', label: 'Emptiness' },
                { value: 'loss', label: 'Loss' },
              ]}
            />
          </div>
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Repeat Count</label>
            <Select
              value={sutraRepeatCount}
              onChange={(v) => setSutraRepeatCount(v)}
              className="w-full"
              size="small"
              options={[
                { value: 1, label: '1 ×' },
                { value: 3, label: '3 ×' },
                { value: 7, label: '7 ×' },
                { value: 108, label: '108 ×' },
              ]}
            />
          </div>
        </div>

        {/* Recite button */}
        <button
          onClick={handleSutraRecitation}
          disabled={isSutraReciting}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2"
        >
          {isSutraReciting ? (
            <><Activity className="w-3.5 h-3.5 animate-spin" /> Reciting…</>
          ) : (
            <><BookOpen className="w-3.5 h-3.5 text-teal-200" /> Recite Sutra</>
          )}
        </button>

        {/* Passage display */}
        {sutraResult && sutraResult.passage && (
          <div className="bg-black/40 rounded-lg border border-teal-500/10 p-4 max-h-[400px] overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] font-mono uppercase text-teal-400">
                {sutraResult.sutra} — {sutraResult.chapter}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => navigator.clipboard.writeText(sutraResult.passage)}
                  className="text-[9px] text-gray-500 hover:text-teal-400"
                >
                  <Copy className="w-3 h-3 inline" /> Copy
                </button>
              </div>
            </div>
            {sutraResult.sanskrit_name && (
              <div className="text-[9px] font-mono italic text-teal-300/70 mb-2">{sutraResult.sanskrit_name}</div>
            )}
            {sutraResult.context && (
              <div className="text-[9px] text-gray-500 mb-2 italic">{sutraResult.context}</div>
            )}
            <pre className="text-[11px] text-gray-300 whitespace-pre-wrap font-serif leading-relaxed">
              {sutraResult.passage}
            </pre>
            {sutraResult.tags && sutraResult.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-white/5">
                {sutraResult.tags.map((tag, i) => (
                  <Tag key={i} color="cyan" className="text-[9px] font-mono">{tag}</Tag>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TTS-friendly version (collapsible) */}
        {sutraResult && sutraResult.passage_tts_friendly && sutraResult.passage_tts_friendly !== sutraResult.passage && (
          <details className="bg-black/30 rounded-lg border border-teal-500/10">
            <summary className="px-3 py-2 text-[10px] font-mono uppercase text-teal-400 cursor-pointer hover:text-teal-300">
              TTS-Friendly Phonetic Version
            </summary>
            <div className="px-3 pb-3">
              <pre className="text-[10px] text-gray-400 whitespace-pre-wrap font-mono leading-relaxed">
                {sutraResult.passage_tts_friendly}
              </pre>
            </div>
          </details>
        )}

        {/* Status footer */}
        {sutraResult && (
          <div className="flex items-center gap-3 text-[10px] text-gray-500 flex-wrap">
            <Tag color={sutraResult.status === 'success' ? 'green' : 'orange'}>{sutraResult.status}</Tag>
            {sutraResult.session_id && (
              <span className="font-mono">Session: {sutraResult.session_id.slice(0, 8)}</span>
            )}
            <Tag color={sutraResult.crystal_output?.status === 'active' ? 'green' : 'orange'}>
              Crystal: {sutraResult.crystal_output?.status ?? 'N/A'}
            </Tag>
            {sutraResult.tts_result && (
              <Tag color={sutraResult.tts_result.status === 'success' ? 'green' : 'orange'}>
                TTS: {sutraResult.tts_result.status}
              </Tag>
            )}
            {sutraResult.frequencies && sutraResult.frequencies.length > 0 && (
              <span>Frequencies: {sutraResult.frequencies.map((f) => f.toFixed(1)).join(', ')} Hz</span>
            )}
            {sutraResult.solfeggio_names && sutraResult.solfeggio_names.length > 0 && (
              <span>Solfeggio: {sutraResult.solfeggio_names.join(', ')}</span>
            )}
          </div>
        )}
      </div>

      {/* ================= DHARANI RECITATION (TTS + crystal bowl accompaniment) ================= */}
      <div className="bg-gradient-to-br from-indigo-950/20 to-violet-950/20 rounded-xl border border-indigo-500/20 p-5 space-y-4 mt-6">
        <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
          <Flower2 className="w-4 h-4 text-indigo-400" />
          DHARANI RECITATION
        </h3>

        <p className="text-[10px] text-gray-400">
          Recite a protective dharani (Great Compassion, Ushnisha Vijaya, Vajrasattva 100-syllable, Cundi,
          Shurangama, Medicine Buddha, Green Tara, Guru Rinpoche, Heart Sutra, Amitabha, Manjushri,
          Prajnaparamita) with crystal bowl accompaniment. Each dharani is dedicated to a specific deity
          and tuned to a particular frequency and chakra.
        </p>

        {/* Dharani + repeat count row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Dharani</label>
            <Select
              value={selectedDharaniId || undefined}
              onChange={(v) => setSelectedDharaniId(v ?? '')}
              placeholder={dharaniList.length === 0 ? 'Loading dharanis…' : 'Select a dharani'}
              className="w-full"
              size="small"
              allowClear
              disabled={dharaniList.length === 0}
              options={dharaniList.map((d) => ({
                value: d.id,
                label: `${d.name} — ${d.deity}`,
              }))}
            />
          </div>
          <div>
            <label className="text-[10px] font-mono uppercase text-gray-500 mb-1 block">Repeat Count</label>
            <Select
              value={dharaniRepeatCount}
              onChange={(v) => setDharaniRepeatCount(v)}
              className="w-full"
              size="small"
              options={[
                { value: 1, label: '1 ×' },
                { value: 3, label: '3 ×' },
                { value: 7, label: '7 ×' },
                { value: 21, label: '21 ×' },
                { value: 108, label: '108 ×' },
              ]}
            />
          </div>
        </div>

        {/* Selected dharani info tags */}
        {selectedDharaniId && (() => {
          const selected = dharaniList.find((d) => d.id === selectedDharaniId);
          if (!selected) return null;
          return (
            <div className="bg-black/30 rounded-lg border border-indigo-500/10 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase text-indigo-300">{selected.name}</span>
                <span className="text-[9px] font-mono text-gray-500">{selected.tradition}</span>
              </div>
              {selected.sanskrit && (
                <div className="text-[10px] font-mono italic text-indigo-300/70">{selected.sanskrit}</div>
              )}
              <div className="flex flex-wrap gap-2">
                <Tag color="purple" className="text-[9px] font-mono">Deity: {selected.deity}</Tag>
                {selected.chakra && (
                  <Tag color="geekblue" className="text-[9px] font-mono">Chakra: {selected.chakra}</Tag>
                )}
                {selected.frequency_hz && (
                  <Tag color="magenta" className="text-[9px] font-mono">{selected.frequency_hz} Hz</Tag>
                )}
              </div>
              {selected.purpose && (
                <div className="text-[10px] text-gray-400 italic">{selected.purpose}</div>
              )}
              {selected.text_sanskrit_preview && (
                <div className="text-[9px] text-gray-500 italic pt-2 border-t border-white/5">
                  Sanskrit preview: {selected.text_sanskrit_preview}
                </div>
              )}
            </div>
          );
        })()}

        {/* Recite button */}
        <button
          onClick={handleDharaniRecitation}
          disabled={isDharaniReciting || !selectedDharaniId}
          className="w-full px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2"
        >
          {isDharaniReciting ? (
            <><Activity className="w-3.5 h-3.5 animate-spin" /> Reciting…</>
          ) : (
            <><Flower2 className="w-3.5 h-3.5 text-indigo-200" /> Recite Dharani</>
          )}
        </button>

        {/* Passage display */}
        {dharaniResult && dharaniResult.passage && (
          <div className="bg-black/40 rounded-lg border border-indigo-500/10 p-4 max-h-[400px] overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] font-mono uppercase text-indigo-400">
                {dharaniResult.name}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => navigator.clipboard.writeText(dharaniResult.passage)}
                  className="text-[9px] text-gray-500 hover:text-indigo-400"
                >
                  <Copy className="w-3 h-3 inline" /> Copy
                </button>
              </div>
            </div>
            {dharaniResult.sanskrit_name && (
              <div className="text-[9px] font-mono italic text-indigo-300/70 mb-2">{dharaniResult.sanskrit_name}</div>
            )}
            {(dharaniResult.deity || dharaniResult.purpose || dharaniResult.chakra) && (
              <div className="flex flex-wrap gap-2 mb-2">
                {dharaniResult.deity && (
                  <Tag color="purple" className="text-[9px] font-mono">Deity: {dharaniResult.deity}</Tag>
                )}
                {dharaniResult.chakra && (
                  <Tag color="geekblue" className="text-[9px] font-mono">Chakra: {dharaniResult.chakra}</Tag>
                )}
                {dharaniResult.frequency_hz && (
                  <Tag color="magenta" className="text-[9px] font-mono">{dharaniResult.frequency_hz} Hz</Tag>
                )}
              </div>
            )}
            {dharaniResult.purpose && (
              <div className="text-[9px] text-gray-500 mb-2 italic">{dharaniResult.purpose}</div>
            )}
            <pre className="text-[11px] text-gray-300 whitespace-pre-wrap font-serif leading-relaxed">
              {dharaniResult.passage}
            </pre>
          </div>
        )}

        {/* TTS-friendly version (collapsible) */}
        {dharaniResult && dharaniResult.passage_tts_friendly && dharaniResult.passage_tts_friendly !== dharaniResult.passage && (
          <details className="bg-black/30 rounded-lg border border-indigo-500/10">
            <summary className="px-3 py-2 text-[10px] font-mono uppercase text-indigo-400 cursor-pointer hover:text-indigo-300">
              TTS-Friendly Phonetic Version
            </summary>
            <div className="px-3 pb-3">
              <pre className="text-[10px] text-gray-400 whitespace-pre-wrap font-mono leading-relaxed">
                {dharaniResult.passage_tts_friendly}
              </pre>
            </div>
          </details>
        )}

        {/* Status footer */}
        {dharaniResult && (
          <div className="flex items-center gap-3 text-[10px] text-gray-500 flex-wrap">
            <Tag color={dharaniResult.status === 'success' ? 'green' : 'orange'}>{dharaniResult.status}</Tag>
            {dharaniResult.session_id && (
              <span className="font-mono">Session: {dharaniResult.session_id.slice(0, 8)}</span>
            )}
            <Tag color={dharaniResult.crystal_output?.status === 'active' ? 'green' : 'orange'}>
              Crystal: {dharaniResult.crystal_output?.status ?? 'N/A'}
            </Tag>
            {dharaniResult.tts_result && (
              <Tag color={dharaniResult.tts_result.status === 'success' ? 'green' : 'orange'}>
                TTS: {dharaniResult.tts_result.status}
              </Tag>
            )}
            {dharaniResult.frequencies && dharaniResult.frequencies.length > 0 && (
              <span>Frequencies: {dharaniResult.frequencies.map((f) => f.toFixed(1)).join(', ')} Hz</span>
            )}
            {dharaniResult.solfeggio_names && dharaniResult.solfeggio_names.length > 0 && (
              <span>Solfeggio: {dharaniResult.solfeggio_names.join(', ')}</span>
            )}
          </div>
        )}
      </div>

    </div>
  );
};

export default BroadcastPanel;
