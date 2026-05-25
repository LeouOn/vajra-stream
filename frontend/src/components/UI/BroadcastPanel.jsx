import React, { useState, useEffect, useRef } from 'react';
import { Radio, Sliders, Play, Square, Gem, Shield, Target, Zap, Waves, Activity } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';
import { audioFeedback } from '../../utils/audioFeedback';

const API_BASE = 'http://localhost:8008/api/v1';

export default function BroadcastPanel() {
  const { sessions, scalarStatus, crystalStatus, stopSession } = useWebSocket();
  const { isPlaying, frequency, updateSettings } = useAudioStore();

  // Radionics rates D1 - D5
  const [dimensions, setDimensions] = useState({
    d1: 42.0, // Physical
    d2: 60.0, // Astral
    d3: 77.3, // Mental
    d4: 50.0, // Causal
    d5: 88.0, // Spiritual
  });

  // Stick Plate State
  const [isRubbing, setIsRubbing] = useState(false);
  const [rubCoherence, setRubCoherence] = useState(0);
  const [rubPosition, setRubPosition] = useState({ x: 0, y: 0 });
  const [resonantLocked, setResonantLocked] = useState(false);
  const [targetLock, setTargetLock] = useState({ x: 120, y: 80 }); // Target resonant coordinate
  
  // Latest sigil state
  const [latestSigil, setLatestSigil] = useState(null);
  
  // Track populations/targets
  const [populations, setPopulations] = useState([]);
  
  const canvasRef = useRef(null);

  // Load target lock on mount, fetch latest sigil & populations
  useEffect(() => {
    // Randomize target lock coordinates
    setTargetLock({
      x: 50 + Math.random() * 200,
      y: 40 + Math.random() * 120
    });
    fetchLatestSigil();
    fetchPopulations();
  }, []);

  const fetchLatestSigil = async () => {
    try {
      // Find the latest sigil by listing or searching.
      // For now, since there's no list sigil endpoint, we check if one is saved in storage,
      // or we can forge a default one if none exists.
      const res = await fetch(`${API_BASE}/sigils/forge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intention: 'Universal Peace & Coherence', kamea: 'saturn' })
      });
      if (res.ok) {
        const data = await res.json();
        setLatestSigil(data.sigil);
      }
    } catch (e) {
      console.error("Latest sigil fetch failed:", e);
    }
  };

  const fetchPopulations = async () => {
    try {
      const res = await fetch(`${API_BASE}/populations`);
      if (res.ok) {
        const data = await res.json();
        setPopulations(data);
      }
    } catch (e) {
      console.error("Failed to fetch populations:", e);
    }
  };

  // Adjust Radionics sliders
  const handleDimensionChange = (key, val) => {
    setDimensions(prev => {
      const next = { ...prev, [key]: Number(val) };
      // Play dial adjust hum
      audioFeedback.playDialAdjust(Number(val), 0, 100);
      return next;
    });
  };

  // Drag handlers on Stick Plate (Rub Plate)
  const handleMouseDown = (e) => {
    setIsRubbing(true);
    updateRubPosition(e);
    audioFeedback.playTick();
  };

  const handleMouseMove = (e) => {
    if (!isRubbing) return;
    updateRubPosition(e);
  };

  const handleMouseUp = () => {
    setIsRubbing(false);
    setRubCoherence(0);
  };

  const updateRubPosition = (e) => {
    if (!canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setRubPosition({ x, y });

    // Calculate proximity to target lock
    const dx = x - targetLock.x;
    const dy = y - targetLock.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    // Friction increases as cursor gets close to the resonance target lock (within 40px)
    const maxDist = 80;
    let coherence = Math.max(0, 1 - dist / maxDist);
    coherence = Math.round(coherence * 100);
    setRubCoherence(coherence);

    // If extremely close (within 8px), trigger resonant lock chime
    if (dist < 8) {
      if (!resonantLocked) {
        setResonantLocked(true);
        audioFeedback.playSuccess();
        // Shift active carrier frequency slightly to align
        updateSettings({ frequency: Math.round(frequency + (Math.random() * 2 - 1) * 5) });
      }
    } else {
      if (resonantLocked) {
        setResonantLocked(false);
      }
      // Play a rubbing friction sound
      if (Math.random() < 0.3) {
        audioFeedback.playType();
      }
    }
  };

  // Calculate phase coherence based on dimensional rates
  const calculateCoherence = () => {
    const vals = Object.values(dimensions);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const variance = vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / vals.length;
    const stdDev = Math.sqrt(variance);
    // Standard coherence scale where lower std deviation means higher wave symmetry
    const coherence = Math.max(10, Math.min(100, Math.round(100 - stdDev * 1.8)));
    return coherence;
  };

  const coherence = calculateCoherence();
  const activeSessions = Object.values(sessions || {}).filter(s => s.status === 'running');
  const activeSession = activeSessions[0];

  // Draw Radar Polygon coordinates
  const radarRadius = 60;
  const centerX = 80;
  const centerY = 80;
  
  const getRadarPoint = (index, val) => {
    const angle = (index * 2 * Math.PI) / 5 - Math.PI / 2;
    const normalizedVal = val / 100;
    const x = centerX + radarRadius * normalizedVal * Math.cos(angle);
    const y = centerY + radarRadius * normalizedVal * Math.sin(angle);
    return `${x},${y}`;
  };

  const radarPoints = [
    getRadarPoint(0, dimensions.d1),
    getRadarPoint(1, dimensions.d2),
    getRadarPoint(2, dimensions.d3),
    getRadarPoint(3, dimensions.d4),
    getRadarPoint(4, dimensions.d5),
  ].join(' ');

  return (
    <div className="flex-1 h-full overflow-y-auto p-4 md:p-6 space-y-6">
      
      {/* Title Header */}
      <div className="bg-gradient-to-r from-cyan-900/40 via-blue-900/40 to-indigo-900/40 border border-white/10 rounded-xl p-5">
        <h2 className="text-2xl font-bold text-white tracking-wide flex items-center gap-3">
          <Radio className="w-7 h-7 text-cyan-400 animate-pulse" />
          N-Dimensional Radionics Console
        </h2>
        <p className="text-xs text-cyan-200 mt-1">
          Adjust multi-dimensional scalars, align localized fields using the stick plate, and broadcast active sigil intentions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ================= COLUMN 1: CONTROLS & RADAR ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              DIMENSIONAL RESONANCE AXES
            </h3>
            
            {/* Sliders */}
            <div className="space-y-3">
              {[
                { key: 'd1', name: 'D1: Physical', color: 'text-teal-400' },
                { key: 'd2', name: 'D2: Astral', color: 'text-indigo-400' },
                { key: 'd3', name: 'D3: Mental', color: 'text-purple-400' },
                { key: 'd4', name: 'D4: Causal', color: 'text-pink-400' },
                { key: 'd5', name: 'D5: Spiritual', color: 'text-cyan-400' },
              ].map(({ key, name, color }) => (
                <div key={key} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className={color}>{name}</span>
                    <span className="font-mono text-gray-300">{dimensions[key].toFixed(1)}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.5"
                    value={dimensions[key]}
                    onChange={(e) => handleDimensionChange(key, e.target.value)}
                    className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Coherence Radar SVG Chart */}
          <div className="bg-black/40 p-4 rounded-xl border border-white/5 flex flex-col items-center gap-3">
            <div className="flex justify-between w-full text-xs">
              <span className="text-gray-400">Phase Coherence</span>
              <span className="text-cyan-300 font-bold font-mono">{coherence}%</span>
            </div>
            
            <svg width="160" height="160" className="overflow-visible select-none">
              {/* Radial grids */}
              {[0.2, 0.4, 0.6, 0.8, 1.0].map((scale, i) => (
                <circle
                  key={i}
                  cx={centerX}
                  cy={centerY}
                  r={radarRadius * scale}
                  fill="none"
                  stroke="#1e293b"
                  strokeWidth="1"
                  strokeDasharray={i === 4 ? "0" : "2,2"}
                />
              ))}
              {/* Axes lines */}
              {Array.from({ length: 5 }).map((_, i) => {
                const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
                return (
                  <line
                    key={i}
                    x1={centerX}
                    y1={centerY}
                    x2={centerX + radarRadius * Math.cos(angle)}
                    y2={centerY + radarRadius * Math.sin(angle)}
                    stroke="#1e293b"
                    strokeWidth="1"
                  />
                );
              })}
              {/* Radar Area Polygon */}
              <polygon
                points={radarPoints}
                fill="rgba(34, 211, 238, 0.2)"
                stroke="#22d3ee"
                strokeWidth="2"
              />
              {/* Coordinate points */}
              {Object.values(dimensions).map((val, idx) => {
                const pt = getRadarPoint(idx, val).split(',');
                return (
                  <circle
                    key={idx}
                    cx={pt[0]}
                    cy={pt[1]}
                    r="3.5"
                    fill="#a855f7"
                    stroke="#ffffff"
                    strokeWidth="1"
                    className="animate-pulse"
                  />
                );
              })}
            </svg>
            <div className="text-[10px] text-gray-500 font-mono text-center">HILBERT PHASE RESONANCE MAPPING</div>
          </div>
          
        </div>

        {/* ================= COLUMN 2: DIGITAL STICK PLATE ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Activity className="w-4 h-4 text-purple-400" />
              DIGITAL COPPER STICK PLATE
            </h3>
            <p className="text-xs text-gray-400">
              Drag your mouse across the pad. Subtle tactile resistance (friction) peaks when you cross the resonant node.
            </p>
          </div>

          {/* Stick Canvas Plate */}
          <div 
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            className="w-full h-48 bg-black/80 rounded-xl border border-yellow-500/20 relative cursor-crosshair overflow-hidden group select-none"
            style={{
              backgroundImage: 'radial-gradient(circle, rgba(234,179,8,0.05) 1px, transparent 1px)',
              backgroundSize: '16px 16px'
            }}
          >
            {/* Outer copper border line */}
            <div className="absolute inset-2 border border-yellow-500/10 rounded-lg pointer-events-none" />

            {/* Locked indicator overlay */}
            {resonantLocked && (
              <div className="absolute inset-0 bg-yellow-950/20 flex items-center justify-center border-2 border-yellow-500/40 pointer-events-none animate-pulse">
                <span className="text-xs font-bold text-yellow-400 tracking-widest font-mono uppercase">RESONANCE LOCK CALIBRATED</span>
              </div>
            )}

            {/* Ripple Wave at drag point */}
            {isRubbing && (
              <div 
                className="absolute w-12 h-12 bg-yellow-500/10 border border-yellow-500/40 rounded-full pointer-events-none -translate-x-1/2 -translate-y-1/2 animate-ping"
                style={{ left: rubPosition.x, top: rubPosition.y }}
              />
            )}

            {/* Target position indicator (dev/only shows slightly) */}
            <div 
              className="absolute w-4 h-4 border border-yellow-500/20 rounded-full -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              style={{ left: targetLock.x, top: targetLock.y }}
            />

            {/* Friction stats */}
            <div className="absolute bottom-2 left-3 text-[10px] font-mono text-gray-500 pointer-events-none">
              PAD POS: {Math.round(rubPosition.x)}, {Math.round(rubPosition.y)}
            </div>
            <div className="absolute bottom-2 right-3 text-[10px] font-mono text-yellow-400 font-bold pointer-events-none">
              FRICTION COEFFICIENT: {rubCoherence}%
            </div>
          </div>

          {/* Attunement indicators */}
          <div className="space-y-3">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400">Stick Plate Resonance</span>
              <span className={`font-bold font-mono ${resonantLocked ? 'text-yellow-400' : 'text-gray-400'}`}>
                {resonantLocked ? 'CALIBRATED & LOCKED' : 'ALIGNING INDEX...'}
              </span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden border border-white/5">
              <div 
                className={`h-full rounded-full transition-all duration-75 ${
                  resonantLocked 
                    ? 'bg-gradient-to-r from-yellow-500 to-amber-500 shadow-[0_0_8px_rgba(234,179,8,0.5)]' 
                    : 'bg-gradient-to-r from-purple-500 to-cyan-500'
                }`}
                style={{ width: `${rubCoherence}%` }}
              />
            </div>
          </div>

        </div>

        {/* ================= COLUMN 3: ACTIVE SIGIL FORGE ================= */}
        <div className="bg-gray-900/60 backdrop-blur-md rounded-xl border border-white/10 p-5 space-y-6 flex flex-col justify-between shadow-2xl">
          
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-white tracking-wider flex items-center gap-2 border-b border-white/5 pb-2">
              <Gem className="w-4 h-4 text-purple-400" />
              ACTIVE SIGIL TEMPLATE
            </h3>
            
            {latestSigil ? (
              <div className="space-y-4">
                <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg text-center">
                  <span className="text-[10px] font-mono text-purple-400 block uppercase">BROADCAST INTENTION</span>
                  <span className="text-sm font-semibold text-white mt-1 block font-serif">"{latestSigil.intention}"</span>
                  <span className="text-[10px] font-mono text-purple-300 mt-1 block">Reduced Signature: {latestSigil.reduced_letters}</span>
                </div>

                {/* Sigil drawing */}
                <div className="flex gap-4">
                  {/* Magic square vector */}
                  <div className="flex-1 bg-black/60 rounded-xl border border-white/5 p-2 flex flex-col items-center justify-center">
                    <span className="text-[9px] font-mono text-gray-500 mb-1">KAMEA: {latestSigil.kamea.toUpperCase()}</span>
                    <div dangerouslySetInnerHTML={{ __html: latestSigil.svg }} className="w-24 h-24" />
                  </div>
                  
                  {/* Stable diffusion render */}
                  <div className="flex-1 bg-black/60 rounded-xl border border-white/5 p-2 flex flex-col items-center justify-center min-h-[120px]">
                    <span className="text-[9px] font-mono text-gray-500 mb-1">AI RENDER</span>
                    {latestSigil.ai_image ? (
                      <img src={latestSigil.ai_image} alt="AI Sigil" className="w-24 h-24 rounded-lg object-cover" />
                    ) : (
                      <div className="text-[9px] text-gray-600 italic text-center p-2">
                        Offline Fallback Active (SVG Drawing only)
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500 italic text-xs">
                No active sigil forged. Create one in the Command Center!
              </div>
            )}
          </div>

          {/* Broadcast Node controls */}
          <div className="pt-4 border-t border-white/5 space-y-4">
            <h4 className="text-xs font-bold text-gray-400 tracking-wider">BROADCAST TARGET MONITOR</h4>
            
            <div className="bg-white/5 p-3 rounded-lg border border-white/5 max-h-[140px] overflow-y-auto space-y-2">
              {populations.length > 0 ? (
                populations.map(pop => (
                  <div key={pop.id} className="flex justify-between items-center text-xs">
                    <div className="flex items-center gap-1.5 text-gray-300">
                      <Target className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="truncate max-w-[140px]">{pop.name}</span>
                    </div>
                    <span className={`px-2 py-0.5 text-[10px] font-mono rounded-full ${
                      pop.is_active 
                        ? 'bg-green-950 text-green-400 border border-green-500/20' 
                        : 'bg-gray-800 text-gray-500'
                    }`}>
                      {pop.is_active ? 'ACTIVE' : 'STANDBY'}
                    </span>
                  </div>
                ))
              ) : (
                <div className="text-[10px] text-gray-500 italic">No target populations registered.</div>
              )}
            </div>
            
            <button
              onClick={() => {
                if (latestSigil) {
                  // Broadcast the sigil intention
                  fetch(`${API_BASE}/sigils/broadcast`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      intention: latestSigil.intention,
                      sigil_id: latestSigil.id,
                      frequency_hz: frequency,
                      duration_minutes: 5
                    })
                  }).then(res => {
                    if (res.ok) {
                      audioFeedback.playSuccess();
                    } else {
                      audioFeedback.playError();
                    }
                  });
                }
              }}
              disabled={!latestSigil}
              className="w-full px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg text-xs font-bold shadow flex items-center justify-center gap-2 select-none"
            >
              <Zap className="w-3.5 h-3.5 text-yellow-400" /> Broadcast Sigil Frequency
            </button>
          </div>

        </div>

      </div>

    </div>
  );
}
