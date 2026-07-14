/**
 * PracticeDetail — single-practice view for `/practices/:id`.
 *
 * Surfaces the full mantra (Sanskrit + transliteration + English
 * meaning), Start/Stop recitation controls, a 108-bead mala counter
 * with a live visual bead-progress ring, the session timer, a
 * dedication/intention text input, and a "View Visualization" button
 * that routes the user to the 3D Visualizer tab (`/practice/visualizers`).
 *
 * Data flow:
 *  - Resolves the practice locally from `practicesCatalog` (the shared
 *    curated seed list). If the route id doesn't match any practice,
 *    renders a 404-style fallback inside the page rather than blowing
 *    up the whole layout.
 *  - POST `/api/v1/practices/{id}/start` and `/stop` to drive the
 *    recitation. We optimistically toggle `running` locally and roll
 *    back on error.
 *  - GET `/api/v1/practices/{id}/status` on mount AND every 2 seconds
 *    while the session is running, so the bead count + mala count +
 *    total count stay in sync with the backend.
 *  - The session timer is purely client-side (started on first Start,
 *    reset on Stop). It is not authoritative — the backend is.
 *
 * Visual system:
 *  - The practice's color is the primary accent throughout — top bar,
 *    icon halo, button gradients, bead ring stroke, focus glow.
 *  - Bead ring is an SVG circle whose `stroke-dashoffset` is computed
 *    from `count % 108`. Smooth via CSS transition on stroke-dashoffset.
 *  - Reduced-motion respect: all motion lives on transform/opacity and
 *    the global prefers-reduced-motion rule zeroes transition durations.
 *
 * @component
 * @route /practices/:id
 */
