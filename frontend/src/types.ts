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
  data: { intention: string };
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
