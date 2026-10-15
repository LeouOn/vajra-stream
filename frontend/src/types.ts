/**
 * Shared TypeScript types for Vajra.Stream frontend.
 */

import type { Provenance } from './types/operations';

// ---------------------------------------------------------------------------
// WebSocket message types
// ---------------------------------------------------------------------------

export interface WSMessageBase {
  type: string;
}

export interface WSRealtimeData extends WSMessageBase {
  type: 'realtime_data';
  audio_spectrum: number[];
  active_sessions: Record<string, unknown>;
  timestamp: number;
}

export interface WSAudioSpectrum extends WSMessageBase {
  type: 'audio_spectrum';
  data: number[];
}

export interface WSSessionUpdate extends WSMessageBase {
  type: 'session_update';
  data: { id: string; [key: string]: unknown };
}

export interface WSConnectionStatus extends WSMessageBase {
  type: 'connection_status';
  status: string;
  connection_id?: string;
  message?: string;
  timestamp?: number;
}

export interface WSHeartbeat extends WSMessageBase {
  type: 'heartbeat';
  active_connections?: number;
}

export interface WSBlessingStarted extends WSMessageBase {
  type: 'BLESSING_STARTED';
  data: { intention: string; target: string };
}

export interface WSCrystalBroadcast extends WSMessageBase {
  type: 'CRYSTAL_BROADCAST_STARTED';
  data: { session_id: string; intention: string };
}

export interface WSRadionicsRate extends WSMessageBase {
  type: 'RADIONICS_RATE_BROADCAST';
  /** rate = carrier frequency mod 100 (computed, no jitter) — vajra_service.rate_broadcast_message. */
  data: { rate: number; session_id?: string; frequency?: number; provenance?: Partial<Record<string, Provenance>> };
}

export interface WSScalarWave extends WSMessageBase {
  type: 'SCALAR_WAVE_ACTIVE';
  data: { active: boolean };
}

/**
 * Error frames. The backend sends BOTH lowercase `error`
 * (connection_manager.py: bad JSON / handler failure) and uppercase `ERROR`
 * (session-start failures) with the same `{ message }` shape.
 */
export interface WSError extends WSMessageBase {
  type: 'error' | 'ERROR';
  message: string;
}

/** connection_manager.py send_safe_realtime_data — loop failure notice. */
export interface WSSystemError extends WSMessageBase {
  type: 'system_error';
  message?: string;
  error?: string;
  timestamp?: number;
}

/** connection_manager.py _handle_update_settings — settings-change ack. */
export interface WSSettingsUpdated extends WSMessageBase {
  type: 'settings_updated';
  message?: string;
}

/** connection_manager.py _handle_start_session — informational lifecycle event. */
export interface WSSessionStarted extends WSMessageBase {
  type: 'SESSION_STARTED';
  session_id: string;
  intention: string;
  timestamp?: number;
}

/** Keep-alive frames: `pong` answers the client ping; `ping` is server-initiated (main.py). */
export interface WSKeepAlive extends WSMessageBase {
  type: 'ping' | 'pong';
  timestamp?: number;
}

/**
 * BUDDHA_RECITATION_STARTED — core/buddha_recitation_loop.py start(). Unlike
 * the other recitation events this is NOT a full `get_status()` projection.
 */
export interface WSBuddhaRecitationStarted extends WSMessageBase {
  type: 'BUDDHA_RECITATION_STARTED';
  data: { intention: string; total_buddhas: number };
  timestamp?: number;
}

/** BUDDHA_NAME_RECITED / BUDDHA_RECITATION_STOPPED carry `get_status()`. */
export interface WSBuddhaRecitationEvent extends WSMessageBase {
  type: 'BUDDHA_NAME_RECITED' | 'BUDDHA_RECITATION_STOPPED';
  data: RecitationStatus;
  timestamp?: number;
}

/** core/ritual_engine.py _broadcast_ws — record/status dicts. */
export interface WSRitualEvent extends WSMessageBase {
  type: 'RITUAL_ENGINE_STATUS' | 'RITUAL_PHASE' | 'RITUAL_COMPLETED' | 'PLANETARY_HOUR_SHIFT';
  data: Record<string, unknown>;
  timestamp?: number;
}

/** core/character_journey.py _broadcast_ws — informational only. */
export interface WSJourneyEvent extends WSMessageBase {
  type: 'JOURNEY_STAGE_STARTED' | 'JOURNEY_STAGE_COMPLETED' | 'JOURNEY_COMPLETED';
  data: Record<string, unknown>;
  timestamp?: number;
}

/** modules/radionics.py broadcast_healing — singing-bowl broadcast notice. */
export interface HealingBroadcastPayload {
  target?: string;
  location?: string;
  lat?: number | null;
  lon?: number | null;
  frequency_hz?: number;
  frequencies?: number[];
  duration_minutes?: number;
  audio_muted?: boolean;
}

export interface WSHealingBroadcastStarted extends WSMessageBase {
  type: 'HEALING_BROADCAST_STARTED';
  data?: HealingBroadcastPayload;
  timestamp?: number;
}

