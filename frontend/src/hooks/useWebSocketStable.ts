/**
 * useWebSocketStable — production-grade WebSocket hook with heartbeat.
 *
 * More robust WebSocket hook. Adds configurable WebSocket URL, heartbeat/ping
 * interval, connection statistics tracking, manual disconnect flag (to suppress
 * reconnect after intentional close), and error state.
 *
 * The canonical WebSocket hook — imported as `useWebSocket` by most components.
 *
 * @param wsUrl — Optional WebSocket endpoint URL (defaults to auto-detected backend).
 */
import { useState, useEffect, useRef, useCallback } from 'react';
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
} from '../types';

// Local state shapes for events that previously hit default: console.log.
// Journey events come from core/character_journey.py:225,335,324.
// Astrology hour-shift comes from core/ritual_engine.py:617.
export interface JourneyState {
  currentStage?: number;
  stageName?: string;
  character?: string;
  totalStages?: number;
  totalBlessings?: number;
  completed?: boolean;
  startedAt?: number;
}

export interface AstrologyContext {
  currentHour?: string;
  tithi?: string;
  nakshatra?: string;
  since?: number;
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
  providerHealth: ProviderHealthStatus[];
  lastProviderHealthUpdate: number | null;
  journey: JourneyState | null;
  astrologyContext: AstrologyContext | null;
  error: string | null;
  startSession: (config: Record<string, unknown>) => Promise<ApiResponse>;
  stopSession: (sessionId: string) => Promise<ApiResponse>;
  sendMessage: (message: Record<string, unknown>) => boolean;
  connect: () => void;
  disconnect: () => void;
  getConnectionStats: () => Promise<Record<string, unknown> | null>;
  clearError: () => void;
}

