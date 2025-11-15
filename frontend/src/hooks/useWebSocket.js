import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [audioSpectrum, setAudioSpectrum] = useState([]);
  const [sessions, setSessions] = useState({});
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  
  const ws = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000; // 3 seconds

  const connect = useCallback(() => {
    try {
      // Use WebSocket with proper protocol detection
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//localhost:8000/ws`;
      
      console.log('Connecting to WebSocket:', wsUrl);
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionStatus('connected');
        setReconnectAttempts(0);
        setLastUpdate(new Date());
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        setLastUpdate(new Date());
        
        // Attempt to reconnect if not manually closed
        if (event.code !== 1000 && reconnectAttempts < maxReconnectAttempts) {
          const nextAttempt = reconnectAttempts + 1;
          setReconnectAttempts(nextAttempt);
          
          console.log(`Attempting to reconnect (${nextAttempt}/${maxReconnectAttempts}) in ${reconnectDelay}ms...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        setLastUpdate(new Date());
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          switch (data.type) {
            case 'realtime_data':
              setAudioSpectrum(data.audio_spectrum || []);
              setSessions(data.active_sessions || {});
              setLastUpdate(new Date(data.timestamp * 1000)); // Convert timestamp to Date
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
              break;
            default:
              console.log('Unknown WebSocket message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionStatus('error');
    }
  }, [reconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus('disconnected');
    setReconnectAttempts(0);
  }, []);

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    }
    return false;
  }, []);

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
      throw error;
    }
  }, []);

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
      throw error;
    }
  }, []);

  // Initialize connection on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    isConnected,
    audioSpectrum,
    sessions,
    connectionStatus,
    lastUpdate,
    reconnectAttempts,
    startSession,
    stopSession,
    sendMessage,
    connect,
    disconnect
  };
};