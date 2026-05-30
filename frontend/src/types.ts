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

export interface Toast {
  id: number;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  duration: number;
  action: (() => void) | null;
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