export const useWebSocketStable = (wsUrl: string | null = null): UseWebSocketStableReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [audioSpectrum, setAudioSpectrum] = useState<number[]>([]);
  const [sessions, setSessions] = useState<Record<string, unknown>>({});
  const [connectionStatus, setConnectionStatus] = useState<WSConnectionState>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [crystalStatus, setCrystalStatus] = useState<CrystalStatus>({ active: false, intention: '' });
  const [scalarStatus, setScalarStatus] = useState<ScalarStatus>({ active: false, rate: 0 });
  const [connectionStats, setConnectionStats] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [rngData, setRngData] = useState<Record<string, unknown> | null>(null);
  const [buddhaStatus, setBuddhaStatus] = useState<RecitationStatus | null>(null);
  const [sakaDawa, setSakaDawa] = useState<SakaDawaResult | null>(null);
  const [ritualStatus, setRitualStatus] = useState<Record<string, unknown> | null>(null);
  const [providerHealth, setProviderHealth] = useState<ProviderHealthStatus[]>([]);
  const [lastProviderHealthUpdate, setLastProviderHealthUpdate] = useState<number | null>(null);
  const [journey, setJourney] = useState<JourneyState | null>(null);
  const [astrologyContext, setAstrologyContext] = useState<AstrologyContext | null>(null);

  const ws = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const manualDisconnect = useRef(false);

  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000;
  const maxReconnectDelay = 30000;
  const heartbeatInterval = 30000;
  const connectionTimeout = 10000;

  const getReconnectDelay = (attempt: number): number => {
    const delay = Math.min(baseReconnectDelay * Math.pow(2, attempt), maxReconnectDelay);
    return delay + Math.random() * 1000;
  };

  const getDefaultWsUrl = (): string => {
    // Use the centralized WS_URL from utils/api which always points
    // at the backend port (8008), bypassing the unreliable Vite WS proxy.
    return WS_URL;
  };

  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);

    heartbeatIntervalRef.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, heartbeatInterval);
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const url = wsUrl || getDefaultWsUrl();
    console.log(`Connecting to WebSocket (attempt ${reconnectAttemptsRef.current + 1}):`, url);

    try {
      ws.current = new WebSocket(url);

      const timeoutId = setTimeout(() => {
        if (ws.current?.readyState === WebSocket.CONNECTING) {
          ws.current.close();
          console.log('WebSocket connection timeout');
        }
      }, connectionTimeout);

      ws.current.onopen = () => {
        clearTimeout(timeoutId);
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setConnectionStatus('connected');
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);
        setError(null);
        setLastUpdate(new Date());
        startHeartbeat();
      };

      ws.current.onclose = (event: CloseEvent) => {
        clearTimeout(timeoutId);
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        setLastUpdate(new Date());
        stopHeartbeat();

        if (!manualDisconnect.current && event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const nextAttempt = reconnectAttemptsRef.current + 1;
          const delay = getReconnectDelay(nextAttempt);

          reconnectAttemptsRef.current = nextAttempt;
          setReconnectAttempts(nextAttempt);
          setError(`Connection lost. Reconnecting in ${Math.round(delay / 1000)}s... (attempt ${nextAttempt}/${maxReconnectAttempts})`);

          console.log(`Attempting to reconnect (${nextAttempt}/${maxReconnectAttempts}) in ${Math.round(delay)}ms...`);

          reconnectTimeoutRef.current = setTimeout(() => connect(), delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError('Failed to reconnect after maximum attempts. Please refresh the page.');
        }
      };

      ws.current.onerror = (_event: Event) => {
        clearTimeout(timeoutId);
        console.error('WebSocket error:', _event);
        setConnectionStatus('error');
        setError('Connection error occurred');
        setLastUpdate(new Date());
      };

      ws.current.onmessage = (event: MessageEvent) => {
        try {
          const data: WSMessage = JSON.parse(event.data as string);

          switch (data.type) {
            case 'realtime_data':
              setAudioSpectrum(data.audio_spectrum || []);
              setSessions(data.active_sessions || {});
              setLastUpdate(new Date(data.timestamp * 1000));
              break;
            case 'session_update':
              setSessions(prev => ({ ...prev, [data.data.id]: data.data }));
              break;
            // Backend: connection_manager_stable_v2.py:132 — session lifecycle event.
            // Payload shape: {type, session_id, intention, timestamp} (no data wrapper).
            // Fold into the sessions map alongside session_update.
            case 'SESSION_STARTED':
              setSessions(prev => ({
                ...prev,
                [data.session_id]: {
                  ...(prev[data.session_id] || {}),
                  id: data.session_id,
                  name: data.intention,
                  status: 'started',
                  _updatedAt: data.timestamp,
                },
              }));
              break;
            case 'connection_status':
              setConnectionStatus(data.status as WSConnectionState);
              if (data.connection_id) console.log('Connection ID:', data.connection_id);
              break;
            case 'heartbeat':
              if (data.active_connections !== undefined) {
                setConnectionStats(prev => ({ ...prev, active_connections: data.active_connections }));
              }
              break;
            case 'pong':
            case 'ping':
              break;
            case 'RNG_READING':
              setRngData(data.data);
              break;
            case 'BUDDHA_RECITATION_UPDATE':
              setBuddhaStatus(data.data as RecitationStatus);
              break;
            // Backend: core/buddha_recitation_loop.py:196,425,267 — lifecycle events for
            // the 88-Buddhas recitation. Same payload shape as BUDDHA_RECITATION_UPDATE;
            // wire them to the same setter so the UI updates regardless of which fires.
            // (Restored after remediation Task 24 regressively deleted these branches.)
            case 'BUDDHA_RECITATION_STARTED':
            case 'BUDDHA_NAME_RECITED':
            case 'BUDDHA_RECITATION_STOPPED':
              setBuddhaStatus(data.data as RecitationStatus);
              break;
            // Backend: core/ritual_engine.py:759,297,317,337,348,368,617 — ritual engine
            // lifecycle + planetary-hour shift. RITUAL_ENGINE_STATUS/RITUAL_PHASE/
            // RITUAL_COMPLETED mutate the ritual status the UI reads; the hour shift is
            // informational only. (Restored after remediation Task 24 regression.)
            case 'RITUAL_ENGINE_STATUS':
            case 'RITUAL_PHASE':
            case 'RITUAL_COMPLETED':
              setRitualStatus(data.data);
              break;
            // Backend: core/ritual_engine.py:617 — fires when _last_hour changes.
            // Powers a "current planetary hour" indicator in the UI.
            case 'PLANETARY_HOUR_SHIFT':
              setAstrologyContext({
                currentHour: data.data.hour,
                tithi: data.data.tithi,
                nakshatra: data.data.nakshatra,
                since: data.timestamp,
              });
              break;
            // Backend: core/character_journey.py:225,335,324 — journey lifecycle events.
// Stage events reset/replace the active journey; completion freezes it.
            case 'JOURNEY_STAGE_STARTED':
              setJourney({
                currentStage: data.data.stage,
                stageName: data.data.name,
                character: data.data.character,
                startedAt: data.timestamp,
              });
              break;
            case 'JOURNEY_STAGE_COMPLETED':
              setJourney(prev => ({
                ...(prev || {}),
                totalBlessings: (prev?.totalBlessings || 0) + (data.data.blessings_count || 0),
                lastCompletedStage: data.data.stage,
                lastCompletedStageName: data.data.name,
              }));
              break;
            case 'JOURNEY_COMPLETED':
              setJourney(prev => ({
                ...(prev || {}),
                completed: true,
                totalStages: data.data.total_stages,
                totalBlessings: data.data.total_blessings,
                character: data.data.character,
              }));
              break;
            case 'SAKA_DAWA_CHECK':
              setSakaDawa(data.data as SakaDawaResult);
              break;
            case 'PROVIDER_HEALTH':
              setProviderHealth((data as { statuses?: ProviderHealthStatus[] }).statuses || []);
              setLastProviderHealthUpdate(Date.now());
              break;
            case 'CRYSTAL_BROADCAST_STARTED':
              setCrystalStatus({ active: true, intention: data.data.intention });
              break;
            case 'RADIONICS_RATE_BROADCAST':
              setScalarStatus(prev => ({ ...prev, rate: data.data.rate }));
              break;
            case 'SCALAR_WAVE_ACTIVE':
              setScalarStatus(prev => ({ ...prev, active: data.data.active }));
              break;
            // Backend: connection_manager_stable_v2.py:137 — settings-change ack.
            // No settings store lives in this hook; surface as informational log.
            case 'settings_updated':
              console.log('Settings updated:', data.message);
              break;
            // Backend: orchestrator_bridge._forward_event_to_websocket forwards every
            // DomainEvent subclass as {type: ClassName, timestamp, data: {...}}.
            // SessionCreated/Started/Stopped carry session lifecycle info that
            // previously hit default. Fold into the existing sessions map.
            case 'SessionCreated':
              setSessions(prev => ({
                ...prev,
                [data.data.session_id]: {
                  ...(prev[data.data.session_id] || {}),
                  ...data.data,
                  id: data.data.session_id,
                  status: 'created',
                  _updatedAt: data.timestamp,
                },
              }));
              break;
            case 'SessionStarted':
              setSessions(prev => ({
                ...prev,
                [data.data.session_id]: {
                  ...(prev[data.data.session_id] || {}),
                  ...data.data,
                  id: data.data.session_id,
                  status: 'started',
                  _updatedAt: data.timestamp,
                },
              }));
              break;
            case 'SessionStopped':
              setSessions(prev => ({
                ...prev,
                [data.data.session_id]: {
                  ...(prev[data.data.session_id] || {}),
                  ...data.data,
                  id: data.data.session_id,
                  status: 'stopped',
                  _updatedAt: data.timestamp,
                },
              }));
              break;
            // Backend emits BOTH uppercase 'ERROR' (connection_manager_stable_v2.py:109,131)
            // AND lowercase 'error' (lines 89,93). Explicit fall-through so both surface
            // to the user via setError(); previously uppercase ERROR silently hit default.
            // (Wave 1 Task 10 added the uppercase ERROR branch.)
            case 'ERROR':
            case 'error':
              console.error('Server error:', data.message);
              setError(data.message);
              break;
            // Backend: connection_manager_stable_v2.py:277 — system-level error.
            // Surface to the user alongside the ERROR/error branches.
            case 'system_error':
              console.error('System error:', data.message);
              setError(data.message || 'System error occurred');
              break;
            default:
              console.log('Unknown WebSocket message type:', data.type);
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          setError('Error processing server message');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setConnectionStatus('error');
      setError('Failed to establish connection');
    }
  }, [wsUrl, startHeartbeat, stopHeartbeat]);

  const disconnect = useCallback(() => {
    manualDisconnect.current = true;
    clearTimers();

    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    setReconnectAttempts(0);
    setError(null);
  }, [clearTimers]);

  const sendMessage = useCallback((message: Record<string, unknown>): boolean => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (err) {
        console.error('Error sending WebSocket message:', err);
        setError('Failed to send message');
        return false;
      }
    }
    console.warn('WebSocket not connected, cannot send message');
    return false;
  }, []);

  const startSession = useCallback(async (sessionConfig: Record<string, unknown>): Promise<ApiResponse> => {
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
      setError('Failed to start session');
      throw err;
    }
  }, []);

  const stopSession = useCallback(async (sessionId: string): Promise<ApiResponse> => {
    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}/stop`, { method: 'POST' });
      const result: ApiResponse = await response.json();
      if (result.status === 'success') console.log('Session stopped:', sessionId);
      return result;
    } catch (err) {
      console.error('Error stopping session:', err);
      setError('Failed to stop session');
      throw err;
    }
  }, []);

  const getConnectionStats = useCallback(async (): Promise<Record<string, unknown> | null> => {
    try {
      const response = await fetch('/ws-stats');
      const stats: Record<string, unknown> = await response.json();
      setConnectionStats(stats);
      return stats;
    } catch (err) {
      console.error('Error getting connection stats:', err);
      return null;
    }
  }, []);

  useEffect(() => {
    manualDisconnect.current = false;
    connect();
    return () => { disconnect(); };
  }, [connect, disconnect]);

  useEffect(() => {
    return () => { clearTimers(); };
  }, [clearTimers]);

  return {
    isConnected,
    audioSpectrum,
    sessions,
    connectionStatus,
    lastUpdate,
    reconnectAttempts,
    crystalStatus,
    scalarStatus,
    connectionStats,
    rngData,
    buddhaStatus,
    sakaDawa,
    ritualStatus,
    providerHealth,
    lastProviderHealthUpdate,
    journey,
    astrologyContext,
    error,
    startSession,
    stopSession,
    sendMessage,
    connect,
    disconnect,
    getConnectionStats,
    clearError: () => setError(null),
  };
};
