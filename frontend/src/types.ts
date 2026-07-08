/**
 * Shared TypeScript types for Vajra.Stream frontend.
 */

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
  data: { rate: number };
}

export interface WSScalarWave extends WSMessageBase {
  type: 'SCALAR_WAVE_ACTIVE';
  data: { active: boolean };
}

export interface WSError extends WSMessageBase {
  type: 'error';
  message: string;
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
export interface WSLLMUsageUpdate extends WSMessageBase {
  type: 'LLM_USAGE_UPDATE';
  total_calls: number;
  total_cost_usd: number;
  calls_today: number;
  cost_today: number;
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
  | WSMessageBase;

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

export interface SakaDawaResult {
  is_saka_dawa: boolean;
  multiplier: number;
  current_date: string;
  saka_dawa_month_start?: string;
  saka_dawa_month_end?: string;
  saka_dawa_duchen?: string;
  is_duchen?: boolean;
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
