import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocketStable = (wsUrl = null) => {
  const [isConnected, setIsConnected] = useState(false);
  const [audioSpectrum, setAudioSpectrum] = useState([]);
  const [sessions, setSessions] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [crystalStatus, setCrystalStatus] = useState({ active: false, intention: '' });
  const [scalarStatus, setScalarStatus] = useState({ active: false, rate: 0 });
  const [connectionStats, setConnectionStats] = useState({});
  const [error, setError] = useState(null);
  
  const ws = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const manualDisconnect = useRef(false);
  
  // Configuration
  const maxReconnectAttempts = 10;
  const baseReconnectDelay = 1000; // 1 second
  const maxReconnectDelay = 30000; // 30 seconds
  const heartbeatInterval = 30000; // 30 seconds
  const connectionTimeout = 10000; // 10 seconds

  // Calculate exponential backoff delay
  const getReconnectDelay = (attempt) => {
    const delay = Math.min(baseReconnectDelay * Math.pow(2, attempt), maxReconnectDelay);
    // Add jitter to prevent thundering herd
    return delay + Math.random() * 1000;
  };

  // Default WebSocket URL if not provided
  const getDefaultWsUrl = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const frontendHost = window.location.hostname;
    return `${wsProtocol}//${frontendHost}:8007/ws`; // Use stable server port
  };

  // Clear all timers
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

  // Start heartbeat
  const startHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    
    heartbeatIntervalRef.current = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, heartbeatInterval);
  }, []);

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      return;
    }

    const url = wsUrl || getDefaultWsUrl();
    console.log(`Connecting to WebSocket (attempt ${reconnectAttempts + 1}):`, url);
    
    try {
      ws.current = new WebSocket(url);
      
      // Connection timeout
      const timeoutId = setTimeout(() => {
        if (ws.current && ws.current.readyState === WebSocket.CONNECTING) {
          ws.current.close();
          console.log('WebSocket connection timeout');
        }
      }, connectionTimeout);

      ws.current.onopen = () => {
        clearTimeout(timeoutId);
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setConnectionStatus('connected');
        setReconnectAttempts(0);
        setError(null);
        setLastUpdate(new Date());
        startHeartbeat();
      };

      ws.current.onclose = (event) => {
        clearTimeout(timeoutId);
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        setLastUpdate(new Date());
        stopHeartbeat();

        // Attempt to reconnect if not manually closed and within max attempts
        if (!manualDisconnect.current && event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          const nextAttempt = reconnectAttempts + 1;
          const delay = getReconnectDelay(nextAttempt);
          
          setReconnectAttempts(nextAttempt);
          setError(`Connection lost. Reconnecting in ${Math.round(delay / 1000)}s... (attempt ${nextAttempt}/${maxReconnectAttempts})`);
          
          console.log(`Attempting to reconnect (${nextAttempt}/${maxReconnectAttempts}) in ${Math.round(delay)}ms...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setError('Failed to reconnect after maximum attempts. Please refresh the page.');
        }
      };

      ws.current.onerror = (errorEvent) => {
        clearTimeout(timeoutId);
        console.error('WebSocket error:', errorEvent);
        setConnectionStatus('error');
        setError('Connection error occurred');
        setLastUpdate(new Date());
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
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
              setSessions(prev => ({
                ...prev,
                [data.data.id]: data.data
              }));
              break;
            case 'connection_status':
              setConnectionStatus(data.status);
              if (data.connection_id) {
                console.log('Connection ID:', data.connection_id);
              }
              break;
            case 'heartbeat':
              // Update connection stats if available
              if (data.active_connections !== undefined) {
                setConnectionStats(prev => ({
                  ...prev,
                  active_connections: data.active_connections
                }));
              }
              break;
            case 'pong':
              // Heartbeat response received
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
            case 'error':
              console.error('Server error:', data.message);
              setError(data.message);
              break;
            case 'ping':
              // Respond to server ping
              sendMessage({ type: 'pong' });
              break;
            default:
              console.log('Unknown WebSocket message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setError('Error processing server message');
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
      setError('Failed to establish connection');
    }
  }, [wsUrl, reconnectAttempts, startHeartbeat, stopHeartbeat]);

  // Disconnect from WebSocket
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

  // Send message to WebSocket
  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        setError('Failed to send message');
        return false;
      }
    } else {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
  }, []);

  // Start session
  const startSession = useCallback(async (sessionConfig) => {
    try {
      const response = await fetch('/api/v1/sessions/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sessionConfig),
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        // Start the session
        const startResponse = await fetch(`/api/v1/sessions/${result.session_id}/start`, {
          method: 'POST',
        });
        
        const startResult = await startResponse.json();
        
        if (startResult.status === 'success') {
          console.log('Session started successfully:', result.session_id);
        }
      }
      
      return result;
    } catch (error) {
      console.error('Error starting session:', error);
      setError('Failed to start session');
      throw error;
    }
  }, []);

  // Stop session
  const stopSession = useCallback(async (sessionId) => {
    try {
      const response = await fetch(`/api/v1/sessions/${sessionId}/stop`, {
        method: 'POST',
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        console.log('Session stopped successfully:', sessionId);
      }
      
      return result;
    } catch (error) {
      console.error('Error stopping session:', error);
      setError('Failed to stop session');
      throw error;
    }
  }, []);

  // Get connection statistics
  const getConnectionStats = useCallback(async () => {
    try {
      const response = await fetch('/ws-stats');
      const stats = await response.json();
      setConnectionStats(stats);
      return stats;
    } catch (error) {
      console.error('Error getting connection stats:', error);
      return null;
    }
  }, []);

  // Initialize connection on mount
  useEffect(() => {
    manualDisconnect.current = false;
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
    };
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
    error,
    startSession,
    stopSession,
    sendMessage,
    connect,
    disconnect,
    getConnectionStats,
    clearError: () => setError(null)
  };
};