import React, { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import {
  Button,
  Card,
  Input,
  Tag,
  Statistic,
  Progress,
  Space,
  Typography,
  Result,
  Tooltip,
  Alert,
  Divider,
  Skeleton,
  Switch,
  Collapse,
  message,
} from 'antd';
import {
  ArrowLeft,
  Play,
  Square,
  RotateCcw,
  Eye,
  Heart,
  Sparkles,
  Clock,
  CircleDot,
  Activity,
  Compass,
  Loader2,
  CheckCircle2,
  Volume2,
  VolumeX,
  Flame,
  CalendarCheck,
  BookText,
} from 'lucide-react';
import { audioFeedback } from '../../utils/audioFeedback';
import { apiUrl } from '../../utils/api';
import { getPracticeById, type Practice } from './practicesCatalog';
import { getDeityVisualization } from '../../lib/deityVisualizations';
import SadhanaVisualization from './SadhanaVisualization';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';
import { useAmbientBowl } from '../../hooks/useAmbientBowl';
import {
  appendJournal,
  computeCurrentStreak,
  readJournal,
  readStreaks,
  recordSession,
  todayStr,
  writeStreaks,
  type JournalEntry,
  type StreakMap,
} from '../../utils/practiceStorage';
import type { PracticeStatus } from '../../types';
const TaraGreenLotusLazy = React.lazy(() => import('../3D/TaraGreenLotus'));
const ZhuntiMandalaLazy = React.lazy(() => import('../3D/ZhuntiMandala'));
const MedicineBuddhaHealingLazy = React.lazy(() => import('../3D/MedicineBuddhaHealing'));
const SacredGeometryLazy = React.lazy(() => import('../3D/SacredGeometry'));
const SacredMandalaLazy = React.lazy(() => import('../3D/SacredMandala'));

const { Title, Text, Paragraph } = Typography;

/** Total beads on a traditional mala — a complete cycle. */
const MALA_BEADS = 108;

/**
 * Shared prop contract of the three wired-in 3D visualization
 * components (TaraGreenLotus / ZhuntiMandala / MedicineBuddhaHealing).
 */
type Complexity = 'simple' | 'medium' | 'complex';

interface VizComponentProps {
  audioSpectrum: number[];
  isPlaying: boolean;
  frequency: number;
  complexity?: Complexity;
}

/**
 * Map a practice id (underscore form, matches knowledge/practices/*.json)
 * to its dedicated 3D visualization component. Covers all 9 practices in
 * the catalog; entries without a one-of-a-kind scene reuse a thematic
 * stand-in (same prop contract — these are R3F components consuming
 * audio spectrum / play state / frequency).
 *
 *  - 88 Buddhas        → SacredGeometry (multi-pattern field)
 *  - Green/White Tara  → TaraGreenLotus
 *  - Zhunti            → ZhuntiMandala
 *  - Medicine Buddha   → MedicineBuddhaHealing
 *  - Vajrasattva       → MedicineBuddhaHealing (purification by light)
 *  - Amitabha          → SacredMandala (Pure Land resonance)
 *  - Avalokiteshvara   → TaraGreenLotus (compassionate lotus seat)
 *  - Heart Sutra       → ZhuntiMandala (pure-awareness mandala)
 */
type LazyVizComponent = React.LazyExoticComponent<React.ComponentType<VizComponentProps>>;

const PRACTICE_VISUALIZATIONS: Record<string, LazyVizComponent> = {
  green_tara: TaraGreenLotusLazy as unknown as LazyVizComponent,
  white_tara: TaraGreenLotusLazy as unknown as LazyVizComponent,
  zhunti: ZhuntiMandalaLazy as unknown as LazyVizComponent,
  medicine_buddha: MedicineBuddhaHealingLazy as unknown as LazyVizComponent,
  vajrasattva: MedicineBuddhaHealingLazy as unknown as LazyVizComponent,
  amitabha: SacredMandalaLazy as unknown as LazyVizComponent,
  avalokiteshvara: TaraGreenLotusLazy as unknown as LazyVizComponent,
  heart_sutra: ZhuntiMandalaLazy as unknown as LazyVizComponent,
  '88_buddhas': SacredGeometryLazy as unknown as LazyVizComponent,
};

/** Optional props — App.tsx passes the live WS practice map for real-time updates. */
export interface PracticeDetailProps {
  wsPractices?: Record<string, PracticeStatus>;
}

/** Status payload the backend returns from /status. */
interface PracticeStatusResponse {
  running: boolean;
  count: number;
  mala_count: number;
}

/**
 * Start response — backend returns `{status: "started", session: {...}}`
 * where `session` is the full status dict (including `practice_id`,
 * which serves as the session identifier since each practice tracks at
 * most one running session). Legacy/offline paths may still return the
 * flat `{session_id}` shape, so we tolerate both.
 */
interface StartResponse {
  status: string;
  session?: { practice_id?: string };
  session_id?: string;
}

/**
 * Stop response — backend returns `{status: "stopped", session: {...}}`
 * with `session.total_recited` carrying the final tally. Older shapes
 * surfaced `total_count` at the top level; tolerate both.
 */
interface StopResponse {
  status: string;
  session?: { total_recited?: number };
  total_count?: number;
}

/**
 * BeadRing — an SVG ring that visualizes progress around the 108-bead
 * mala. The filled arc grows clockwise from 12 o'clock.
 *
 * Props:
 *  - count: total recitations so far (mod 108 controls the arc fill).
 *  - color: stroke color (the practice's accent).
 *  - size: diameter in pixels.
 */
interface BeadRingProps {
  count: number;
  color: string;
  colorRgb: string;
  size?: number;
}

const BeadRing: React.FC<BeadRingProps> = ({
  count,
  color,
  colorRgb,
  size = 220,
}) => {
  const progress = ((count % MALA_BEADS) / MALA_BEADS) * 100;
  // SVG circle math: r=46, C=2πr≈289.033
  const radius = 46;
  const circumference = 2 * Math.PI * radius;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size, maxWidth: '60vw', maxHeight: '60vw' }}
    >
      {/* Outer halo — soft glow tint */}
      <div
        className="absolute inset-0 rounded-full blur-2xl opacity-40"
        style={{ background: `radial-gradient(circle, rgba(${colorRgb}, 0.55), transparent 70%)` }}
        aria-hidden
      />
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        className="relative transform -rotate-90"
        aria-label={`${count} recitations on a 108-bead mala`}
      >
        {/* Track */}
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={`rgba(${colorRgb}, 0.15)`}
          strokeWidth="4"
        />
        {/* Progress arc */}
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (progress / 100) * circumference}
          style={{ transition: 'stroke-dashoffset 320ms ease-out' }}
        />
        {/* Tick marks — 108 dots around the ring */}
        {Array.from({ length: MALA_BEADS }).map((_, i) => {
          const angle = (i / MALA_BEADS) * 360;
          const filled = i < (count % MALA_BEADS);
          // Place the dot just inside the ring on a tiny circle.
          const dotR = 48.5;
          const rad = (angle - 90) * (Math.PI / 180);
          const cx = 50 + dotR * Math.cos(rad);
          const cy = 50 + dotR * Math.sin(rad);
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={0.4}
              fill={filled ? color : `rgba(${colorRgb}, 0.25)`}
            />
          );
        })}
      </svg>
      {/* Center label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="text-4xl font-bold tabular-nums"
          style={{ color, textShadow: `0 0 20px rgba(${colorRgb}, 0.5)` }}
        >
          {count % MALA_BEADS}
        </div>
        <Text type="secondary" className="!text-xs !font-mono !tracking-wider">
          / {MALA_BEADS} beads
        </Text>
      </div>
    </div>
  );
};

/** Format ms → HH:MM:SS for the session timer. */
function formatElapsed(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return [h, m, s].map((n) => String(n).padStart(2, '0')).join(':');
}

/**
 * Hook: ticks a state counter every `intervalMs` while `enabled`.
 * Used to keep the session timer live without forcing a re-render of
 * the whole detail tree.
 */
function useInterval(enabled: boolean, intervalMs: number): number {
  const [tick, setTick] = useState<number>(0);
  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => {
      setTick((t) => t + 1);
    }, intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs]);
  return tick;
}

