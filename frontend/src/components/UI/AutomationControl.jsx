/**
 * Automation Control Panel
 *
 * Controls for automated blessing rotation through populations.
 * Start/stop/pause automation, monitor progress, view queue.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Square, RotateCw, Clock, Users, Zap, TrendingUp, Info } from 'lucide-react';

const API_BASE = 'http://localhost:8001/api/v1';

const AutomationControl = ({ className = '' }) => {
  const [sessionId, setSessionId] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Config
  const [durationPerPop, setDurationPerPop] = useState(1800); // 30 min default
  const [transitionPause, setTransitionPause] = useState(30);
  const [linkRng, setLinkRng] = useState(true);
  const [continuousMode, setContinuousMode] = useState(true);

  // Status
  const [currentStatus, setCurrentStatus] = useState(null);
  const [stats, setStats] = useState(null);
  const [queue, setQueue] = useState([]);

  const statusInterval = useRef(null);

  // Load status periodically
  useEffect(() => {
    if (isActive && sessionId) {
      loadStatus();
      loadQueue();

      statusInterval.current = setInterval(() => {
        loadStatus();
      }, 5000); // Every 5 seconds

      return () => {
        if (statusInterval.current) clearInterval(statusInterval.current);
      };
    }
  }, [isActive, sessionId]);

  const startAutomation = async () => {
    try {
      const response = await fetch(`${API_BASE}/automation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'round_robin',
          duration_per_population: durationPerPop,
          transition_pause: transitionPause,
          link_rng: linkRng,
          auto_dedicate: true,
          continuous_mode: continuousMode,
          only_active: true,
          min_priority: 1
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setIsActive(true);
        setIsPaused(false);
        console.log('Automation started:', data);
      }
    } catch (error) {
      console.error('Failed to start automation:', error);
    }
  };

  const stopAutomation = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/automation/${sessionId}/stop`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data);
        setIsActive(false);
        setIsPaused(false);
        setSessionId(null);
      }
    } catch (error) {
      console.error('Failed to stop automation:', error);
    }
  };

  const pauseAutomation = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/automation/${sessionId}/pause`, {
        method: 'POST'
      });
      setIsPaused(true);
    } catch (error) {
      console.error('Failed to pause automation:', error);
    }
  };

  const resumeAutomation = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/automation/${sessionId}/resume`, {
        method: 'POST'
      });
      setIsPaused(false);
    } catch (error) {
      console.error('Failed to resume automation:', error);
    }
  };

  const loadStatus = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/automation/${sessionId}/status`);
      if (response.ok) {
        const data = await response.json();
        setCurrentStatus(data);
      }
    } catch (error) {
      console.error('Failed to load status:', error);
    }
  };

  const loadQueue = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/automation/${sessionId}/queue`);
      if (response.ok) {
        const data = await response.json();
        setQueue(data);
      }
    } catch (error) {
      console.error('Failed to load queue:', error);
    }
  };

  const loadStats = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/automation/${sessionId}/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hours}h ${remainMins}m`;
  };

  return (
    <div className={`bg-gray-800 rounded-lg ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900/50 to-blue-900/50 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RotateCw className={`w-6 h-6 text-purple-400 ${isActive && !isPaused ? 'animate-spin' : ''}`} />
            <h2 className="text-xl font-bold text-white">Automated Compassion</h2>
          </div>
          {isActive && !isPaused && (
            <div className="flex items-center gap-2 text-sm">
              <Zap className="w-4 h-4 text-yellow-400 animate-pulse" />
              <span className="text-yellow-400">Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Configuration (when not active) */}
      {!isActive && (
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            {/* Duration per population */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Duration per Population
              </label>
              <select
                value={durationPerPop}
                onChange={(e) => setDurationPerPop(parseInt(e.target.value))}
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
              >
                <option value={600}>10 minutes</option>
                <option value={900}>15 minutes</option>
                <option value={1200}>20 minutes</option>
                <option value={1800}>30 minutes</option>
                <option value={2700}>45 minutes</option>
                <option value={3600}>60 minutes</option>
              </select>
            </div>

            {/* Transition pause */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Transition Pause
              </label>
              <select
                value={transitionPause}
                onChange={(e) => setTransitionPause(parseInt(e.target.value))}
                className="w-full bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
              >
                <option value={0}>None</option>
                <option value={15}>15 seconds</option>
                <option value={30}>30 seconds</option>
                <option value={60}>1 minute</option>
              </select>
            </div>
          </div>

          {/* Options */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={linkRng}
                onChange={(e) => setLinkRng(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-300">Link RNG Monitoring</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={continuousMode}
                onChange={(e) => setContinuousMode(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-300">Continuous Mode (Loop Forever)</span>
            </label>
          </div>

          {/* Start Button */}
          <button
            onClick={startAutomation}
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white py-3 px-4 rounded-lg font-semibold transition-all transform hover:scale-105 flex items-center justify-center gap-2"
          >
            <Play className="w-5 h-5" />
            Begin Automated Rotation
          </button>

          {/* Final Stats (after stop) */}
          {stats && (
            <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                Last Session Complete
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-800/50 p-3 rounded-lg">
                  <div className="text-xs text-gray-400">Populations Blessed</div>
                  <div className="text-2xl font-bold text-white">{stats.completed_sessions}</div>
                </div>
                <div className="bg-gray-800/50 p-3 rounded-lg">
                  <div className="text-xs text-gray-400">Total Mantras</div>
                  <div className="text-2xl font-bold text-purple-400">
                    {stats.total_mantras.toLocaleString()}
                  </div>
                </div>
                <div className="bg-gray-800/50 p-3 rounded-lg">
                  <div className="text-xs text-gray-400">Photos Blessed</div>
                  <div className="text-2xl font-bold text-white">{stats.total_photos_blessed}</div>
                </div>
                <div className="bg-gray-800/50 p-3 rounded-lg">
                  <div className="text-xs text-gray-400">Floating Needles</div>
                  <div className="text-2xl font-bold text-green-400">{stats.total_rng_floating_needles}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active Session */}
      {isActive && currentStatus && (
        <div className="p-6 space-y-6">
          {/* Current Population */}
          {currentStatus.current_population && (
            <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-2">Currently Blessing</div>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-white mb-2">
                    {currentStatus.current_population.name}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-gray-300">
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {currentStatus.current_population.photo_count} photos
                    </span>
                    <span>Priority: {currentStatus.current_population.priority}</span>
                    <span>{currentStatus.current_population.mantra}</span>
                  </div>
                </div>
              </div>

              {/* Progress */}
              <div className="mt-4">
                <div className="flex justify-between text-sm text-gray-400 mb-1">
                  <span>{formatTime(currentStatus.elapsed_seconds)} / {formatDuration(currentStatus.target_duration)}</span>
                  <span>{currentStatus.progress_percentage.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(100, currentStatus.progress_percentage)}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Controls */}
          <div className="flex gap-2">
            {!isPaused ? (
              <button
                onClick={pauseAutomation}
                className="flex-1 bg-amber-600 hover:bg-amber-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
              >
                <Pause className="w-4 h-4" />
                Pause
              </button>
            ) : (
              <button
                onClick={resumeAutomation}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
              >
                <Play className="w-4 h-4" />
                Resume
              </button>
            )}

            <button
              onClick={loadStats}
              className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center gap-2"
            >
              <TrendingUp className="w-4 h-4" />
              Stats
            </button>

            <button
              onClick={stopAutomation}
              className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center gap-2"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
          </div>

          {/* Queue Preview */}
          {queue.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-300 mb-3">Next in Queue</h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {queue.slice(0, 5).filter(item => !item.is_current).map(item => (
                  <div key={item.id} className="bg-gray-900 rounded-lg p-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-white font-medium">{item.name}</span>
                      {item.is_urgent && <span className="text-red-400">🔥</span>}
                    </div>
                    <div className="text-gray-400 text-xs mt-1">
                      {item.photo_count} photos • Priority {item.priority}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current Stats */}
          {stats && (
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <div className="text-xs text-gray-400">Session Duration</div>
                  <div className="text-lg font-bold text-white">
                    {formatDuration(stats.total_duration)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Cycles</div>
                  <div className="text-lg font-bold text-white">{stats.cycle_count}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Populations Done</div>
                  <div className="text-lg font-bold text-white">{stats.completed_sessions}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">Total Mantras</div>
                  <div className="text-lg font-bold text-purple-400">
                    {stats.total_mantras.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info */}
      <div className="p-4 bg-purple-900/20 border-t border-purple-500/30">
        <div className="flex items-start gap-2">
          <Info className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <p className="mb-1">
              <strong className="text-purple-400">Automated Rotation</strong> - Cycles through active populations.
            </p>
            <p>
              Each population receives blessings for the configured duration.
              RNG monitoring provides real-time feedback on energetic connection.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AutomationControl;
