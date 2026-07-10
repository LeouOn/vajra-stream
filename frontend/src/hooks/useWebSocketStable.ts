/**
 * useWebSocketStable — production-grade singleton WebSocket hook.
 *
 * SINGLETON INVARIANT (Wave 5 — WS flood fix).
 *
 * Previously every component calling this hook spawned its own WebSocket.
 * With 13+ consumers mounting concurrently, the browser opened 13+ parallel
 * connections to the backend — flooding the connection manager, the event
 * bus, and the browser's per-host socket limit.
 *
 * The WebSocket is now a **module-level singleton**. All hook consumers
 * share ONE socket and ONE state snapshot via `useSyncExternalStore`.
 * Mount-count tracking ensures the socket is opened on first mount and
 * closed when the last consumer unmounts.
 *
 * The hook's return shape is unchanged — every existing call site
 * continues to work without modification.
 *
 * Message-handler coverage is also unchanged: all 33 case labels in the
 * `data.type` switch are preserved verbatim (see
 * `__tests__/hooks/ws-contract.test.ts`).
 *
 * @param wsUrl — Optional WebSocket endpoint URL (defaults to the
 *   proxy-relative `/ws` URL from `utils/api.ts`).
 */
import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react';
import { WS_URL } from '../utils/api';
import type {
  WSMessage,
  CrystalStatus,
  ScalarStatus,
  WSConnectionState,
  ApiResponse,
  RecitationStatus,
  SakaDawaResult,
  ProviderHealthStatus,
  PracticeStatus,
  WSPracticeStarted,
  WSPracticeRecited,
  WSPracticeCompleted,
  WSPracticeStopped,
  WSLLMUsageUpdate,
} from '../types';

export interface LLMUsageUpdate {
  total_calls: number;
  total_cost_usd: number;
  calls_today: number;
  cost_today: number;
  received_at: number;
}

export interface UseWebSocketStableReturn {
  isConnected: boolean;
  audioSpectrum: number[];
  sessions: Record<string, unknown>;
  connectionStatus: WSConnectionState;
  lastUpdate: Date | null;
  reconnectAttempts: number;
  crystalStatus: CrystalStatus;
  scalarStatus: ScalarStatus;
  connectionStats: Record<string, unknown>;
  rngData: Record<string, unknown> | null;
  buddhaStatus: RecitationStatus | null;
  sakaDawa: SakaDawaResult | null;
  ritualStatus: Record<string, unknown> | null;
  practices: Record<string, PracticeStatus>;
  providerHealth: ProviderHealthStatus[];
  lastProviderHealthUpdate: number | null;
  usageUpdate: LLMUsageUpdate | null;
  lastUsageUpdateAt: number | null;
  idleReflectionCount: number;
  lastIdleReflection: { intention: string; genre: string; timestamp: string; narrative_preview: string } | null;
  error: string | null;
  startSession: (config: Record<string, unknown>) => Promise<ApiResponse>;
  stopSession: (sessionId: string) => Promise<ApiResponse>;
  sendMessage: (message: Record<string, unknown>) => boolean;
  connect: () => void;
  disconnect: () => void;
  getConnectionStats: () => Promise<Record<string, unknown> | null>;
  clearError: () => void;
}

/* -------------------------------------------------------------------------- *
 * Module-level singleton state.
 *
 * ONE WebSocket per browser tab. All hook instances read from the same
 * snapshot via `useSyncExternalStore` and increment/decrement a shared
 * mount counter so the socket lifecycle is bound to "any consumer is
 * mounted" rather than "this specific component is mounted".
 * -------------------------------------------------------------------------- */

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;
const HEARTBEAT_INTERVAL_MS = 30000;
const CONNECTION_TIMEOUT_MS = 10000;

let _ws: WebSocket | null = null;
let _url: string = WS_URL;
let _mountCount = 0;
let _manualDisconnect = false;
let _reconnectAttempts = 0;

let _heartbeatInterval: ReturnType<typeof setInterval> | null = null;
let _reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let _connectionTimeout: ReturnType<typeof setTimeout> | null = null;

const _listeners = new Set<() => void>();