/**
 * Triple of Web Audio nodes backing the ambient bowl drone. The
 * `useAmbientBowl` hook owns the lifecycle; we just call start/stop
 * from a useEffect gated on `running`/`enableAmbient`/`enableTts`.
 */

export default function PracticeDetail({
  wsPractices,
}: PracticeDetailProps = {}): React.ReactElement {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const practice: Practice | undefined = useMemo(() => getPracticeById(id), [id]);

  /** In-page 3D visualization toggle (replaces navigation to /practice/visualizers). */
  const [showVisualization, setShowVisualization] = useState<boolean>(false);

  /** Live recitation state. */
  const [running, setRunning] = useState<boolean>(false);
  const [count, setCount] = useState<number>(0);
  const [malaCount, setMalaCount] = useState<number>(0);
  const [sessionId, setSessionId] = useState<string | null>(null);

  /** UI state. */
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [intention, setIntention] = useState<string>('');
  const [sessionStartedAt, setSessionStartedAt] = useState<number | null>(null);
  const [enableTts, setEnableTts] = useState<boolean>(true);

  // Per-practice streak (keyed by practiceId, persists to localStorage).
  const [streaks, setStreaks] = useState<StreakMap>({});

  // Post-session reflection input and the user's journal history.
  const [reflection, setReflection] = useState<string>('');
  const [journal, setJournal] = useState<JournalEntry[]>([]);

  // Ambient bowl drone toggle (drives the AudioContext oscillator).
  const [enableAmbient, setEnableAmbient] = useState<boolean>(false);

  /**
   * Audio + live-practice state from the shared hooks. The 3D viz
   * components consume `audioSpectrum` / `isPlaying` / `frequency`
   * directly; `wsPractices` (prop) is preferred for live session
   * updates but we fall back to the local hook value when App.tsx
   * hasn't wired the prop through yet.
   */
  const wsHook = useWebSocketStable();
  const audioSpectrum = wsHook.audioSpectrum;
  const { isPlaying, frequency } = useAudioStore();
  const livePractices = wsPractices ?? wsHook.practices;

  // Re-render every second while running so the timer ticks.
  useInterval(running, 1000);
  const elapsedMs = sessionStartedAt ? Date.now() - sessionStartedAt : 0;

  // Hydrate streak + journal state from localStorage once on mount.
  useEffect(() => {
    setStreaks(readStreaks());
    setJournal(readJournal());
  }, []);

  /**
   * When the backend pushes a fresher session state via WebSocket
   * (PRACTICE_RECITED / PRACTICE_STARTED / etc.), fold it into local
   * UI state so the bead ring + counters stay in sync without polling.
   */
  useEffect(() => {
    if (!id) return;
    const live = livePractices[id];
    if (!live) return;
    setRunning(Boolean(live.running));
    setCount(typeof live.total_recited === 'number' ? live.total_recited : 0);
    setMalaCount(typeof live.mala_count === 'number' ? live.mala_count : 0);
  }, [id, livePractices]);

  /**
   * TTS audio playback for the practice mantra.
   *
   * The backend exposes `/api/v1/tts/stream` (edge-tts MP3 stream).
   * We fetch the stream, wrap it in a blob URL, and play through an
   * HTMLAudioElement so each `PRACTICE_RECITED` WS push speaks the
   * mantra aloud in the browser. Gated by `enableTts` so the user can
   * mute via the existing switch without breaking the recitation loop.
   *
   * Silent failure: audio is enhancement, not critical — any fetch /
   * playback error is swallowed so recitation stays uninterrupted.
   */
  const mantraAudioRef = useRef<HTMLAudioElement | null>(null);
  const lastSpokenCountRef = useRef<number>(0);

  /**
   * Ambient bowl drone — a held sine-wave oscillator at the practice's
   * `frequencyHz`, started/stopped in lockstep with TTS playback and
   * the practice toggle. Owned by the shared `useAmbientBowl` hook so
   * the same Web Audio plumbing backs both the practice and 88-Buddhas
   * pages.
   */
  const ambient = useAmbientBowl();

  /**
   * Drive ambient bowl start/stop from `running` + `enableAmbient` +
   * `enableTts`. The drone plays only while the practice is running,
   * the toggle is on, and TTS is enabled (per spec: "while TTS is
   * speaking"). It tears down cleanly on unmount.
   */
  useEffect(() => {
    const desired = running && enableAmbient && enableTts && id === practice?.id;
    const freq = practice?.frequencyHz;
    if (desired && freq) {
      ambient.start(freq);
    } else {
      ambient.stop();
    }
    return () => {
      ambient.stop();
    };
  }, [running, enableAmbient, enableTts, id, practice, ambient]);

  /** Clean up any in-flight audio on unmount. */
  useEffect(() => {
    return () => {
      if (mantraAudioRef.current) {
        mantraAudioRef.current.pause();
        mantraAudioRef.current = null;
      }
      ambient.stop();
    };
  }, [ambient]);

  /** Speak the practice mantra on each new recitation. */
  useEffect(() => {
    if (!id || !enableTts) return;
    const live = livePractices[id];
    if (!live) return;
    const total = typeof live.total_recited === 'number' ? live.total_recited : 0;
    if (total <= lastSpokenCountRef.current) return;
    lastSpokenCountRef.current = total;

    const mantraText = practice?.mantra ?? practice?.transliteration ?? practice?.name;
    if (!mantraText) return;

    if (mantraAudioRef.current) {
      mantraAudioRef.current.pause();
      mantraAudioRef.current = null;
    }

    void (async () => {
      try {
        const res = await fetch(apiUrl('/tts/stream'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: mantraText,
            role: 'buddhist_chant',
            rate: '-20%',
          }),
        });
        if (!res.ok) return;
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        mantraAudioRef.current = audio;
        audio.onended = () => {
          URL.revokeObjectURL(url);
          mantraAudioRef.current = null;
        };
        audio.onerror = () => {
          URL.revokeObjectURL(url);
          mantraAudioRef.current = null;
        };
        await audio.play();
      } catch {
        // Silent fail — audio is enhancement, not critical.
      }
    })();
  }, [id, enableTts, livePractices, practice]);

  /** Status poll ref so we can cancel from cleanup. */
  const statusPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /** Pull the live status from the backend. Falls back silently if offline. */
  const fetchStatus = useCallback(async (): Promise<void> => {
    if (!id) return;
    try {
      const res = await fetch(apiUrl(`/practices/${id}/status`));
      if (!res.ok) return;
      const data: PracticeStatusResponse = await res.json();
      setRunning(Boolean(data.running));
      setCount(typeof data.count === 'number' ? data.count : 0);
      setMalaCount(typeof data.mala_count === 'number' ? data.mala_count : 0);
    } catch {
      // Backend offline — keep the local state we already have.
    } finally {
      setLoading(false);
    }
  }, [id]);

  /** Initial fetch + start the status poll. */
  useEffect(() => {
    void fetchStatus();

    if (statusPollRef.current) clearInterval(statusPollRef.current);
    statusPollRef.current = setInterval(() => {
      void fetchStatus();
    }, 2000);

    return () => {
      if (statusPollRef.current) {
        clearInterval(statusPollRef.current);
        statusPollRef.current = null;
      }
    };
  }, [fetchStatus]);

  /** Stop the poll if the session is idle (saves battery). */
  useEffect(() => {
    if (!running && statusPollRef.current) {
      clearInterval(statusPollRef.current);
      statusPollRef.current = null;
    } else if (running && !statusPollRef.current) {
      statusPollRef.current = setInterval(() => {
        void fetchStatus();
      }, 2000);
    }
  }, [running, fetchStatus]);

  /** Drive the Start/Stop button. */
  const handleToggle = useCallback(async (): Promise<void> => {
    if (!practice) return;
    setActionLoading(true);
    setError(null);
    audioFeedback.playTelemetry();

    try {
      if (running) {
        const res = await fetch(apiUrl(`/practices/${practice.id}/stop`), {
          method: 'POST',
        });
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data: StopResponse = await res.json();
        const finalTotal = data.session?.total_recited ?? data.total_count;
        if (typeof finalTotal === 'number') {
          setCount(finalTotal);
        }
        setRunning(false);
        setSessionStartedAt(null);
        audioFeedback.playSuccess();

        // Ambient drone cleanup is owned by the [running, enableAmbient,
// enableTts] useEffect above; reflection prompt is rendered in JSX.
        setReflection('');
      } else {
        const res = await fetch(apiUrl(`/practices/${practice.id}/start`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            intention: intention || undefined,
            dedication: intention || undefined,
            enable_tts: enableTts,
          }),
        });
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        const data: StartResponse = await res.json();
        setRunning(true);
        setSessionStartedAt(Date.now());
        lastSpokenCountRef.current = 0;
        const resolvedSessionId = data.session?.practice_id ?? data.session_id;
        if (resolvedSessionId) setSessionId(resolvedSessionId);
        audioFeedback.playSuccess();

        // Record today on the streak ledger + fire the milestone toast.
        const today = todayStr();
        const prevDates = streaks[practice.id] ?? [];
        const prevStreak = computeCurrentStreak(prevDates, today);
        const nextDates = recordSession(streaks, practice.id, today);
        const nextStreak = computeCurrentStreak(nextDates, today);
        setStreaks({ ...streaks, [practice.id]: nextDates });
        const totalSessions = nextDates.length;
        const milestoneDays = [3, 7, 21, 30, 49, 100, 108, 365, 1000];
        if (nextStreak > prevStreak && milestoneDays.includes(nextStreak)) {
          message.success(
            `🎉 ${nextStreak}-day streak! ${totalSessions} sessions completed!`,
            4,
          );
        }
      }
    } catch (err) {
      // Local optimistic fallback — flip the UI even if the backend
      // is down so the user can still practice with their own mala.
      setError(
        err instanceof Error
          ? `Couldn't reach the practice server (${err.message}). Continuing locally — counts will not be saved.`
          : "Couldn't reach the practice server. Continuing locally.",
      );
      setRunning((prev) => !prev);
      setSessionStartedAt((prev) => (prev ? null : Date.now()));
      audioFeedback.playError();
    } finally {
      setActionLoading(false);
    }
  }, [practice, running, intention, enableTts, streaks]);

  /** Manual increment — bumped while reciting outside the backend. */
  const handleIncrement = useCallback((): void => {
    setCount((prev) => prev + 1);
    // Roll over to the next mala.
    if ((count + 1) % MALA_BEADS === 0) {
      setMalaCount((prev) => prev + 1);
      audioFeedback.playTick();
    }
  }, [count]);

  /** Reset to zero (does NOT hit the backend — local UI only). */
  const handleReset = useCallback((): void => {
    setCount(0);
    setMalaCount(0);
    lastSpokenCountRef.current = 0;
    setSessionStartedAt(running ? Date.now() : null);
  }, [running]);

  const handleSaveReflection = useCallback((): void => {
    const trimmed = reflection.trim();
    if (!trimmed || !practice) return;
    const entry: JournalEntry = {
      date: todayStr(),
      practiceId: practice.id,
      reflection: trimmed.slice(0, 1000),
      recited: count,
    };
    appendJournal(entry);
    setJournal(readJournal());
    setReflection('');
    message.success('Reflection saved', 2);
  }, [reflection, practice, count]);

  // -- Loading state --------------------------------------------------------
  if (loading) {
    return (
      <div className="flex-1 h-full overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto">
          <Skeleton active paragraph={{ rows: 6 }} />
        </div>
      </div>
    );
  }

  // -- Not found ------------------------------------------------------------
  if (!practice) {
    return (
      <div className="flex-1 h-full flex items-center justify-center p-6">
        <Result
          status="404"
          title="Practice not found"
          subTitle={`No practice exists at id "${id ?? ''}".`}
          extra={
            <Button
              type="primary"
              icon={<ArrowLeft size={16} />}
              onClick={() => navigate('/practices')}
            >
              Back to library
            </Button>
          }
        />
      </div>
    );
  }

  const Icon = practice.icon;
  const accentStyle = {
    ['--practice-color' as string]: practice.color,
    ['--practice-color-rgb' as string]: practice.colorRgb,
  } as React.CSSProperties;

  const today = todayStr();
  const practiceStreakDates = streaks[practice.id] ?? [];
  const currentStreak = computeCurrentStreak(practiceStreakDates, today);
  const totalSessions = practiceStreakDates.length;
  const journalForPractice = journal
    .filter((j) => j.practiceId === practice.id)
    .slice(0, 3);

  const VizComponent = id ? PRACTICE_VISUALIZATIONS[id] : undefined;

  return (
    <div className="flex-1 h-full overflow-y-auto" style={accentStyle}>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <Space orientation="vertical" size={24} className="w-full">
          {/* Top action row */}
          <div className="flex items-center justify-between">
            <Button
              icon={<ArrowLeft size={16} />}
              onClick={() => navigate('/practices')}
              className="!bg-white/5 !border-white/10 !text-white/80 hover:!bg-white/10"
            >
              Library
            </Button>
            <Space size={8}>
              <Tag
                icon={<CircleDot size={11} />}
                color="default"
                className="!bg-white/5 !border-white/10 !text-white/70 !font-mono"
              >
                {practice.id}
              </Tag>
              {VizComponent && (
                <Tooltip title="Toggle the in-page 3D visualization for this practice">
                  <Button
                    icon={<Eye size={16} />}
                    onClick={() => setShowVisualization((v) => !v)}
                    type={showVisualization ? 'primary' : 'default'}
                    className="!bg-white/5 !border-white/10 !text-white/80 hover:!bg-white/10"
                  >
                    {showVisualization ? 'Hide Visualization' : 'View Visualization'}
                  </Button>
                </Tooltip>
              )}
            </Space>
          </div>

          {/* Header */}
          <div className="text-center">
            <div
              className="mx-auto w-20 h-20 rounded-full flex items-center justify-center mb-4"
              style={{
                background: `radial-gradient(circle, rgba(${practice.colorRgb}, 0.22), rgba(${practice.colorRgb}, 0.04))`,
                boxShadow: `inset 0 0 24px rgba(${practice.colorRgb}, 0.35), 0 0 30px rgba(${practice.colorRgb}, 0.25)`,
              }}
            >
              <Icon size={36} style={{ color: practice.color }} strokeWidth={1.5} />
            </div>
            <Title
              level={2}
              className="!mb-1 !text-white"
              style={{ letterSpacing: '0.02em' }}
            >
              {practice.name}
            </Title>
            {practice.transliteration && (
              <Text type="secondary" className="!font-mono !text-base">
                {practice.transliteration}
              </Text>
            )}
            <Paragraph
              type="secondary"
              className="!mt-3 !max-w-2xl !mx-auto !text-base !leading-relaxed"
            >
              {practice.description}
            </Paragraph>
          </div>

          {getDeityVisualization(id) && (
            <div className="flex justify-center mb-6">
              <SadhanaVisualization deity={getDeityVisualization(id)!} size={260} />
            </div>
          )}

          {/* Error */}
          {error && (
            <Alert
              type="warning"
              showIcon
              message="Working in offline mode"
              description={error}
              closable
              onClose={() => setError(null)}
              className="!bg-amber-500/10 !border-amber-500/30"
            />
          )}

          {/* In-page 3D visualization panel (toggled by the Eye button) */}
          {showVisualization && VizComponent && (
            <Card
              className="!bg-black/40 !border-white/10 backdrop-blur-md"
              styles={{ body: { padding: 0 } }}
              title={
                <div className="flex items-center gap-2 px-2 pt-1">
                  <Eye size={16} style={{ color: practice.color }} />
                  <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                    {practice.name} Visualization
                  </Text>
                </div>
              }
              extra={
                <Button
                  size="small"
                  onClick={() => setShowVisualization(false)}
                  className="!bg-white/5 !border-white/10 !text-white/80"
                >
                  Close
                </Button>
              }
            >
              <div className="h-[420px] w-full bg-black/60">
                <Suspense
                  fallback={
                    <div className="w-full h-full flex items-center justify-center text-white/60 text-sm">
                      Loading visualization…
                    </div>
                  }
                >
                  <Canvas
                    key={`viz-${practice.id}`}
                    camera={{ position: [0, 0, 12], fov: 60 }}
                    className="w-full h-full"
                  >
                    <ambientLight intensity={0.5} />
                    <pointLight position={[10, 10, 10]} intensity={1} />
                    <Stars
                      radius={100}
                      depth={50}
                      count={3500}
                      factor={3}
                      saturation={0}
                      fade
                      speed={0.8}
                    />
                    <VizComponent
                      audioSpectrum={audioSpectrum}
                      isPlaying={isPlaying}
                      frequency={frequency}
                      complexity="medium"
                    />
                    <OrbitControls
                      enableZoom
                      enablePan={false}
                      enableRotate
                      autoRotate
                      autoRotateSpeed={0.5}
                    />
                    <Environment preset="sunset" />
                  </Canvas>
                </Suspense>
              </div>
            </Card>
          )}

          {/* Mantra + Counters */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Mantra card */}
            <Card
              className="!bg-black/40 !border-white/10 backdrop-blur-md"
              styles={{ body: { padding: 24 } }}
            >
              <Space orientation="vertical" size={16} className="w-full">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} style={{ color: practice.color }} />
                  <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                    Mantra
                  </Text>
                </div>
                <div
                  className="text-center px-4 py-6 rounded-lg"
                  style={{
                    background: `linear-gradient(180deg, rgba(${practice.colorRgb}, 0.06), rgba(${practice.colorRgb}, 0.01))`,
                    border: `1px solid rgba(${practice.colorRgb}, 0.18)`,
                  }}
                >
                  <div
                    className="font-serif text-lg leading-relaxed"
                    style={{ color: practice.color }}
                  >
                    {practice.mantra ?? '—'}
                  </div>
                </div>
                {practice.mantraMeaning && (
                  <Paragraph
                    type="secondary"
                    italic
                    className="!text-center !mb-0 !text-sm"
                  >
                    “{practice.mantraMeaning}”
                  </Paragraph>
                )}
              </Space>
            </Card>

            {/* Counter card */}
            <Card
              className="!bg-black/40 !border-white/10 backdrop-blur-md"
              styles={{ body: { padding: 24 } }}
            >
              <div className="flex flex-col items-center gap-4">
                <Text
                  strong
                  className="!text-white !uppercase !tracking-widest !text-xs self-start"
                >
                  Mala Counter
                </Text>
                <div
                  className="flex items-center justify-center gap-3 w-full"
                  aria-label="Practice streak and total sessions"
                >
                  <span className="flex items-center gap-1 text-orange-400 text-sm font-mono">
                    <Flame size={14} aria-hidden /> {currentStreak}
                    -day streak
                  </span>
                  <span className="text-white/30" aria-hidden>|</span>
                  <span className="text-white/70 text-sm font-mono">
                    Total: {totalSessions} session{totalSessions === 1 ? '' : 's'}
                  </span>
                </div>
                <BeadRing
                  count={count}
                  color={practice.color}
                  colorRgb={practice.colorRgb}
                />
                <div className="grid grid-cols-3 gap-2 sm:gap-4 w-full">
                  <Statistic
                    title={
                      <span className="!text-white/60 !text-[10px] sm:!text-xs">Beads</span>
                    }
                    value={count}
                    valueStyle={{
                      color: practice.color,
                      fontSize: 'clamp(14px, 4vw, 20px)',
                      fontFamily: 'monospace',
                    }}
                  />
                  <Statistic
                    title={
                      <span className="!text-white/60 !text-[10px] sm:!text-xs">Malas</span>
                    }
                    value={malaCount}
                    valueStyle={{
                      color: '#fcd34d',
                      fontSize: 'clamp(14px, 4vw, 20px)',
                      fontFamily: 'monospace',
                    }}
                  />
                  <Statistic
                    title={
                      <span className="!text-white/60 !text-[10px] sm:!text-xs">Session</span>
                    }
                    value={formatElapsed(elapsedMs)}
                    valueStyle={{
                      color: '#67e8f9',
                      fontSize: 'clamp(12px, 3.5vw, 16px)',
                      fontFamily: 'monospace',
                    }}
                  />
                </div>
              </div>
            </Card>
          </div>

          {/* Controls */}
          <Card
            className="!bg-black/40 !border-white/10 backdrop-blur-md"
            styles={{ body: { padding: 24 } }}
          >
            <Space orientation="vertical" size={16} className="w-full">
              <div className="flex items-center gap-2">
                <Activity size={16} style={{ color: practice.color }} />
                <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                  Session
                </Text>
                {running && (
                  <Tag
                    color="success"
                    icon={<CheckCircle2 size={11} />}
                    className="!ml-2"
                  >
                    Reciting
                  </Tag>
                )}
              </div>

              <div className="flex flex-wrap gap-3 justify-center">
                <Button
                  type={running ? 'default' : 'primary'}
                  size="large"
                  danger={running}
                  icon={
                    actionLoading ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : running ? (
                      <Square size={16} />
                    ) : (
                      <Play size={16} />
                    )
                  }
                  onClick={handleToggle}
                  loading={actionLoading}
                  className={
                    running
                      ? '!border-red-400/50 !text-red-200 hover:!bg-red-500/10'
                      : '!border-0 !shadow-lg'
                  }
                  style={
                    !running
                      ? {
                          background: `linear-gradient(135deg, ${practice.color}, ${practice.color}dd)`,
                          boxShadow: `0 0 24px rgba(${practice.colorRgb}, 0.4)`,
                        }
                      : undefined
                  }
                >
                  {running ? 'Stop Recitation' : 'Start Recitation'}
                </Button>

                <Button
                  size="large"
                  icon={<RotateCcw size={16} />}
                  onClick={handleReset}
                  className="!bg-white/5 !border-white/10 !text-white/80 hover:!bg-white/10"
                >
                  Reset
                </Button>

                <Button
                  size="large"
                  icon={<Sparkles size={16} />}
                  onClick={handleIncrement}
                  disabled={!running}
                  className="!bg-white/5 !border-white/10 !text-white/80 hover:!bg-white/10"
                >
                  +1 Bead
                </Button>

                <Tooltip
                  title={enableTts ? 'TTS will recite each mantra aloud' : 'Silent recitation — no audio output'}
                >
                  <div className="flex items-center gap-2 px-4 h-10 rounded-lg bg-white/5 border border-white/10 text-white/80">
                    {enableTts ? (
                      <Volume2 size={16} className="text-purple-300" />
                    ) : (
                      <VolumeX size={16} className="text-white/40" />
                    )}
                    <span className="text-sm">Speak mantras</span>
                    <Switch
                      size="small"
                      checked={enableTts}
                      onChange={setEnableTts}
                      aria-label="Toggle mantra TTS recitation"
                    />
                  </div>
                </Tooltip>

                <Tooltip
                  title={
                    enableAmbient
                      ? `Singing-bowl drone at ${practice.frequencyHz ?? 136.1} Hz will hum during TTS`
                      : 'Silent — no ambient bowl tone'
                  }
                >
                  <div className="flex items-center gap-2 px-4 h-10 rounded-lg bg-white/5 border border-white/10 text-white/80">
                    <span className="text-base leading-none" aria-hidden>🥣</span>
                    <span className="text-sm">Ambient Bowl</span>
                    <Switch
                      size="small"
                      checked={enableAmbient}
                      onChange={setEnableAmbient}
                      aria-label="Toggle ambient bowl drone tone"
                    />
                  </div>
                </Tooltip>
              </div>

              {/* Progress bar reflects beads within the current mala */}
              <Progress
                percent={((count % MALA_BEADS) / MALA_BEADS) * 100}
                showInfo={false}
                strokeColor={practice.color}
                railColor={`rgba(${practice.colorRgb}, 0.1)`}
              />
            </Space>
          </Card>

          {/* Intention / Dedication */}
          <Card
            className="!bg-black/40 !border-white/10 backdrop-blur-md"
            styles={{ body: { padding: 24 } }}
          >
            <Space orientation="vertical" size={12} className="w-full">
              <div className="flex items-center gap-2">
                <Heart size={16} style={{ color: '#f43f5e' }} />
                <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                  Intention / Dedication
                </Text>
              </div>
              <Input.TextArea
                rows={3}
                value={intention}
                onChange={(e) => setIntention(e.target.value)}
                placeholder="May all beings be free from suffering..."
                maxLength={500}
                showCount
                className="!bg-black/30 !border-white/10 !text-white"
              />
              <Text type="secondary" className="!text-xs">
                Send this dedication along with your practice. It will be
                included in the next recitation cycle.
              </Text>
            </Space>
          </Card>

          {/* Benefits */}
          <Card
            className="!bg-black/40 !border-white/10 backdrop-blur-md"
            styles={{ body: { padding: 24 } }}
          >
            <Space orientation="vertical" size={12} className="w-full">
              <div className="flex items-center gap-2">
                <Compass size={16} style={{ color: '#06b6d4' }} />
                <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                  Benefits
                </Text>
              </div>
              <ul className="!m-0 !pl-5 space-y-2 text-white/80">
                {practice.benefits.map((b) => (
                  <li key={b} className="leading-relaxed">
                    {b}
                  </li>
                ))}
              </ul>
            </Space>
          </Card>

          {/* Session Journal — reflection prompt + collapsible history */}
          <Card
            className="!bg-black/40 !border-white/10 backdrop-blur-md"
            styles={{ body: { padding: 24 } }}
          >
            <Space orientation="vertical" size={12} className="w-full">
              <div className="flex items-center gap-2">
                <BookText size={16} style={{ color: '#a78bfa' }} />
                <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                  Session Journal
                </Text>
              </div>

              {!running && (
                <Space.Compact style={{ width: '100%' }}>
                  <Input.TextArea
                    rows={2}
                    value={reflection}
                    onChange={(e) => setReflection(e.target.value)}
                    placeholder="Reflect on this session (optional)"
                    maxLength={1000}
                    className="!bg-black/30 !border-white/10 !text-white"
                  />
                  <Button
                    type="primary"
                    icon={<CalendarCheck size={14} />}
                    onClick={handleSaveReflection}
                    disabled={!reflection.trim()}
                    style={{
                      background: `linear-gradient(135deg, ${practice.color}, ${practice.color}dd)`,
                      border: 0,
                    }}
                  >
                    Save
                  </Button>
                </Space.Compact>
              )}

              {journalForPractice.length > 0 && (
                <Collapse
                  ghost
                  items={[
                    {
                      key: 'recent',
                      label: (
                        <Text className="!text-white/80 !text-sm">
                          Past reflections ({journalForPractice.length})
                        </Text>
                      ),
                      children: (
                        <Space orientation="vertical" size={10} className="w-full">
                          {journalForPractice.map((j, i) => (
                            <div
                              key={`${j.date}-${i}`}
                              className="rounded-md px-3 py-2 bg-white/5 border border-white/10"
                            >
                              <div className="flex items-center gap-2 mb-1">
                                <CalendarCheck size={12} className="text-white/50" />
                                <Text type="secondary" className="!text-xs !font-mono">
                                  {j.date} · {j.recited} recitation{j.recited === 1 ? '' : 's'}
                                </Text>
                              </div>
                              <Paragraph className="!mb-0 !text-white/85 !text-sm !whitespace-pre-wrap">
                                {j.reflection}
                              </Paragraph>
                            </div>
                          ))}
                        </Space>
                      ),
                    },
                  ]}
                />
              )}
            </Space>
          </Card>

          {/* Instructions (optional) */}
          {practice.instructions && (
            <Card
              className="!bg-black/40 !border-white/10 backdrop-blur-md"
              styles={{ body: { padding: 24 } }}
            >
              <Space orientation="vertical" size={12} className="w-full">
                <div className="flex items-center gap-2">
                  <Clock size={16} style={{ color: '#fcd34d' }} />
                  <Text strong className="!text-white !uppercase !tracking-widest !text-xs">
                    How to practice
                  </Text>
                </div>
                <Paragraph className="!mb-0 !text-white/75 !leading-relaxed">
                  {practice.instructions}
                </Paragraph>
              </Space>
            </Card>
          )}

          <Divider className="!border-white/10" />

          {/* Closing dedication */}
          <div className="text-center">
            <Text type="secondary" className="!text-xs !font-mono !italic">
              愿一切众生离苦得乐 · May all beings be free from suffering
            </Text>
          </div>
        </Space>
      </div>
    </div>
  );
}