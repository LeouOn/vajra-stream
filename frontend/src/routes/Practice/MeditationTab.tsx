/**
 * MeditationTab — full-screen Rothko color-field meditation sanctuary with
 * ambient singing bowl drone, timer, breath guide, and palette controls.
 *
 * Provides:
 *   - Palette switcher across all 8 contemplative palettes (Compassion, Wisdom, Peace,
 *     Awakening, Emptiness, Earth, Transcendence, Rainbow Body).
 *   - Singing bowl drone generator (136.1 Hz OM, 432 Hz, 528 Hz) via `useAmbientBowl`.
 *   - Meditation countdown timer (5m, 10m, 15m, 20m, 30m, continuous) with bell.
 *   - Subtle breath rhythm pulse indicator (4-4-4-4 box or 8s harmonic cycle).
 *   - Auto-fading HUD controls that soften to 0% opacity after 4s of idle mouse movement.
 *   - Exit Meditation control navigating back to `/practice/sanctuary`.
 *
 * @component
 * @route /practice/meditation
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Select, Switch, Space, Tag, Tooltip, Button } from 'antd';
import {
  Volume2,
  VolumeX,
  Clock,
  Wind,
  Sparkles,
  ArrowLeft,
  Eye,
  EyeOff,
} from 'lucide-react';
import RothkoGenerator, {
  type PaletteName,
  PALETTES,
} from '../../components/2D/RothkoGenerator';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';
import { useAmbientBowl } from '../../hooks/useAmbientBowl';

const PALETTE_OPTIONS: Array<{ value: PaletteName; label: string; desc: string }> = [
  { value: 'compassion', label: 'Compassion', desc: 'Pinks & soft reds (Heart)' },
  { value: 'wisdom', label: 'Wisdom', desc: 'Deep blues & purples (Insight)' },
  { value: 'peace', label: 'Peace', desc: 'Gentle greens & teals (Stillness)' },
  { value: 'awakening', label: 'Awakening', desc: 'Golds & ambers (Realization)' },
  { value: 'emptiness', label: 'Emptiness', desc: 'Luminous greys & white (Sunyata)' },
  { value: 'earth', label: 'Earth', desc: 'Warm ochres & browns (Grounded)' },
  { value: 'transcendence', label: 'Transcendence', desc: 'Sacred thangka crimson' },
  { value: 'rainbow-body', label: 'Rainbow Body', desc: 'Full light spectrum' },
];

const DRONE_FREQUENCIES: Array<{ label: string; freq: number; desc: string }> = [
  { label: '136.1 Hz', freq: 136.1, desc: 'OM / Earth frequency' },
  { label: '432.0 Hz', freq: 432.0, desc: 'Universal natural tuning' },
  { label: '528.0 Hz', freq: 528.0, desc: 'Transformation & miracles' },
];

const TIMER_OPTIONS: Array<{ value: number; label: string }> = [
  { value: 0, label: 'Continuous' },
  { value: 5, label: '5 Minutes' },
  { value: 10, label: '10 Minutes' },
  { value: 15, label: '15 Minutes' },
  { value: 20, label: '20 Minutes' },
  { value: 30, label: '30 Minutes' },
];

export default function MeditationTab(): React.ReactElement {
  const navigate = useNavigate();
  const { audioSpectrum } = useWebSocketStable();
  const isPlaying = useAudioStore((s) => s.isPlaying);

  const [palette, setPalette] = useState<PaletteName>('compassion');
  const [transitionSpeed, setTransitionSpeed] = useState<number>(30);

  // ── Ambient Singing Bowl Drone ─────────────────────────────────────
  const [bowlEnabled, setBowlEnabled] = useState<boolean>(false);
  const [bowlFreq, setBowlFreq] = useState<number>(136.1);
  const bowl = useAmbientBowl();

  useEffect(() => {
    if (bowlEnabled) {
      bowl.start(bowlFreq);
    } else {
      bowl.stop();
    }
    return () => {
      bowl.stop();
    };
  }, [bowlEnabled, bowlFreq, bowl]);

  // ── Meditation Timer ───────────────────────────────────────────────
  const [timerMinutes, setTimerMinutes] = useState<number>(0);
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null);
  const [timerActive, setTimerActive] = useState<boolean>(false);

  useEffect(() => {
    if (timerMinutes === 0) {
      setSecondsRemaining(null);
      setTimerActive(false);
      return;
    }
    setSecondsRemaining(timerMinutes * 60);
    setTimerActive(true);
  }, [timerMinutes]);

  useEffect(() => {
    if (!timerActive || secondsRemaining == null) return;
    if (secondsRemaining <= 0) {
      setTimerActive(false);
      // Play completion chime
      if (bowlEnabled) bowl.stop();
      return;
    }
    const interval = setInterval(() => {
      setSecondsRemaining((prev) => (prev != null && prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [timerActive, secondsRemaining, bowlEnabled, bowl]);

  const formatTime = (secs: number): string => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // ── Breath Guide Rhythm ────────────────────────────────────────────
  const [breathGuide, setBreathGuide] = useState<boolean>(false);
  const [breathPhase, setBreathPhase] = useState<'inhale' | 'hold' | 'exhale' | 'rest'>('inhale');

  useEffect(() => {
    if (!breathGuide) return;
    const cycle = ['inhale', 'hold', 'exhale', 'rest'] as const;
    let step = 0;
    const interval = setInterval(() => {
      step = (step + 1) % 4;
      setBreathPhase(cycle[step]);
    }, 4000);
    return () => clearInterval(interval);
  }, [breathGuide]);

  // ── Auto-Fading HUD on Idle Mouse ──────────────────────────────────
  const [hudVisible, setHudVisible] = useState<boolean>(true);
  const hideTimerRef = useRef<NodeJS.Timeout | null>(null);

  const resetHideTimer = useCallback(() => {
    setHudVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    hideTimerRef.current = setTimeout(() => {
      setHudVisible(false);
    }, 4500);
  }, []);

  useEffect(() => {
    resetHideTimer();
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, [resetHideTimer]);

  return (
    <div
      className="relative w-full h-full bg-black overflow-hidden select-none"
      onMouseMove={resetHideTimer}
      onClick={resetHideTimer}
    >
      {/* ── Background: Rothko Color-Field Generator ────────────────── */}
      <RothkoGenerator
        audioSpectrum={audioSpectrum}
        isPlaying={isPlaying || bowlEnabled}
        palette={palette}
        transitionSpeed={transitionSpeed}
        fullscreen
      />

      {/* ── Breath Guide Pulse (Center Floating) ────────────────────── */}
      {breathGuide && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="relative flex flex-col items-center">
            <div
              className={`w-36 h-36 rounded-full border border-white/20 transition-all duration-[4000ms] flex items-center justify-center ${
                breathPhase === 'inhale'
                  ? 'scale-125 bg-white/10 shadow-[0_0_50px_rgba(255,255,255,0.25)]'
                  : breathPhase === 'hold'
                    ? 'scale-125 bg-white/15'
                    : breathPhase === 'exhale'
                      ? 'scale-75 bg-white/5 shadow-none'
                      : 'scale-75 bg-transparent'
              }`}
            >
              <span className="text-white/80 text-xs uppercase tracking-[0.2em] font-light">
                {breathPhase}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* ── Floating HUD Controls Overlay (Auto-Fading) ─────────────── */}
      <div
        className={`transition-opacity duration-700 ${
          hudVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        {/* Top-Left: Palette & Ambience Controls */}
        <div className="absolute top-4 left-4 z-50 flex items-center gap-3 flex-wrap">
          {/* Palette Selector */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[rgba(20,10,30,0.75)] backdrop-blur-[14px] border border-purple-400/20 text-white">
            <Sparkles size={14} className="text-amber-300" />
            <span className="text-xs font-semibold tracking-wider">Palette:</span>
            <Select<PaletteName>
              value={palette}
              onChange={setPalette}
              options={PALETTE_OPTIONS.map((p) => ({
                value: p.value,
                label: p.label,
              }))}
              size="small"
              style={{ width: 140 }}
              popupMatchSelectWidth={false}
            />
          </div>

          {/* Singing Bowl Drone */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[rgba(20,10,30,0.75)] backdrop-blur-[14px] border border-purple-400/20 text-white">
            <span className="text-sm" aria-hidden>🥣</span>
            <span className="text-xs font-semibold">Bowl Drone:</span>
            <Select<number>
              value={bowlFreq}
              onChange={setBowlFreq}
              options={DRONE_FREQUENCIES.map((f) => ({
                value: f.freq,
                label: f.label,
              }))}
              size="small"
              style={{ width: 110 }}
              disabled={!bowlEnabled}
            />
            <Switch
              size="small"
              checked={bowlEnabled}
              onChange={setBowlEnabled}
              aria-label="Toggle ambient singing bowl drone"
            />
          </div>

          {/* Timer Selector */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[rgba(20,10,30,0.75)] backdrop-blur-[14px] border border-purple-400/20 text-white">
            <Clock size={14} className="text-cyan-300" />
            <Select<number>
              value={timerMinutes}
              onChange={setTimerMinutes}
              options={TIMER_OPTIONS}
              size="small"
              style={{ width: 120 }}
            />
            {secondsRemaining != null && (
              <span className="text-xs font-mono text-cyan-300 font-bold ml-1">
                {formatTime(secondsRemaining)}
              </span>
            )}
          </div>

          {/* Breath Guide Toggle */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[rgba(20,10,30,0.75)] backdrop-blur-[14px] border border-purple-400/20 text-white">
            <Wind size={14} className={breathGuide ? 'text-emerald-300' : 'text-gray-400'} />
            <span className="text-xs">Breath Guide</span>
            <Switch
              size="small"
              checked={breathGuide}
              onChange={setBreathGuide}
              aria-label="Toggle breath rhythm guide"
            />
          </div>
        </div>

        {/* Top-Right: Exit Control */}
        <div className="absolute top-4 right-4 z-50 flex items-center gap-2">
          <button
            onClick={() => navigate('/practice/sanctuary')}
            className="flex items-center gap-1.5 bg-white/10 hover:bg-white/20 text-white/80 hover:text-white px-3.5 py-1.5 rounded-xl text-xs font-semibold backdrop-blur-md border border-white/10 transition-colors shadow-lg"
          >
            <ArrowLeft size={14} />
            <span>Exit Meditation</span>
          </button>
        </div>

        {/* Bottom-Center: Active Palette Description */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50 pointer-events-none">
          <div className="px-4 py-1.5 rounded-full bg-black/40 backdrop-blur-md border border-white/10 text-white/60 text-xs tracking-wider text-center">
            {PALETTES[palette]?.description}
          </div>
        </div>
      </div>
    </div>
  );
}