/** backend/app/main.py — operations ledger pushes the full Operation (validated by the store). */
export interface WSOperationUpdate extends WSMessageBase {
  type: 'operation_update';
  data?: unknown;
}

/**
 * Async chat progress — backend/app/api/v1/endpoints/llm.py `_push()` spreads
 * the event fields next to `type` and `job_id` (e.g. `tool`, `args`, `result`,
 * `error`, `response`). `chat_cancelled` IS emitted there (on cancel/timeout
 * paths), even though scripts/audit_ws_contract.py does not list it.
 */
export interface WSChatProgress extends WSMessageBase {
  type:
    | 'chat_started'
    | 'chat_tool_start'
    | 'chat_tool_complete'
    | 'chat_tool_error'
    | 'chat_complete'
    | 'chat_error'
    | 'chat_cancelled';
  job_id: string;
  [key: string]: unknown;
}

/** outlook.py background loop / idle reflection engine. */
export interface IdleReflectionPayload {
  intention?: string;
  genre?: string;
  timestamp?: string;
  narrative_preview?: string;
  stats?: Record<string, unknown>;
}

export interface WSIdleReflection extends WSMessageBase {
  type: 'IDLE_REFLECTION' | 'BACKGROUND_GENERATION';
  data?: IdleReflectionPayload;
}

export interface WSBuddhaRecitationUpdate extends WSMessageBase {
  type: 'BUDDHA_RECITATION_UPDATE';
  data: RecitationStatus;
  timestamp: number;
}

export interface WSSakaDawaCheck extends WSMessageBase {
  type: 'SAKA_DAWA_CHECK';
  data: SakaDawaResult;
  timestamp: number;
}

export interface WSRngReading extends WSMessageBase {
  type: 'RNG_READING';
  data: RNGReading;
  timestamp: number;
}

export interface WSProviderHealth extends WSMessageBase {
  type: 'PROVIDER_HEALTH';
  statuses: ProviderHealthStatus[];
  timestamp?: number;
}

/**
 * LLM_USAGE_UPDATE — streamed from the backend when aggregate usage counters
 * change. The payload drives the live cost badge in `UsageDashboard`.
 *
 * Backend: `core/usage_tracker.py` (broadcast on every call settlement).
 */
export interface LLMUsageSummaryPayload {
  total_calls?: number | null;
  total_cost_usd?: number | null;
  calls_today?: number | null;
  cost_today?: number | null;
  daily_cost_usd?: number | null;
  daily_cost_cap?: number | null;
  over_cap?: boolean | null;
  remaining_balance?: number | null;
  provider_stats?: Record<string, unknown> | null;
}

/**
 * Backend: `backend/app/main.py` `_broadcast_usage` — the counters are nested
 * under `data` (they were once read from the top level, which always gave 0).
 */
export interface WSLLMUsageUpdate extends WSMessageBase {
  type: 'LLM_USAGE_UPDATE';
  data: LLMUsageSummaryPayload;
  timestamp?: number;
}

export interface WSPracticeStarted extends WSMessageBase {
  type: 'PRACTICE_STARTED';
  data: PracticeStartedPayload;
  timestamp: number;
}

export interface WSPracticeRecited extends WSMessageBase {
  type: 'PRACTICE_RECITED';
  data: PracticeStatus;
  timestamp: number;
}

export interface WSPracticeCompleted extends WSMessageBase {
  type: 'PRACTICE_COMPLETED';
  data: PracticeCompletedPayload;
  timestamp: number;
}

export interface WSPracticeStopped extends WSMessageBase {
  type: 'PRACTICE_STOPPED';
  data: PracticeStoppedPayload;
  timestamp: number;
}

/**
 * Every message the `useWebSocketStable` switch handles, discriminated on
 * `type`. Frames with any other `type` fall to the switch's `default:`.
 */
export type WSMessage =
  | WSRealtimeData
  | WSAudioSpectrum
  | WSSessionUpdate
  | WSConnectionStatus
  | WSHeartbeat
  | WSBlessingStarted
  | WSCrystalBroadcast
  | WSRadionicsRate
  | WSScalarWave
  | WSBuddhaRecitationUpdate
  | WSSakaDawaCheck
  | WSRngReading
  | WSProviderHealth
  | WSLLMUsageUpdate
  | WSPracticeStarted
  | WSPracticeRecited
  | WSPracticeCompleted
  | WSPracticeStopped
  | WSError
  | WSSystemError
  | WSSettingsUpdated
  | WSSessionStarted
  | WSKeepAlive
  | WSBuddhaRecitationStarted
  | WSBuddhaRecitationEvent
  | WSRitualEvent
  | WSJourneyEvent
  | WSHealingBroadcastStarted
  | WSOperationUpdate
  | WSChatProgress
  | WSIdleReflection;

// ---------------------------------------------------------------------------
// Status types
// ---------------------------------------------------------------------------

export interface CrystalStatus {
  active: boolean;
  intention: string;
}

export interface ScalarStatus {
  active: boolean;
  rate: number;
}

export interface ProviderHealthStatus {
  provider: string;
  healthy: boolean;
  latency_ms: number;
  error: string | null;
  last_checked: number;
  models_available: number;
}

