import React, { useState } from 'react';
import { Play, Square, Plus, Clock, Zap, Heart } from 'lucide-react';

const SessionManager = ({ sessions, onStartSession, onStopSession, isConnected }) => {
  const [sessionName, setSessionName] = useState('');
  const [sessionIntention, setSessionIntention] = useState('');
  const [sessionDuration, setSessionDuration] = useState(3600); // 1 hour default
  const [audioFrequency, setAudioFrequency] = useState(136.1); // OM frequency
  const [showCreateForm, setShowCreateForm] = useState(false);

  const handleStartSession = async () => {
    if (!sessionName.trim() || !sessionIntention.trim()) {
      alert('Please enter both session name and intention');
      return;
    }

    const sessionConfig = {
      name: sessionName,
      intention: sessionIntention,
      duration: sessionDuration,
      audio_frequency: audioFrequency,
      astrology_enabled: true,
      hardware_enabled: true,
      visuals_enabled: true
    };

    try {
      const result = await onStartSession(sessionConfig);
      if (result.status === 'success') {
        setSessionName('');
        setSessionIntention('');
        setShowCreateForm(false);
        console.log('Session started successfully');
      }
    } catch (error) {
      console.error('Failed to start session:', error);
      alert('Failed to start session. Please try again.');
    }
  };

  const handleStopSession = async (sessionId) => {
    try {
      const result = await onStopSession(sessionId);
      if (result.status === 'success') {
        console.log('Session stopped successfully');
      }
    } catch (error) {
      console.error('Failed to stop session:', error);
      alert('Failed to stop session. Please try again.');
    }
  };

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const getSessionIcon = (frequency) => {
    if (frequency >= 100 && frequency <= 150) return <Heart className="w-4 h-4" />;
    if (frequency >= 500 && frequency <= 550) return <Zap className="w-4 h-4" />;
    return <Clock className="w-4 h-4" />;
  };

  const getSessionType = (frequency) => {
    if (frequency >= 100 && frequency <= 150) return 'Heart Coherence';
    if (frequency >= 500 && frequency <= 550) return 'Love Frequency';
    if (frequency >= 7 && frequency <= 10) return 'Earth Resonance';
    return 'Custom Frequency';
  };

  const activeSessions = Object.values(sessions);
  const runningSessions = activeSessions.filter(s => s.status === 'running');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4 text-vajra-purple flex items-center">
          <Clock className="w-5 h-5 mr-2" />
          Session Manager
        </h2>
        
        {/* Connection Status */}
        {!isConnected && (
          <div className="mb-4 p-3 bg-red-900 bg-opacity-50 border border-red-700 rounded-lg">
            <p className="text-sm text-red-300">
              ⚠️ Disconnected from backend. Session management unavailable.
            </p>
          </div>
        )}

        {/* Create New Session */}
        <div className="mb-6">
          {!showCreateForm ? (
            <button
              onClick={() => setShowCreateForm(true)}
              disabled={!isConnected}
              className="w-full vajra-button vajra-button-primary flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create New Session
            </button>
          ) : (
            <div className="vajra-panel space-y-4">
              <h3 className="text-lg font-semibold text-vajra-cyan">New Blessing Session</h3>
              
              {/* Session Name */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Session Name
                </label>
                <input
                  type="text"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  placeholder="Enter session name"
                  className="vajra-input"
                />
              </div>

              {/* Intention */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Intention
                </label>
                <textarea
                  value={sessionIntention}
                  onChange={(e) => setSessionIntention(e.target.value)}
                  placeholder="Enter your intention for this session"
                  rows={3}
                  className="vajra-input resize-none"
                />
              </div>

              {/* Duration */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Duration: {formatDuration(sessionDuration)}
                </label>
                <select
                  value={sessionDuration}
                  onChange={(e) => setSessionDuration(parseInt(e.target.value))}
                  className="vajra-input"
                >
                  <option value={600}>10 minutes</option>
                  <option value={900}>15 minutes</option>
                  <option value={1800}>30 minutes</option>
                  <option value={3600}>1 hour</option>
                  <option value={7200}>2 hours</option>
                  <option value={14400}>4 hours</option>
                </select>
              </div>

              {/* Frequency */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Frequency: {audioFrequency.toFixed(1)} Hz
                </label>
                <select
                  value={audioFrequency}
                  onChange={(e) => setAudioFrequency(parseFloat(e.target.value))}
                  className="vajra-input"
                >
                  <option value={136.1}>OM Frequency (136.1 Hz)</option>
                  <option value={528.0}>Love Frequency (528 Hz)</option>
                  <option value={7.83}>Earth Resonance (7.83 Hz)</option>
                  <option value={432.0}>Verdi Tuning (432 Hz)</option>
                  <option value={396.0}>Liberation (396 Hz)</option>
                </select>
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-2">
                <button
                  onClick={handleStartSession}
                  className="flex-1 vajra-button vajra-button-success"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Start Session
                </button>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 vajra-button vajra-button-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Active Sessions */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-vajra-cyan">
            Active Sessions ({runningSessions.length})
          </h3>
          
          {activeSessions.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Clock className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No active sessions</p>
              <p className="text-xs mt-1">Create a session to begin your blessing practice</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeSessions.map((session) => (
                <div 
                  key={session.id} 
                  className={`session-card ${session.status === 'running' ? 'active' : ''}`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h4 className="font-medium flex items-center">
                        {getSessionIcon(session.audio_frequency)}
                        <span className="ml-2">{session.name}</span>
                      </h4>
                      <p className="text-sm text-gray-400 mt-1">{session.intention}</p>
                      <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                        <span>{getSessionType(session.audio_frequency)}</span>
                        <span>{formatDuration(session.duration)}</span>
                        <span>{session.audio_frequency.toFixed(1)} Hz</span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <span className={`px-2 py-1 text-xs rounded font-medium ${
                        session.status === 'running' 
                          ? 'bg-green-600 text-white' 
                          : session.status === 'created'
                          ? 'bg-yellow-600 text-white'
                          : 'bg-gray-600 text-gray-300'
                      }`}>
                        {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                      </span>
                      
                      {session.status === 'running' && (
                        <button
                          onClick={() => handleStopSession(session.id)}
                          className="vajra-button vajra-button-danger text-xs px-2 py-1"
                        >
                          <Square className="w-3 h-3 mr-1" />
                          Stop
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {/* Session Progress */}
                  {session.status === 'running' && session.start_time && (
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>Session Progress</span>
                        <span>Active</span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2">
                        <div className="bg-gradient-to-r from-vajra-cyan to-vajra-purple h-2 rounded-full animate-pulse" 
                             style={{ width: '100%' }} />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Session Statistics */}
        {activeSessions.length > 0 && (
          <div className="mt-6 p-4 bg-gray-700 rounded-lg">
            <h3 className="text-sm font-semibold mb-3 text-vajra-cyan">Session Statistics</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Total Sessions:</span>
                <span className="ml-2 font-medium">{activeSessions.length}</span>
              </div>
              <div>
                <span className="text-gray-400">Running:</span>
                <span className="ml-2 font-medium text-green-400">{runningSessions.length}</span>
              </div>
              <div>
                <span className="text-gray-400">Avg Frequency:</span>
                <span className="ml-2 font-medium">
                  {(activeSessions.reduce((sum, s) => sum + s.audio_frequency, 0) / activeSessions.length).toFixed(1)} Hz
                </span>
              </div>
              <div>
                <span className="text-gray-400">Total Duration:</span>
                <span className="ml-2 font-medium">
                  {formatDuration(activeSessions.reduce((sum, s) => sum + s.duration, 0))}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionManager;