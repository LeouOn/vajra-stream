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
import type {
  WSMessage,
  CrystalStatus,
  ScalarStatus,
  WSConnectionState,
  ApiResponse,
  RecitationStatus,
  SakaDawaResult,
} from '../types';

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
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}/ws`;
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
            case 'audio_spectrum':
              setAudioSpectrum(data.data || []);
              break;
            case 'session_update':
              setSessions(prev => ({ ...prev, [data.data.id]: data.data }));
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
            case 'SAKA_DAWA_CHECK':
              setSakaDawa(data.data as SakaDawaResult);
              break;
            case 'BLESSING_STARTED':
              console.log('Blessing started:', data.data);
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
            case 'JOURNEY_STAGE_STARTED':
            case 'JOURNEY_STAGE_COMPLETED':
            case 'JOURNEY_COMPLETED':
              console.log(`Journey event: ${data.type}`, data.data);
              break;
            case 'BUDDHA_RECITATION_STARTED':
            case 'BUDDHA_NAME_RECITED':
            case 'BUDDHA_RECITATION_STOPPED':
              console.log(`Recitation event: ${data.type}`, data.data);
              break;
            case 'error':
              console.error('Server error:', data.message);
              setError(data.message);
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