export type WSConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

// ---------------------------------------------------------------------------
// Session types
// ---------------------------------------------------------------------------

export interface SessionConfig {
  name?: string;
  intention: string;
  duration?: number;
  modality?: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// API response wrappers
// ---------------------------------------------------------------------------

export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  session_id?: string;
  data?: T;
  message?: string;
}

// ---------------------------------------------------------------------------
// Astrology
// ---------------------------------------------------------------------------

export interface PlanetaryPosition {
  longitude: number;
  sign: string;
  degree: number;
  formatted: string;
  house?: number | null;
}

export interface MoonPhase {
  phase_name: string;
  illumination: number;
  phase_angle: number;
  is_new_moon: boolean;
  is_full_moon: boolean;
}

// ---------------------------------------------------------------------------
// Store types (imported by store modules)
// ---------------------------------------------------------------------------

export interface ToastAction {
  onClick: () => void;
  label: string;
}

export interface Toast {
  id: number;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  duration: number;
  action: ToastAction | null;
}

export interface RatePreset {
  id: string;
  name: string;
  values: number[];
  icon: string;
  category: string;
}

export interface CommandDef {
  id: string;
  label: string;
  category: string;
  shortcut?: string;
  icon?: string;
}

// ---------------------------------------------------------------------------
// 88 Buddhas & Saka Dawa Types
// ---------------------------------------------------------------------------

export interface BuddhaEntry {
  name_chinese: string;
  name_pinyin?: string;
  name_sanskrit?: string;
  category: string;
}

export interface RecitationStatus {
  running: boolean;
  intention: string;
  current_index: number;
  current_cycle: number;
  total_recited: number;
  mala_count: number;
  dedications: number;
  total_buddhas: number;
  current_buddha: BuddhaEntry | Record<string, never>;
  progress_pct: number;
  started_at: string;
  last_recited_at: string;
}

export interface SakaDawaPractice {
  id?: string;
  name?: string;
  tradition?: string;
  description?: string;
  genre?: string;
  merit_multiplier?: number;
  blessing_prompt?: string;
  preferred_hours?: string[];
}

export interface SakaDawaResult {
  is_saka_dawa: boolean;
  is_duchen?: boolean;
  multiplier: number;
  current_date: string;
  lunar_month?: number | null;
  lunar_day?: number | null;
  losar?: string | null;
  saka_dawa_month_start?: string | null;
  saka_dawa_month_end?: string | null;
  saka_dawa_duchen?: string | null;
  days_until_saka_dawa?: number | null;
  days_until_duchen?: number | null;
  calendar?: string;
  tibetan_year?: number;
  message?: string;
  practice?: SakaDawaPractice;
}

// ---------------------------------------------------------------------------
// Multi-practice engine (Tara, Zhunti, Medicine Buddha, Vajrasattva,
// Amitabha, Avalokiteshvara, Heart Sutra, ...)
// Backend: core/practice_engine.py + backend/app/api/v1/endpoints/practices.py
// ---------------------------------------------------------------------------

export interface PracticeListItem {
  practice_id: string;
  name: string;
  primary_purpose: string;
  tradition: string;
  category: string;
  benefits: string[];
  dedication: string;
  frequency_hz: number | null;
  color: string | null;
  color_name: string | null;
  element: string;
  chakra: string;
  target_count: number;
  visualizations: string[];
  mantra_count: number;
}

export interface PracticeStatus {
  practice_id: string;
  practice_name: string;
  intention: string;
  target_count: number;
  total_recited: number;
  mala_count: number;
  mala_rounds: number;
  current_repetition: string;
  running: boolean;
  started_at: string;
  last_recited_at: string;
  elapsed_seconds: number;
  progress_pct: number;
}

export interface PracticeStartedPayload {
  practice_id: string;
  practice_name: string;
  intention: string;
  target_count: number;
}

export interface PracticeCompletedPayload {
  practice_id: string;
  practice_name: string;
  total_count: number;
  mala_rounds: number;
  duration_seconds: number;
  intention: string;
}

export interface PracticeStoppedPayload {
  practice_id: string;
  practice_name: string;
  total_count: number;
  mala_rounds: number;
  reason: string;
}

export interface RNGReading {
  coherence: number;
  entropy: number;
  floating_needle_score: number;
  session_id?: string;
  /** Every attunement value is a draw — rng_attunement_service.READING_PROVENANCE. */
  provenance?: Partial<Record<string, Provenance>>;
}

export interface CharacterSheet {
  name: string;
  element: string;
  role: string;
  chinese_name?: string;
  stats?: Record<string, number>;
  [key: string]: unknown;
}

export interface TimingWindow {
  go: boolean;
  planetary_hour: string;
  tithi: string;
  nakshatra: string;
  quality: string;
  message: string;
  transmutation: string;
  transmutation_mantra: string;
  wait_minutes: number;
  next_favorable_hour: string;
  time_shift_available: boolean;
  recommended_approach: string;
  details?: Record<string, unknown> | null;
}

export interface JourneyStageResult {
  stage: string;
  status: string;
  progress: number;
  message?: string;
  [key: string]: unknown;
}
