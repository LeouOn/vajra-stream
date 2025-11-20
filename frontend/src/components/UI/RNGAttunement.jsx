/**
 * RNG Attunement Display Component
 * Inspired by E-meter and Ken Ogger's Super Scio work
 * Displays quantum-random readings that may be influenced by consciousness
 */

import React, { useState, useEffect, useRef } from 'react';
import { Activity, TrendingUp, TrendingDown, Minus, Zap, AlertCircle, CheckCircle } from 'lucide-react';

const API_BASE = 'http://localhost:8003/api/v1';

// Needle state colors
const NEEDLE_COLORS = {
  floating: '#10b981',    // green - release/EP
  rising: '#f59e0b',      // amber - building charge
  falling: '#3b82f6',     // blue - releasing
  rockslam: '#ef4444',    // red - heavy charge
  theta_bop: '#8b5cf6',   // purple - rhythmic
  stuck: '#6b7280'        // gray - neutral
};

// Quality level colors
const QUALITY_COLORS = {
  excellent: '#10b981',   // green
  good: '#3b82f6',        // blue
  fair: '#f59e0b',        // amber
  poor: '#ef4444',        // red
  disrupted: '#dc2626'    // dark red
};

const RNGAttunement = ({ className = '' }) => {
  const [sessionId, setSessionId] = useState(null);
  const [isActive, setIsActive] = useState(false);
  const [reading, setReading] = useState(null);
  const [history, setHistory] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshRate, setRefreshRate] = useState(1000); // ms
  const [sensitivity, setSensitivity] = useState(1.0);
  const [baselineToneArm, setBaselineToneArm] = useState(5.0);
  const [summary, setSummary] = useState(null);

  const intervalRef = useRef(null);
  const canvasRef = useRef(null);

  // Create session
  const createSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/rng-attunement/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseline_tone_arm: baselineToneArm,
          sensitivity: sensitivity
        })
      });
      const data = await response.json();
      setSessionId(data.session_id);
      setIsActive(true);
      setHistory([]);
      console.log('RNG session created:', data.session_id);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  // Get reading
  const getReading = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/rng-attunement/reading/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setReading(data);
        setHistory(prev => [...prev.slice(-99), data]); // Keep last 100
      }
    } catch (error) {
      console.error('Failed to get reading:', error);
    }
  };

  // Get session summary
  const getSummary = async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(`${API_BASE}/rng-attunement/session/${sessionId}/summary`);
      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to get summary:', error);
    }
  };

  // Stop session
  const stopSession = async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE}/rng-attunement/session/${sessionId}/stop`, {
        method: 'POST'
      });
      setIsActive(false);
      setAutoRefresh(false);
      await getSummary();
    } catch (error) {
      console.error('Failed to stop session:', error);
    }
  };

  // Auto-refresh readings
  useEffect(() => {
    if (autoRefresh && isActive) {
      intervalRef.current = setInterval(getReading, refreshRate);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, isActive, refreshRate, sessionId]);

  // Draw needle visualization
  useEffect(() => {
    if (!canvasRef.current || !reading) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height - 20;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw background arc
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 100, Math.PI, 2 * Math.PI);
    ctx.stroke();

    // Draw scale marks
    ctx.strokeStyle = '#4b5563';
    ctx.lineWidth = 1;
    for (let i = -100; i <= 100; i += 20) {
      const angle = Math.PI + (Math.PI * (i + 100) / 200);
      const innerR = 90;
      const outerR = i % 40 === 0 ? 105 : 100;
      const x1 = centerX + innerR * Math.cos(angle);
      const y1 = centerY + innerR * Math.sin(angle);
      const x2 = centerX + outerR * Math.cos(angle);
      const y2 = centerY + outerR * Math.sin(angle);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();

      // Draw labels for major marks
      if (i % 40 === 0) {
        ctx.fillStyle = '#9ca3af';
        ctx.font = '10px monospace';
        ctx.textAlign = 'center';
        const labelR = 115;
        const labelX = centerX + labelR * Math.cos(angle);
        const labelY = centerY + labelR * Math.sin(angle);
        ctx.fillText(i.toString(), labelX, labelY + 4);
      }
    }

    // Draw needle
    const needleAngle = Math.PI + (Math.PI * (reading.needle_position + 100) / 200);
    const needleLength = 85;
    const needleX = centerX + needleLength * Math.cos(needleAngle);
    const needleY = centerY + needleLength * Math.sin(needleAngle);

    // Needle color based on state
    const needleColor = NEEDLE_COLORS[reading.needle_state] || '#9ca3af';

    // Draw needle shadow
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(centerX + 2, centerY + 2);
    ctx.lineTo(needleX + 2, needleY + 2);
    ctx.stroke();

    // Draw needle
    ctx.strokeStyle = needleColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(needleX, needleY);
    ctx.stroke();

    // Draw center dot
    ctx.fillStyle = needleColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
    ctx.fill();

    // Draw needle tip
    ctx.beginPath();
    ctx.arc(needleX, needleY, 3, 0, 2 * Math.PI);
    ctx.fill();

  }, [reading]);

  // Render trend indicator
  const renderTrend = () => {
    if (!reading) return null;

    if (reading.trend > 1) {
      return <TrendingUp className="w-4 h-4 text-amber-500" />;
    } else if (reading.trend < -1) {
      return <TrendingDown className="w-4 h-4 text-blue-500" />;
    } else {
      return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className={`bg-gray-800 rounded-lg p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold text-white">RNG Attunement</h2>
        </div>
        <div className="flex items-center gap-2">
          {isActive && (
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-gray-400">Active</span>
            </div>
          )}
        </div>
      </div>

      {/* Session Controls */}
      {!sessionId ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Baseline Tone Arm (0-10)
              </label>
              <input
                type="range"
                min="0"
                max="10"
                step="0.5"
                value={baselineToneArm}
                onChange={(e) => setBaselineToneArm(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="text-sm text-white text-center mt-1">
                {baselineToneArm.toFixed(1)}
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                Sensitivity (0.1-5.0)
              </label>
              <input
                type="range"
                min="0.1"
                max="5.0"
                step="0.1"
                value={sensitivity}
                onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="text-sm text-white text-center mt-1">
                {sensitivity.toFixed(1)}
              </div>
            </div>
          </div>
          <button
            onClick={createSession}
            className="w-full bg-purple-600 hover:bg-purple-700 text-white py-3 px-4 rounded-lg font-semibold transition-colors"
          >
            Start Attunement Session
          </button>
        </div>
      ) : (
        <>
          {/* Needle Visualization */}
          <div className="mb-6 bg-gray-900 rounded-lg p-4">
            <canvas
              ref={canvasRef}
              width={400}
              height={200}
              className="w-full"
              style={{ maxWidth: '400px', margin: '0 auto', display: 'block' }}
            />
          </div>

          {/* Current Reading */}
          {reading && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {/* Tone Arm */}
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Tone Arm</div>
                <div className="text-2xl font-bold text-white">
                  {reading.tone_arm.toFixed(2)}
                </div>
                <div className="text-xs text-gray-500">0-10 scale</div>
              </div>

              {/* Needle Position */}
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                  Needle {renderTrend()}
                </div>
                <div className="text-2xl font-bold text-white">
                  {reading.needle_position.toFixed(1)}
                </div>
                <div className="text-xs text-gray-500">-100 to +100</div>
              </div>

              {/* Coherence */}
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">Coherence</div>
                <div className="text-2xl font-bold text-white">
                  {(reading.coherence * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-gray-500">Order/Pattern</div>
              </div>

              {/* FN Score */}
              <div className="bg-gray-900 rounded-lg p-3">
                <div className="text-xs text-gray-400 mb-1">FN Score</div>
                <div className="text-2xl font-bold text-white">
                  {(reading.floating_needle_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-gray-500">Release likelihood</div>
              </div>
            </div>
          )}

          {/* Needle State & Quality */}
          {reading && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* Needle State */}
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-2">Needle State</div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: NEEDLE_COLORS[reading.needle_state] }}
                  />
                  <span className="text-lg font-semibold text-white uppercase tracking-wide">
                    {reading.needle_state.replace('_', ' ')}
                  </span>
                </div>
                {reading.needle_state === 'floating' && (
                  <div className="mt-2 flex items-center gap-1 text-green-400 text-sm">
                    <CheckCircle className="w-4 h-4" />
                    <span>Release/EP Detected</span>
                  </div>
                )}
              </div>

              {/* Quality */}
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="text-xs text-gray-400 mb-2">Signal Quality</div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: QUALITY_COLORS[reading.quality] }}
                  />
                  <span className="text-lg font-semibold text-white uppercase tracking-wide">
                    {reading.quality}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Controls */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <button
              onClick={getReading}
              disabled={!isActive}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors"
            >
              Get Reading
            </button>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              disabled={!isActive}
              className={`${
                autoRefresh ? 'bg-amber-600 hover:bg-amber-700' : 'bg-green-600 hover:bg-green-700'
              } disabled:bg-gray-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2`}
            >
              <Zap className="w-4 h-4" />
              {autoRefresh ? 'Stop Auto' : 'Start Auto'}
            </button>
          </div>

          {autoRefresh && (
            <div className="mb-4">
              <label className="block text-xs text-gray-400 mb-1">
                Refresh Rate: {refreshRate}ms
              </label>
              <input
                type="range"
                min="100"
                max="5000"
                step="100"
                value={refreshRate}
                onChange={(e) => setRefreshRate(parseInt(e.target.value))}
                className="w-full"
              />
            </div>
          )}

          {/* Session Info */}
          <div className="bg-gray-900 rounded-lg p-4 mb-4">
            <div className="text-xs text-gray-400 mb-2">Session Info</div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Session ID:</span>
                <div className="text-white font-mono text-xs mt-1">
                  {sessionId.slice(0, 20)}...
                </div>
              </div>
              <div>
                <span className="text-gray-400">Readings:</span>
                <div className="text-white font-semibold mt-1">
                  {history.length}
                </div>
              </div>
            </div>
          </div>

          {/* Summary (when stopped) */}
          {summary && !isActive && (
            <div className="bg-gray-900 rounded-lg p-4 mb-4">
              <div className="text-sm font-semibold text-white mb-3">Session Summary</div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-400">Total Readings:</span>
                  <div className="text-white font-semibold">{summary.total_readings}</div>
                </div>
                <div>
                  <span className="text-gray-400">Floating Needles:</span>
                  <div className="text-green-400 font-semibold">{summary.floating_needle_count}</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Tone Arm:</span>
                  <div className="text-white font-semibold">{summary.avg_tone_arm?.toFixed(2)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Coherence:</span>
                  <div className="text-white font-semibold">{(summary.avg_coherence * 100)?.toFixed(0)}%</div>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={getSummary}
              className="bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-lg font-semibold transition-colors"
            >
              Get Summary
            </button>
            <button
              onClick={stopSession}
              disabled={!isActive}
              className="bg-red-600 hover:bg-red-700 disabled:bg-gray-700 text-white py-2 px-4 rounded-lg font-semibold transition-colors"
            >
              Stop Session
            </button>
          </div>
        </>
      )}

      {/* Info */}
      <div className="mt-6 p-4 bg-purple-900/20 border border-purple-500/30 rounded-lg">
        <div className="flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-300">
            <p className="mb-2">
              <strong className="text-purple-400">RNG Attunement Reading</strong> - Inspired by E-meter technology and Ken Ogger's Super Scio work.
            </p>
            <p className="mb-1"><strong>Floating Needle:</strong> Indicates release, end phenomenon (EP). Good sign to end process.</p>
            <p className="mb-1"><strong>Rising:</strong> Building charge on item being addressed.</p>
            <p className="mb-1"><strong>Falling:</strong> Releasing charge, processing occurring.</p>
            <p><strong>Rockslam:</strong> Heavy charge, significant material being addressed.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RNGAttunement;