interface WsSnapshot {
  isConnected: boolean;
  audioSpectrum: number[];
  sessions: Record<string, unknown>;
  connectionStatus: WSConnectionState;
  lastUpdate: Date | null;
  reconnectAttempts: number;
  crystalStatus: CrystalStatus;
  scalarStatus: ScalarStatus;
  connectionStats: Record<string, unknown>;
  rngData: Record<string, unknown> | null;
  buddhaStatus: RecitationStatus | null;
  sakaDawa: SakaDawaResult | null;
  ritualStatus: Record<string, unknown> | null;
  practices: Record<string, PracticeStatus>;
  providerHealth: ProviderHealthStatus[];
  lastProviderHealthUpdate: number | null;
  usageUpdate: LLMUsageUpdate | null;
  lastUsageUpdateAt: number | null;
  idleReflectionCount: number;
  lastIdleReflection: { intention: string; genre: string; timestamp: string; narrative_preview: string } | null;
  error: string | null;
}

function _initialSnapshot(): WsSnapshot {
  return {
    isConnected: false,
    audioSpectrum: [],
    sessions: {},
    connectionStatus: 'disconnected',
    lastUpdate: null,
    reconnectAttempts: 0,
    crystalStatus: { active: false, intention: '' },
    scalarStatus: { active: false, rate: 0 },
    connectionStats: {},
    rngData: null,
    buddhaStatus: null,
    sakaDawa: null,
    ritualStatus: null,
    practices: {},
    providerHealth: [],
    lastProviderHealthUpdate: null,
    usageUpdate: null,
    lastUsageUpdateAt: null,
    idleReflectionCount: 0,
    lastIdleReflection: null,
    error: null,
  };
}

let _snapshot: WsSnapshot = _initialSnapshot();

function _notifyListeners(): void {
  _listeners.forEach((fn) => fn());
}

function _updateSnapshot(partial: Partial<WsSnapshot>): void {
  _snapshot = { ..._snapshot, ...partial };
  _notifyListeners();
}

function _subscribe(listener: () => void): () => void {
  _listeners.add(listener);
  return () => {
    _listeners.delete(listener);
  };
}

function _getSnapshot(): WsSnapshot {
  return _snapshot;
}

function _getReconnectDelay(attempt: number): number {
  const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, attempt), MAX_RECONNECT_DELAY);
  return delay + Math.random() * 1000;
}

function _clearTimers(): void {
  if (_reconnectTimeout) {
    clearTimeout(_reconnectTimeout);
    _reconnectTimeout = null;
  }
  if (_heartbeatInterval) {
    clearInterval(_heartbeatInterval);
    _heartbeatInterval = null;
  }
  if (_connectionTimeout) {
    clearTimeout(_connectionTimeout);
    _connectionTimeout = null;
  }
}

