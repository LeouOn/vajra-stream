/**
 * ScalarTab — the "Living Mandala" practice surface at `/practice/scalar`.
 *
 * The ScalarWaveVisualizer as a full-bleed centerpiece, overlaid with four
 * floating glassmorphism panels that turn the canvas into a sacred instrument:
 *
 *   ┌─────────────────────────┐   ┌──────────────────────┐
 *   │ MOPS readout (top-left) │   │ Intention (top-right) │
 *   │ scalar / mantras /      │   │ input + Send Blessing │
 *   │ crystals / divination   │   │ + element badge       │
 *   └─────────────────────────┘   └──────────────────────┘
 *                       ┌──────────────────────┐
 *                       │  Living Mandala ✦    │   ← canvas breathes here
 *                       └──────────────────────┘
 *   ┌──────────────────────────────────────────────────┐
 *   │ Audio controls (bottom-left): mode pills, freq,  │
 *   │ volume, prayer-bowl toggle, generate/play/stop   │
 *   └──────────────────────────────────────────────────┘
 *
 * Event wiring (cross-system reactivity):
 *   - Journey poll (5s)        → setElementMood(element) recolors the palette
 *   - MOPS poll (2s)           → drives the top-left readout
 *   - crystalStatus active ──→ triggerCrystalLayer (translucent band + ripple)
 *   - new blessing session  ──→ triggerBlessingRipple + merit particles
 *   - healing session       ──→ setHealingMood(true) for 30s (slower, deeper)
 *   - "Send as Blessing" btn → ripple + particle burst (manual practice)
 *
 * The visualization is intrinsically beautiful without audio — the reactive
 * overlay and 8-second cosmic breath are always on, so the page reads as
 * ambient sacred art even when the audio engine is silent.
 *
 * @component
 * @route /practice/scalar
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import ScalarWaveVisualizer, {
  type ScalarMode,
  type ScalarVizAPI,
} from '../../components/2D/ScalarWaveVisualizer';
import { useAudioStore } from '../../stores/audioStore';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';

// ─── Element display (local copy — mirrors JourneyCard's map so this tab
//     stays self-contained and doesn't reach into another component's guts).
const ELEMENT_EMOJIS: Record<string, string> = {
  Fire: '🔥',
  Water: '💧',
  Earth: '🌍',
  Air: '💨',
  Wood: '🌿',
  Metal: '⚙️',
};

// Element → blessing hue (must match the visualizer's ELEMENT_PALETTES keys).
const ELEMENT_HUES: Record<string, number> = {
  Fire: 25,
  Water: 200,
  Earth: 60,
  Air: 270,
  Wood: 130,
  Metal: 220,
  Cosmic: 280,
};

const MODE_OPTIONS: Array<{ key: ScalarMode; label: string; hint: string }> = [
  { key: 'living', label: 'Living', hint: 'All layers + reactive breath' },
  { key: 'interference', label: 'Interference', hint: 'Stacked wave fields' },
  { key: 'spiral', label: 'Spiral', hint: 'Logarithmic sweep' },
  { key: 'standing', label: 'Standing', hint: 'Vertical resonance' },
  { key: 'particle-storm', label: 'Storm', hint: 'Dense crest sparks' },
];

const FREQ_PRESETS: Array<{ label: string; freq: number; sub: string }> = [
  { label: 'OM', freq: 136.1, sub: 'Earth resonance' },
  { label: 'Heart', freq: 528.0, sub: 'Love / DNA repair' },
  { label: 'Schumann', freq: 7.83, sub: 'Planetary baseline' },
  { label: 'Solfeggio', freq: 432.0, sub: 'Universal tuning' },
];

// ─── MOPS payload shapes (see backend/app/api/v1/endpoints/mops.py) ──────
interface MopsWindow {
  '1s'?: number;
  '10s'?: number;
  '60s'?: number;
  '5m'?: number;
}
interface MopsAverages {
  scalar_pulses?: MopsWindow;
  mantras?: MopsWindow;
  crystals?: MopsWindow;
  divination?: MopsWindow;
  tuning?: MopsWindow;
}

// ─── Journey payload shape (see /api/v1/operator/journey/status) ─────────
interface JourneyCharacter {
  element?: string;
  name?: string;
  role?: string;
  frequency?: number;
}
interface JourneyStatus {
  active?: boolean;
  current_stage?: string;
  stage_index?: number;
  character?: JourneyCharacter;
}

// Minimal narrowing for the WS `sessions` map (typed as Record<string, unknown>).
interface SessionLike {
  id?: string;
  name?: string;
  intention?: string;
  status?: string;
}
function isSessionLike(v: unknown): v is SessionLike {
  return typeof v === 'object' && v !== null;
}

// ─── Formatting helpers ───────────────────────────────────────────────────
function formatRate(n: number | undefined, digits = 2): string {
  if (n == null || !isFinite(n)) return '0.00';
  const abs = Math.abs(n);
  if (abs >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (abs >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return (n / 1e3).toFixed(2) + 'k';
  return n.toFixed(digits);
}

function pickWindow(w: MopsWindow | undefined): number {
  // Prefer the 60s rolling average for a calm, stable readout; fall back
  // through shorter windows so we always show something.
  return w?.['60s'] ?? w?.['10s'] ?? w?.['1s'] ?? w?.['5m'] ?? 0;
}

// ─── Shared glass panel style (matches the UI overhaul's header/footer) ───
// rgba(20,10,30,0.7) + blur(12px) — the established vajra glassmorphism token.
const GLASS_PANEL =
  'rounded-2xl border border-purple-400/15 shadow-[0_8px_40px_rgba(0,0,0,0.45)] ' +
  'backdrop-blur-[12px] bg-[rgba(20,10,30,0.7)] text-purple-50';

const LABEL = 'text-[10px] uppercase tracking-[0.18em] text-purple-300/60 font-semibold';
const VALUE_MONO = 'font-mono text-white tabular-nums';

export default function ScalarTab(): React.ReactElement {
  const vizRef = useRef<ScalarVizAPI>(null);

  // ── mode (controlled — drives the visualizer) ──────────────────────
  const [mode, setMode] = useState<ScalarMode>('living');

  // ── audio store ────────────────────────────────────────────────────
  const {
    frequency,
    volume,
    prayerBowlMode,
    isPlaying,
    audioStatus,
    errorMessage,
    setFrequency,
    setVolume,
    setPrayerBowlMode,
    generateAudio,
    playAudio,
    stopAudio,
  } = useAudioStore();

  // ── websocket: scalar / crystal / sessions / link / slow-data ──────
  // mopsAverages + journeyStatus come from the backend's 10s slow-data
  // broadcast (MOPS_AVERAGES / JOURNEY_STATUS) and replace HTTP polling.
  const {
    scalarStatus,
    crystalStatus,
    sessions,
    isConnected,
    mopsAverages,
    journeyStatus,
  } = useWebSocketStable();

  // ── local UI state ─────────────────────────────────────────────────
  // MOPS + journey derive from the WebSocket slow-data broadcasts. The
  // *Fallback states are seeded by a one-shot HTTP fetch on mount so the
  // UI isn't blank while waiting for the first 10s WS push.
  const [mopsFallback, setMopsFallback] = useState<MopsAverages | null>(null);
  const [journeyFallback, setJourneyFallback] = useState<JourneyStatus | null>(null);
  const mopsWs = mopsAverages as MopsAverages | null;
  const journeyWs = journeyStatus as JourneyStatus | null;
  const mops = mopsWs ?? mopsFallback;
  const journey =
    journeyWs?.active
      ? journeyWs
      : journeyWs === null
        ? journeyFallback
        : null;
  const [intention, setIntention] = useState('');
  const [busy, setBusy] = useState<'generate' | 'play' | 'stop' | null>(null);

  const element = journey?.character?.element;
  const elementKey =
    element && element in ELEMENT_EMOJIS ? element : 'Cosmic';

  // ── refs to read latest values inside stable callbacks ─────────────
  const elementKeyRef = useRef(elementKey);
  elementKeyRef.current = elementKey;

  // ───────────────────────────────────────────────────────────────────
  // EFFECT: one-shot initial MOPS fetch (fallback while waiting for the
  // first 10s WS push). Subsequent updates arrive via WebSocket.
  // ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const fetchOnce = async () => {
      try {
        const res = await fetch('/api/v1/mops/current');
        if (!res.ok) return;
        const data = (await res.json()) as {
          status?: string;
          mops?: MopsAverages;
        };
        if (!cancelled && data.mops) setMopsFallback(data.mops);
      } catch {
        /* silent — telemetry is best-effort */
      }
    };
    fetchOnce();
    return () => {
      cancelled = true;
    };
  }, []);

  // ───────────────────────────────────────────────────────────────────
  // EFFECT: one-shot initial journey fetch (fallback while waiting for
  // the first 10s WS push). Subsequent updates arrive via WebSocket.
  // Element-mood recoloring is handled by the dedicated effect below.
  // ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const fetchOnce = async () => {
      try {
        const res = await fetch('/api/v1/operator/journey/status');
        if (!res.ok) return;
        const data = (await res.json()) as JourneyStatus;
        if (cancelled) return;
        setJourneyFallback(data.active ? data : null);
      } catch {
        /* silent */
      }
    };
    fetchOnce();
    return () => {
      cancelled = true;
    };
  }, []);

  // Set the initial element mood once the visualizer mounts / element resolves.
  useEffect(() => {
    if (element) vizRef.current?.setElementMood(element);
  }, [element]);

  // ───────────────────────────────────────────────────────────────────
  // EFFECT: crystal broadcast → harmonic layer + ceremony ripple
  // ───────────────────────────────────────────────────────────────────
  const prevCrystalActive = useRef(false);
  useEffect(() => {
    const active = !!crystalStatus?.active;
    if (active && !prevCrystalActive.current) {
      const hue = ELEMENT_HUES[elementKeyRef.current] ?? 280;
      vizRef.current?.triggerCrystalLayer(hue);
    }
    prevCrystalActive.current = active;
  }, [crystalStatus]);

  // ───────────────────────────────────────────────────────────────────
  // EFFECT: new blessing session → ripple + merit particles; healing → mood
  // ───────────────────────────────────────────────────────────────────
  const seenSessionsRef = useRef<Set<string>>(new Set());
  const healingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const entries = Object.values(sessions).filter(isSessionLike);
    const seen = seenSessionsRef.current;

    // First-seed: don't fire a burst for sessions that were already live
    // when the tab opened — only react to genuinely new arrivals.
    if (seen.size === 0 && entries.length > 0) {
      for (const s of entries) {
        if (s.id) seen.add(s.id);
      }
      // Still honor healing mood for a session that was already active.
      const hasHealing = entries.some((s) =>
        `${s.name ?? ''} ${s.intention ?? ''}`.toLowerCase().includes('heal'),
      );
      if (hasHealing) vizRef.current?.setHealingMood(true);
      return;
    }

    for (const s of entries) {
      if (!s.id || seen.has(s.id)) continue;
      seen.add(s.id);
      // Each new blessing session = a ripple from center + merit burst.
      vizRef.current?.triggerBlessingRipple(
        ELEMENT_HUES[elementKeyRef.current],
      );
      const text = `${s.name ?? ''} ${s.intention ?? ''}`.toLowerCase();
      if (text.includes('heal')) {
        vizRef.current?.setHealingMood(true);
        if (healingTimeoutRef.current) clearTimeout(healingTimeoutRef.current);
        healingTimeoutRef.current = setTimeout(() => {
          vizRef.current?.setHealingMood(false);
          healingTimeoutRef.current = null;
        }, 30_000);
      }
    }
  }, [sessions]);

  // Cleanup healing timer on unmount.
  useEffect(() => {
    return () => {
      if (healingTimeoutRef.current) clearTimeout(healingTimeoutRef.current);
    };
  }, []);

  // ───────────────────────────────────────────────────────────────────
  // Handlers
  // ───────────────────────────────────────────────────────────────────
  const handleSendBlessing = useCallback(() => {
    // Manual practice: ripple + a small burst of merit particles, tinted by
    // the current element. The visual IS the feedback — no backend roundtrip
    // is required, so this works even with the audio engine silent.
    const hue = ELEMENT_HUES[elementKeyRef.current] ?? 280;
    vizRef.current?.triggerBlessingRipple(hue);
    for (let i = 0; i < 5; i++) vizRef.current?.triggerMeritParticle(hue);
    // Clear the field after offering — the intention has been released.
    if (intention.trim()) setIntention('');
  }, [intention]);

  const handleGenerate = useCallback(async () => {
    setBusy('generate');
    try {
      await generateAudio();
    } finally {
      setBusy(null);
    }
  }, [generateAudio]);

  const handlePlay = useCallback(async () => {
    setBusy('play');
    try {
      await playAudio();
    } finally {
      setBusy(null);
    }
  }, [playAudio]);

  const handleStop = useCallback(async () => {
    setBusy('stop');
    try {
      await stopAudio();
    } finally {
      setBusy(null);
    }
  }, [stopAudio]);

  // ── derived display values ─────────────────────────────────────────
  const scalarRate = scalarStatus?.rate ?? 0;
  const scalarPulses = pickWindow(mops?.scalar_pulses);
  const mantras = pickWindow(mops?.mantras);
  const crystals = pickWindow(mops?.crystals);
  const divination = pickWindow(mops?.divination);

  const statusTone =
    audioStatus === 'error'
      ? 'text-rose-300 border-rose-400/30 bg-rose-950/40'
      : isPlaying
        ? 'text-cyan-300 border-cyan-400/30 bg-cyan-950/40 animate-pulse'
        : audioStatus === 'generating'
          ? 'text-amber-300 border-amber-400/30 bg-amber-950/40 animate-pulse'
          : 'text-purple-300/70 border-purple-400/15 bg-purple-950/30';

  const statusLabel =
    audioStatus === 'error'
      ? 'error'
      : isPlaying
        ? 'playing'
        : audioStatus === 'generating'
          ? 'generating'
          : audioStatus === 'generated'
            ? 'ready'
            : 'idle';

  return (
    <div className="relative w-full h-full overflow-hidden bg-[#08081a]">
      {/* ── Centerpiece: the Living Mandala ─────────────────────────── */}
      <div className="absolute inset-0">
        <ScalarWaveVisualizer
          ref={vizRef}
          mode={mode}
          initialMode="living"
          showModeSelector={false}
        />
      </div>

      {/* Soft radial vignette to focus the center and lift panel legibility */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at center, rgba(8,8,26,0) 35%, rgba(8,8,26,0.55) 100%)',
        }}
      />

      {/* ── Top-left: MOPS readout ──────────────────────────────────── */}
      <div
        className={`absolute top-3 left-3 z-20 w-[230px] p-3.5 ${GLASS_PANEL}`}
        style={{ animation: 'scalarFadeIn 0.8s ease-out' }}
      >
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-[11px] font-semibold tracking-[0.22em] text-purple-200/90 uppercase">
            MOPS
          </span>
          <span
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${
              isConnected
                ? 'text-emerald-300 border-emerald-400/30 bg-emerald-950/40'
                : 'text-rose-300 border-rose-400/30 bg-rose-950/40'
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isConnected ? 'bg-emerald-400' : 'bg-rose-400'
              }`}
            />
            {isConnected ? 'live' : 'offline'}
          </span>
        </div>

        <div className="space-y-1.5">
          <ReadoutRow
            label="Scalar"
            value={formatRate(scalarPulses)}
            unit="/s"
            accent="text-cyan-300"
          />
          <ReadoutRow
            label="Mantras"
            value={formatRate(mantras, 1)}
            unit="/s"
            accent="text-amber-300"
          />
          <ReadoutRow
            label="Crystals"
            value={formatRate(crystals)}
            unit="/s"
            accent="text-yellow-200"
          />
          <ReadoutRow
            label="Divination"
            value={formatRate(divination)}
            unit="/hr"
            accent="text-fuchsia-300"
          />
          <div className="pt-1.5 mt-1.5 border-t border-purple-400/10">
            <ReadoutRow
              label="Carrier λ"
              value={Number(scalarRate).toFixed(2)}
              unit="Hz"
              accent="text-indigo-300"
            />
          </div>
        </div>
      </div>

      {/* ── Top-right: intention + element badge ────────────────────── */}
      <div
        className="absolute top-3 right-3 z-20 w-[280px] p-3.5"
        style={{ animation: 'scalarFadeIn 0.8s ease-out 0.1s both' }}
      >
        <div className={`p-3 ${GLASS_PANEL}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold tracking-[0.22em] text-purple-200/90 uppercase">
              Intention
            </span>
            {journey?.character?.name && (
              <span className="text-[10px] text-purple-300/70 font-mono truncate max-w-[120px]">
                {journey.character.name}
              </span>
            )}
          </div>
          <textarea
            value={intention}
            onChange={(e) => setIntention(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                e.preventDefault();
                handleSendBlessing();
              }
            }}
            placeholder="May all beings be free from suffering…"
            rows={2}
            className="w-full bg-black/30 border border-purple-400/20 rounded-lg px-2.5 py-1.5 text-[12px] text-purple-50 placeholder-purple-300/40 focus:border-purple-300/50 focus:outline-none focus:ring-1 focus:ring-purple-300/30 resize-none transition-colors"
          />
          <button
            onClick={handleSendBlessing}
            className="mt-2 w-full px-3 py-1.5 rounded-lg text-[11px] font-semibold tracking-wider uppercase bg-gradient-to-r from-purple-600/80 to-fuchsia-600/80 hover:from-purple-500 hover:to-fuchsia-500 text-white border border-purple-300/30 shadow-[0_0_18px_rgba(168,85,247,0.35)] transition-all duration-300 active:scale-[0.98]"
          >
            ✦ Send as Blessing
          </button>
          <p className="mt-1.5 text-[9px] text-purple-300/40 text-center font-mono">
            ⌘/Ctrl + Enter
          </p>
        </div>

        {/* Element badge (character journey) */}
        <div className="mt-2 flex justify-end">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold border bg-[rgba(20,10,30,0.7)] backdrop-blur-[12px] border-purple-300/25"
            style={{ color: `hsl(${ELEMENT_HUES[elementKey]}, 80%, 72%)` }}
            title={
              element && element in ELEMENT_EMOJIS
                ? `Active element: ${element}`
                : 'No active journey — Cosmic palette'
            }
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{
                background: `hsl(${ELEMENT_HUES[elementKey]}, 85%, 60%)`,
                boxShadow: `0 0 8px hsl(${ELEMENT_HUES[elementKey]}, 85%, 60%)`,
              }}
            />
            {element && element in ELEMENT_EMOJIS
              ? `${ELEMENT_EMOJIS[element]} ${element}`
              : '✦ Cosmic'}
          </span>
        </div>
      </div>

      {/* ── Bottom-left: audio controls + mode switcher ─────────────── */}
      <div
        className="absolute bottom-3 left-3 z-20 w-[340px] p-4"
        style={{ animation: 'scalarFadeIn 0.8s ease-out 0.2s both' }}
      >
        <div className={`${GLASS_PANEL} p-3.5`}>
          {/* Mode switcher */}
          <div className="mb-3">
            <div className={LABEL + ' mb-1.5'}>Mode</div>
            <div className="flex flex-wrap gap-1">
              {MODE_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  onClick={() => setMode(opt.key)}
                  title={opt.hint}
                  className={`px-2 py-1 rounded-md text-[10px] font-semibold tracking-wide uppercase transition-all duration-200 ${
                    mode === opt.key
                      ? 'bg-purple-600/80 text-white border border-purple-300/40 shadow-[0_0_10px_rgba(168,85,247,0.4)]'
                      : 'bg-white/5 text-purple-200/60 border border-transparent hover:bg-white/10 hover:text-purple-100'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Frequency */}
          <div className="mb-2.5">
            <div className="flex items-baseline justify-between mb-1">
              <span className={LABEL}>Frequency</span>
              <span className={`${VALUE_MONO} text-cyan-300 text-sm`}>
                {Number(frequency).toFixed(2)}
                <span className="text-[9px] text-cyan-300/60 ml-1">Hz</span>
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={1000}
              step={0.01}
              value={Math.min(1000, Math.max(1, frequency))}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full accent-purple-400 h-1 cursor-pointer"
            />
            <div className="mt-1.5 flex flex-wrap gap-1">
              {FREQ_PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setFrequency(p.freq)}
                  title={p.sub}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono border transition-colors ${
                    Math.abs(Number(frequency) - p.freq) < 0.05
                      ? 'bg-purple-600/40 text-purple-100 border-purple-300/40'
                      : 'bg-black/20 text-purple-300/60 border-purple-400/15 hover:text-purple-100 hover:border-purple-300/30'
                  }`}
                >
                  {p.label} {p.freq}
                </button>
              ))}
            </div>
          </div>

          {/* Volume */}
          <div className="mb-2.5">
            <div className="flex items-baseline justify-between mb-1">
              <span className={LABEL}>Volume</span>
              <span className={`${VALUE_MONO} text-purple-200 text-xs`}>
                {Math.round(volume * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              className="w-full accent-fuchsia-400 h-1 cursor-pointer"
            />
          </div>

          {/* Prayer bowl toggle */}
          <label className="flex items-center justify-between mb-3 cursor-pointer select-none">
            <span className={LABEL}>Prayer Bowl</span>
            <span
              onClick={() => setPrayerBowlMode(!prayerBowlMode)}
              className={`relative inline-flex items-center w-9 h-5 rounded-full transition-colors ${
                prayerBowlMode ? 'bg-purple-500/70' : 'bg-white/10'
              }`}
            >
              <span
                className={`inline-block w-3.5 h-3.5 rounded-full bg-white shadow transform transition-transform ${
                  prayerBowlMode ? 'translate-x-4' : 'translate-x-1'
                }`}
              />
            </span>
          </label>

          {/* Transport */}
          <div className="grid grid-cols-3 gap-1.5">
            <button
              onClick={handleGenerate}
              disabled={busy !== null}
              className="px-2 py-1.5 rounded-md text-[10px] font-bold tracking-wide uppercase bg-white/5 hover:bg-white/10 text-purple-100 border border-purple-400/20 transition-colors disabled:opacity-40"
            >
              {busy === 'generate' ? '…' : 'Gen'}
            </button>
            <button
              onClick={handlePlay}
              disabled={busy !== null || isPlaying}
              className="px-2 py-1.5 rounded-md text-[10px] font-bold tracking-wide uppercase bg-gradient-to-r from-emerald-600/70 to-teal-600/70 hover:from-emerald-500 hover:to-teal-500 text-white border border-emerald-300/30 transition-colors disabled:opacity-40"
            >
              {busy === 'play' ? '…' : 'Play'}
            </button>
            <button
              onClick={handleStop}
              disabled={busy !== null || !isPlaying}
              className="px-2 py-1.5 rounded-md text-[10px] font-bold tracking-wide uppercase bg-gradient-to-r from-rose-600/70 to-red-600/70 hover:from-rose-500 hover:to-red-500 text-white border border-rose-300/30 transition-colors disabled:opacity-40"
            >
              {busy === 'stop' ? '…' : 'Stop'}
            </button>
          </div>

          {/* Status line */}
          <div className="mt-2.5 flex items-center justify-between">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border ${statusTone}`}
            >
              <span className="w-1 h-1 rounded-full bg-current" />
              {statusLabel}
            </span>
            {errorMessage && (
              <span className="text-[9px] text-rose-300/80 truncate max-w-[140px]">
                {errorMessage}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Inline keyframes for the panel fade-in (scoped, no global pollution) */}
      <style>{`
        @keyframes scalarFadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

// ─── Small presentational helper: label / value / unit row ────────────────
function ReadoutRow({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string;
  unit: string;
  accent: string;
}) {
  return (
    <div className="flex items-baseline justify-between">
      <span className="text-[10px] text-purple-300/60 font-medium">{label}</span>
      <span className="font-mono text-[11px] tabular-nums">
        <span className={accent + ' font-semibold'}>{value}</span>
        <span className="text-purple-300/40 ml-0.5 text-[9px]">{unit}</span>
      </span>
    </div>
  );
}