function _startHeartbeat(): void {
  if (_heartbeatInterval) clearInterval(_heartbeatInterval);

  _heartbeatInterval = setInterval(() => {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, HEARTBEAT_INTERVAL_MS);
}

function _stopHeartbeat(): void {
  if (_heartbeatInterval) {
    clearInterval(_heartbeatInterval);
    _heartbeatInterval = null;
  }
}

/**
 * Singleton connect — only ONE WebSocket ever exists.
 *
 * Dedupes against OPEN, CONNECTING, AND CLOSING states. The previous
 * implementation only checked `=== OPEN`, so under heavy concurrent mount
 * each consumer's `connect()` raced past the CONNECTING check and opened
 * its own socket — the root cause of the connection flood.
 */
function _connect(url: string = _url): void {
  _url = url;

  // Dedupe: any non-CLOSED state means a connection is already in flight.
  if (_ws && _ws.readyState !== WebSocket.CLOSED) return;

  _manualDisconnect = false;
  console.log(`Connecting to WebSocket (attempt ${_reconnectAttempts + 1}):`, url);

  try {
    _ws = new WebSocket(url);

    _connectionTimeout = setTimeout(() => {
      if (_ws?.readyState === WebSocket.CONNECTING) {
        _ws.close();
        console.log('WebSocket connection timeout');
      }
    }, CONNECTION_TIMEOUT_MS);

    _ws.onopen = () => {
      if (_connectionTimeout) {
        clearTimeout(_connectionTimeout);
        _connectionTimeout = null;
      }
      console.log('WebSocket connected successfully');
      _reconnectAttempts = 0;
      _updateSnapshot({
        isConnected: true,
        connectionStatus: 'connected',
        reconnectAttempts: 0,
        error: null,
        lastUpdate: new Date(),
      });
      _startHeartbeat();
    };

    _ws.onclose = (event: CloseEvent) => {
      if (_connectionTimeout) {
        clearTimeout(_connectionTimeout);
        _connectionTimeout = null;
      }
      console.log('WebSocket disconnected:', event.code, event.reason);

      _stopHeartbeat();
      _updateSnapshot({
        isConnected: false,
        connectionStatus: 'disconnected',
        lastUpdate: new Date(),
      });

      if (!_manualDisconnect && event.code !== 1000 && _reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        const nextAttempt = _reconnectAttempts + 1;
        const delay = _getReconnectDelay(nextAttempt);
        _reconnectAttempts = nextAttempt;

        _updateSnapshot({
          reconnectAttempts: nextAttempt,
          error: `Connection lost. Reconnecting in ${Math.round(delay / 1000)}s... (attempt ${nextAttempt}/${MAX_RECONNECT_ATTEMPTS})`,
        });

        console.log(`Attempting to reconnect (${nextAttempt}/${MAX_RECONNECT_ATTEMPTS}) in ${Math.round(delay)}ms...`);

        _reconnectTimeout = setTimeout(() => _connect(url), delay);
      } else if (_reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        _updateSnapshot({
          error: 'Failed to reconnect after maximum attempts. Please refresh the page.',
        });
      }
    };

    _ws.onerror = (_event: Event) => {
      if (_connectionTimeout) {
        clearTimeout(_connectionTimeout);
        _connectionTimeout = null;
      }
      console.error('WebSocket error:', _event);
      _updateSnapshot({
        connectionStatus: 'error',
        error: 'Connection error occurred',
        lastUpdate: new Date(),
      });
    };

    _ws.onmessage = (event: MessageEvent) => {
      try {
        const data: WSMessage = JSON.parse(event.data as string);

        switch (data.type) {
          case 'realtime_data':
            _updateSnapshot({
              audioSpectrum: data.audio_spectrum || [],
              sessions: data.active_sessions || {},
              lastUpdate: new Date(data.timestamp * 1000),
            });
            break;
          case 'session_update':
            _updateSnapshot({
              sessions: { ..._snapshot.sessions, [data.data.id]: data.data },
            });
            break;
          // Backend: connection_manager_stable_v2.py:124 — session lifecycle event.
          // Informational; session_update delivers the actual session data payload.
          case 'SESSION_STARTED':
            console.log('Session started:', data.session_id, data.intention);
            break;
          case 'connection_status':
            _updateSnapshot({ connectionStatus: data.status as WSConnectionState });
            if (data.connection_id) console.log('Connection ID:', data.connection_id);
            break;
          case 'heartbeat':
            if (data.active_connections !== undefined) {
              _updateSnapshot({
                connectionStats: { ..._snapshot.connectionStats, active_connections: data.active_connections },
              });
            }
            break;
          case 'pong':
          case 'ping':
            break;
          case 'RNG_READING':
            _updateSnapshot({ rngData: data.data });
            break;
          case 'BUDDHA_RECITATION_UPDATE':
            _updateSnapshot({ buddhaStatus: data.data as RecitationStatus });
            break;
          // Backend: core/buddha_recitation_loop.py:196,425,267 — lifecycle events for
          // the 88-Buddhas recitation. Same payload shape as BUDDHA_RECITATION_UPDATE;
          // wire them to the same setter so the UI updates regardless of which fires.
          // (Restored after remediation Task 24 regressively deleted these branches.)
          case 'BUDDHA_RECITATION_STARTED':
          case 'BUDDHA_NAME_RECITED':
          case 'BUDDHA_RECITATION_STOPPED':
            _updateSnapshot({ buddhaStatus: data.data as RecitationStatus });
            break;
          // Backend: core/ritual_engine.py:759,297,317,337,348,368,617 — ritual engine
          // lifecycle + planetary-hour shift. RITUAL_ENGINE_STATUS/RITUAL_PHASE/
          // RITUAL_COMPLETED mutate the ritual status the UI reads; the hour shift is
          // informational only. (Restored after remediation Task 24 regression.)
          case 'RITUAL_ENGINE_STATUS':
          case 'RITUAL_PHASE':
          case 'RITUAL_COMPLETED':
            _updateSnapshot({ ritualStatus: data.data });
            break;
          case 'PLANETARY_HOUR_SHIFT':
            console.log('Planetary hour shift:', data.data);
            break;
          // Backend: core/character_journey.py:175,266,255 — journey lifecycle events.
          // Informational only; no journey state lives in this hook.
          case 'JOURNEY_STAGE_STARTED':
            console.log('Journey stage started:', data.data);
            break;
          case 'JOURNEY_STAGE_COMPLETED':
            console.log('Journey stage completed:', data.data);
            break;
          case 'JOURNEY_COMPLETED':
            console.log('Journey completed:', data.data);
            break;
          case 'SAKA_DAWA_CHECK':
            _updateSnapshot({ sakaDawa: data.data as SakaDawaResult });
            break;
          case 'PROVIDER_HEALTH':
            _updateSnapshot({
              providerHealth: (data as { statuses?: ProviderHealthStatus[] }).statuses || [],
              lastProviderHealthUpdate: Date.now(),
            });
            break;
          // Backend: core/usage_tracker.py — emitted on every LLM call settlement
          // and on a periodic aggregate tick. Drives the live cost badge and
          // "calls today" counter on UsageDashboard.
          case 'LLM_USAGE_UPDATE': {
            const payload = data as WSLLMUsageUpdate;
            _updateSnapshot({
              usageUpdate: {
                total_calls: payload.total_calls ?? 0,
                total_cost_usd: payload.total_cost_usd ?? 0,
                calls_today: payload.calls_today ?? 0,
                cost_today: payload.cost_today ?? 0,
                received_at: Date.now(),
              },
              lastUsageUpdateAt: Date.now(),
            });
            break;
          }
          // Backend: core/practice_engine.py:_broadcast_ws — multi-practice
          // recitation lifecycle (Tara / Zhunti / Medicine Buddha / etc.).
          // PRACTICE_RECITED carries the same shape as PRACTICE_STARTED's
          // status projection, so all four branches fold into one setter.
          case 'PRACTICE_STARTED': {
            const started = (data as WSPracticeStarted).data;
            _updateSnapshot({
              practices: {
                ..._snapshot.practices,
                [started.practice_id]: {
                  practice_id: started.practice_id,
                  practice_name: started.practice_name,
                  intention: started.intention,
                  target_count: started.target_count,
                  total_recited: 0,
                  mala_count: 0,
                  mala_rounds: 0,
                  current_repetition: '',
                  running: true,
                  started_at: new Date().toISOString(),
                  last_recited_at: '',
                  elapsed_seconds: 0,
                  progress_pct: 0,
                },
              },
            });
            break;
          }
          case 'PRACTICE_RECITED': {
            const recited = (data as WSPracticeRecited).data;
            _updateSnapshot({
              practices: {
                ..._snapshot.practices,
                [recited.practice_id]: recited,
              },
            });
            break;
          }
          case 'PRACTICE_COMPLETED': {
            const done = (data as WSPracticeCompleted).data;
            _updateSnapshot({
              practices: {
                ..._snapshot.practices,
                [done.practice_id]: {
                  ...(_snapshot.practices[done.practice_id] ?? ({} as PracticeStatus)),
                  practice_id: done.practice_id,
                  practice_name: done.practice_name,
                  total_recited: done.total_count,
                  mala_rounds: done.mala_rounds,
                  running: false,
                  last_recited_at: new Date().toISOString(),
                  progress_pct: 100,
                } as PracticeStatus,
              },
            });
            break;
          }
          case 'PRACTICE_STOPPED': {
            const stopped = (data as WSPracticeStopped).data;
            _updateSnapshot({
              practices: {
                ..._snapshot.practices,
                [stopped.practice_id]: {
                  ...(_snapshot.practices[stopped.practice_id] ?? ({} as PracticeStatus)),
                  practice_id: stopped.practice_id,
                  practice_name: stopped.practice_name,
                  total_recited: stopped.total_count,
                  mala_rounds: stopped.mala_rounds,
                  running: false,
                  last_recited_at: new Date().toISOString(),
                } as PracticeStatus,
              },
            });
            break;
          }
          case 'CRYSTAL_BROADCAST_STARTED':
            _updateSnapshot({ crystalStatus: { active: true, intention: data.data.intention } });
            break;
          // Backend: backend/app/api/v1/endpoints/outlook.py — idle reflection
          // engine broadcasts a preview each time the hourly loop fires.
          // Drives the notification badge on the Outlook tab.
          case 'IDLE_REFLECTION': {
            const reflection = (data as { data?: { intention?: string; genre?: string; timestamp?: string; narrative_preview?: string } }).data;
            console.log('New idle reflection:', reflection?.narrative_preview);
            _updateSnapshot({
              idleReflectionCount: _snapshot.idleReflectionCount + 1,
              lastIdleReflection: {
                intention: reflection?.intention ?? '',
                genre: reflection?.genre ?? '',
                timestamp: reflection?.timestamp ?? '',
                narrative_preview: reflection?.narrative_preview ?? '',
              },
            });
            break;
          }
          case 'RADIONICS_RATE_BROADCAST':
            _updateSnapshot({ scalarStatus: { ..._snapshot.scalarStatus, rate: data.data.rate } });
            break;
          case 'SCALAR_WAVE_ACTIVE':
            _updateSnapshot({ scalarStatus: { ..._snapshot.scalarStatus, active: data.data.active } });
            break;
          // Backend: connection_manager_stable_v2.py:137 — settings-change ack.
          // No settings store lives in this hook; surface as informational log.
          case 'settings_updated':
            console.log('Settings updated:', data.message);
            break;
          // Backend emits BOTH uppercase 'ERROR' (connection_manager_stable_v2.py:109,131)
          // AND lowercase 'error' (lines 89,93). Explicit fall-through so both surface
          // to the user via setError(); previously uppercase ERROR silently hit default.
          // (Wave 1 Task 10 added the uppercase ERROR branch.)
          case 'ERROR':
          case 'error':
            console.error('Server error:', data.message);
            _updateSnapshot({ error: data.message });
            break;
          // Backend: connection_manager_stable_v2.py:277 — system-level error.
          // Surface to the user alongside the ERROR/error branches.
          case 'system_error':
            console.error('System error:', data.message);
            _updateSnapshot({ error: data.message || 'System error occurred' });
            break;
          default:
            console.log('Unknown WebSocket message type:', data.type);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
        _updateSnapshot({ error: 'Error processing server message' });
      }
    };
  } catch (err) {
    console.error('Failed to create WebSocket connection:', err);
    _updateSnapshot({
      connectionStatus: 'error',
      error: 'Failed to establish connection',
    });
  }
}

function _disconnect(): void {
  _manualDisconnect = true;
  _clearTimers();

  if (_ws) {
    try {
      _ws.close(1000, 'Manual disconnect');
    } catch {
      /* ignore close errors on teardown */
    }
    _ws = null;
  }

  _reconnectAttempts = 0;
  // Fully reset the snapshot so the next consumer mount — including the
  // next test in the same Vitest worker — starts from a clean slate rather
  // than reading stale state left over from the previous socket lifecycle.
  _snapshot = _initialSnapshot();
  _notifyListeners();
}

function _sendMessage(message: Record<string, unknown>): boolean {
  if (_ws?.readyState === WebSocket.OPEN) {
    try {
      _ws.send(JSON.stringify(message));
      return true;
    } catch (err) {
      console.error('Error sending WebSocket message:', err);
      _updateSnapshot({ error: 'Failed to send message' });
      return false;
    }
  }
  console.warn('WebSocket not connected, cannot send message');
  return false;
}

async function _startSession(sessionConfig: Record<string, unknown>): Promise<ApiResponse> {
  try {
    const response = await fetch('/api/v1/sessions/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sessionConfig),
    });
    const result: ApiResponse = await response.json();

    if (result.status === 'success' && result.session_id) {
      const startResponse = await fetch(`/api/v1/sessions/${result.session_id}/start`, { method: 'POST' });
      const startResult: ApiResponse = await startResponse.json();
      if (startResult.status === 'success') {
        console.log('Session started successfully:', result.session_id);
      }
    }
    return result;
  } catch (err) {
    console.error('Error starting session:', err);
    _updateSnapshot({ error: 'Failed to start session' });
    throw err;
  }
}

async function _stopSession(sessionId: string): Promise<ApiResponse> {
  try {
    const response = await fetch(`/api/v1/sessions/${sessionId}/stop`, { method: 'POST' });
    const result: ApiResponse = await response.json();
    if (result.status === 'success') console.log('Session stopped:', sessionId);
    return result;
  } catch (err) {
    console.error('Error stopping session:', err);
    _updateSnapshot({ error: 'Failed to stop session' });
    throw err;
  }
}

async function _getConnectionStats(): Promise<Record<string, unknown> | null> {
  try {
    const response = await fetch('/ws-stats');
    const stats: Record<string, unknown> = await response.json();
    _updateSnapshot({ connectionStats: stats });
    return stats;
  } catch (err) {
    console.error('Error getting connection stats:', err);
    return null;
  }
}

function _clearError(): void {
  _updateSnapshot({ error: null });
}

/* -------------------------------------------------------------------------- *
 * The hook — thin wrapper around the module-level singleton.
 * -------------------------------------------------------------------------- */

export const useWebSocketStable = (wsUrl: string | null = null): UseWebSocketStableReturn => {
  // Subscribe to the singleton snapshot. Every consumer sees the same
  // state reference; React re-renders each consumer when _notifyListeners
  // fires after _updateSnapshot.
  const snapshot = useSyncExternalStore(_subscribe, _getSnapshot, _getSnapshot);

  // First consumer mounts → connect. Last consumer unmounts → disconnect.
  // The URL is captured from the FIRST consumer; subsequent consumers
  // joining the live singleton reuse the existing connection regardless
  // of the URL they pass in (singleton invariant — see module docstring).
  const assignedUrl = useRef<string | null>(null);
  if (assignedUrl.current === null) {
    assignedUrl.current = wsUrl ?? WS_URL;
  }

  useEffect(() => {
    _mountCount++;
    if (_mountCount === 1) {
      _connect(assignedUrl.current ?? WS_URL);
    }
    return () => {
      _mountCount = Math.max(0, _mountCount - 1);
      if (_mountCount === 0) {
        _disconnect();
      }
    };
  }, []);

  // Stable action identities — they close over module-level state, not
  // per-instance state, so they can be plain useCallbacks with no deps.
  const connect = useCallback(() => {
    _connect(assignedUrl.current ?? WS_URL);
  }, []);
  const disconnect = useCallback(() => {
    _disconnect();
  }, []);
  const sendMessage = useCallback((message: Record<string, unknown>) => _sendMessage(message), []);
  const startSession = useCallback(
    (config: Record<string, unknown>) => _startSession(config),
    [],
  );
  const stopSession = useCallback((sessionId: string) => _stopSession(sessionId), []);
  const getConnectionStats = useCallback(() => _getConnectionStats(), []);
  const clearError = useCallback(() => _clearError(), []);

  return {
    isConnected: snapshot.isConnected,
    audioSpectrum: snapshot.audioSpectrum,
    sessions: snapshot.sessions,
    connectionStatus: snapshot.connectionStatus,
    lastUpdate: snapshot.lastUpdate,
    reconnectAttempts: snapshot.reconnectAttempts,
    crystalStatus: snapshot.crystalStatus,
    scalarStatus: snapshot.scalarStatus,
    connectionStats: snapshot.connectionStats,
    rngData: snapshot.rngData,
    buddhaStatus: snapshot.buddhaStatus,
    sakaDawa: snapshot.sakaDawa,
    ritualStatus: snapshot.ritualStatus,
    practices: snapshot.practices,
    providerHealth: snapshot.providerHealth,
    lastProviderHealthUpdate: snapshot.lastProviderHealthUpdate,
    usageUpdate: snapshot.usageUpdate,
    lastUsageUpdateAt: snapshot.lastUsageUpdateAt,
    idleReflectionCount: snapshot.idleReflectionCount,
    lastIdleReflection: snapshot.lastIdleReflection,
    error: snapshot.error,
    startSession,
    stopSession,
    sendMessage,
    connect,
    disconnect,
    getConnectionStats,
    clearError,
  };
};
