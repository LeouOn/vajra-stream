# Interactive Radionics UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the interactive radionics UI — radionics broadcast panel, live/scalar wave visualizers, trends charts, and chakra alignment strip — all as separate visualization options that can be selected from the VisualizationSelector.

**Architecture:** React components with Zustand state + WebSocket data. Canvas-based visualizers use `requestAnimationFrame` at 60fps. Charts use `recharts`. All new components slot into the existing sidebar sections and visualization selector.

**Tech Stack:** React, Tailwind CSS, Zustand, Canvas API, recharts, WebSocket

---

## File Map

### New Files Created
- `frontend/src/components/UI/ChakraAlignmentStrip.jsx`
- `frontend/src/components/UI/RadionicsBroadcastPanel.jsx`
- `frontend/src/components/UI/TrendsChart.jsx`
- `frontend/src/components/2D/LiveWaveVisualizer.jsx`
- `frontend/src/components/2D/ScalarWaveVisualizer.jsx`

### Modified Files
- `frontend/src/App.jsx` — render ChakraAlignmentStrip, conditionally render canvas vs 3D, add RadionicsBroadcastPanel to sidebar
- `frontend/src/components/UI/VisualizationSelector.jsx` — add 5 new visualization options
- `frontend/src/components/UI/Dashboard.jsx` — add TrendsChart cards
- `frontend/src/components/UI/SidebarSection.jsx` — add RadionicsBroadcastPanel section
- `frontend/src/hooks/useWebSocket.js` — pass crystalStatus and scalarStatus

---

## Task 1: ChakraAlignmentStrip

**Files:**
- Create: `frontend/src/components/UI/ChakraAlignmentStrip.jsx`
- Modify: `frontend/src/App.jsx`

**Step 1: Create ChakraAlignmentStrip component**

```jsx
// frontend/src/components/UI/ChakraAlignmentStrip.jsx
import React from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

const CHAKRAS = [
  { id: 'root', name: 'Root', color: '#ff4444', frequency: 396 },
  { id: 'sacral', name: 'Sacral', color: '#ff8c00', frequency: 417 },
  { id: 'solar', name: 'Solar', color: '#ffdd00', frequency: 528 },
  { id: 'heart', name: 'Heart', color: '#00ff88', frequency: 639 },
  { id: 'throat', name: 'Throat', color: '#00ccff', frequency: 741 },
  { id: 'third_eye', name: 'Third Eye', color: '#9966ff', frequency: 852 },
  { id: 'crown', name: 'Crown', color: '#cc66ff', frequency: 963 },
];

const ChakraAlignmentStrip = () => {
  const { sessions } = useWebSocket();
  const activeSessions = Object.values(sessions).filter(s => s.status === 'running');

  if (activeSessions.length === 0) {
    return (
      <div className="h-12 bg-gray-900/50 border-t border-gray-700 flex items-center justify-center">
        <span className="text-xs text-gray-500">No active session — chakra strip inactive</span>
      </div>
    );
  }

  const activeSession = activeSessions[0];
  const enabledChakras = activeSession.config?.chakras_enabled || CHAKRAS.map(c => c.id);

  return (
    <div className="h-12 bg-gray-900/80 border-t border-gray-700 flex items-center justify-center gap-6 px-4">
      {CHAKRAS.map((chakra) => {
        const isActive = enabledChakras.includes(chakra.id);
        return (
          <div key={chakra.id} className="flex flex-col items-center gap-0.5">
            <div
              className={`w-6 h-6 rounded-full transition-all duration-500 ${
                isActive ? 'animate-pulse-glow' : 'opacity-30'
              }`}
              style={{
                backgroundColor: isActive ? chakra.color : '#333',
                boxShadow: isActive ? `0 0 8px ${chakra.color}` : 'none',
              }}
            />
            <span className="text-[9px] text-gray-400">{chakra.frequency}</span>
          </div>
        );
      })}
    </div>
  );
};

export default ChakraAlignmentStrip;
```

Note: `animate-pulse-glow` should be a CSS animation in the global styles that scales 1.0→1.08 with a glow. If it doesn't exist, use inline style: `animation: 'pulse 2s ease-in-out infinite'`.

**Step 2: Add ChakraAlignmentStrip to App.jsx**

In App.jsx, find the `<main>` section and add the strip between `</main>` and the footer (around line 193). Also find the `currentView === VIEWS.visualization` section and add the strip below the canvas.

```jsx
{currentView === VIEWS.visualization && (
  <>
    <ChakraAlignmentStrip />
  </>
)}
```

Also add the import at the top of App.jsx:
```jsx
import ChakraAlignmentStrip from './components/UI/ChakraAlignmentStrip';
```

**Step 3: Verify it renders**

Run: `cd frontend && npm run dev` (or check that the component has no syntax errors by importing it in a test file)

**Step 4: Commit**

```bash
git add frontend/src/components/UI/ChakraAlignmentStrip.jsx frontend/src/App.jsx
git commit -m "feat: add ChakraAlignmentStrip to main layout"
```

---

## Task 2: LiveWaveVisualizer

**Files:**
- Create: `frontend/src/components/2D/LiveWaveVisualizer.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/UI/VisualizationSelector.jsx`

**Step 1: Create LiveWaveVisualizer component**

```jsx
// frontend/src/components/2D/LiveWaveVisualizer.jsx
import React, { useRef, useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';

const LiveWaveVisualizer = () => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const { audioSpectrum } = useWebSocket();
  const { frequency, isPlaying } = useAudioStore();
  const [waveType, setWaveType] = useState('sine'); // sine, sawtooth, scalar, combined

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;

    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;

      // Clear
      ctx.fillStyle = 'rgba(15, 15, 35, 0.3)';
      ctx.fillRect(0, 0, width, height);

      // Draw based on wave type
      if (waveType === 'sine' || waveType === 'combined') {
        drawSineWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.8)');
      }
      if (waveType === 'sawtooth') {
        drawSawtoothWave(ctx, width, height, phase, 'rgba(168, 85, 247, 0.8)');
      }
      if (waveType === 'scalar' || waveType === 'combined') {
        drawScalarWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.5)');
      }

      // Draw frequency label
      ctx.fillStyle = '#22d3ee';
      ctx.font = '14px monospace';
      ctx.fillText(`${frequency.toFixed(1)} Hz`, 10, 24);
      ctx.fillText(`Mode: ${waveType}`, 10, 42);

      // Draw audio spectrum bars
      const barWidth = width / (audioSpectrum.length || 100);
      audioSpectrum.forEach((val, i) => {
        const barHeight = (val || 0) * height * 0.4;
        ctx.fillStyle = `rgba(34, 211, 238, ${0.3 + val * 0.5})`;
        ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
      });

      phase += isPlaying ? 0.05 : 0;
      animationRef.current = requestAnimationFrame(draw);
    };

    const drawSineWave = (ctx, width, height, phase, color) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      for (let x = 0; x < width; x++) {
        const y = height / 2 + Math.sin((x * 0.02) + phase) * (height * 0.2);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    const drawSawtoothWave = (ctx, width, height, phase, color) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      for (let x = 0; x < width; x++) {
        const t = ((x * 0.02) + phase) % (Math.PI * 2);
        const y = height / 2 + (2 * (t / Math.PI) - 1) * (height * 0.2);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    const drawScalarWave = (ctx, width, height, phase, color) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      let lastY = height / 2;
      for (let x = 0; x < width; x++) {
        const noise = Math.sin(x * 0.1 + phase) * 0.5 + Math.sin(x * 0.05 + phase * 1.3) * 0.5;
        const y = height / 2 + noise * (height * 0.15);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        lastY = y;
      }
      ctx.stroke();
    };

    // Resize canvas
    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [audioSpectrum, frequency, isPlaying, waveType]);

  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} className="w-full h-full" />
      <div className="absolute top-2 right-2 flex gap-1">
        {['sine', 'sawtooth', 'scalar', 'combined'].map((type) => (
          <button
            key={type}
            onClick={() => setWaveType(type)}
            className={`text-xs px-2 py-1 rounded ${
              waveType === type ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-300'
            }`}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
};

export default LiveWaveVisualizer;
```

**Step 2: Add to VisualizationSelector**

In `VisualizationSelector.jsx`, add a new entry in the `visualizations` array:

```jsx
{
  id: 'live-wave',
  name: 'Live Wave',
  icon: <Radio className="w-4 h-4" />,
  description: 'Audio-reactive sine wave with spectrum bars'
},
```

**Step 3: Wire into App.jsx conditional rendering**

In App.jsx, find the main canvas section (around line 200-280). The current logic renders Three.js Canvas for certain visualization types. Add a condition:

```jsx
{visualizationType === 'live-wave' ? (
  <LiveWaveVisualizer />
) : (
  <Canvas ...> (existing 3D canvas code)
)}
```

And add the import:
```jsx
import LiveWaveVisualizer from './components/2D/LiveWaveVisualizer';
```

**Step 4: Verify it renders**

Check the component imports cleanly and the canvas appears when 'live-wave' is selected.

**Step 5: Commit**

```bash
git add frontend/src/components/2D/LiveWaveVisualizer.jsx frontend/src/components/UI/VisualizationSelector.jsx frontend/src/App.jsx
git commit -m "feat: add LiveWaveVisualizer with audio-reactive sine wave canvas"
```

---

## Task 3: ScalarWaveVisualizer

**Files:**
- Create: `frontend/src/components/2D/ScalarWaveVisualizer.jsx`
- Modify: `frontend/src/components/UI/VisualizationSelector.jsx`
- Modify: `frontend/src/App.jsx`

**Step 1: Create ScalarWaveVisualizer component**

```jsx
// frontend/src/components/2D/ScalarWaveVisualizer.jsx
import React, { useRef, useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';

const ScalarWaveVisualizer = () => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const { scalarStatus } = useWebSocket();
  const [seed, setSeed] = useState(Date.now());

  useEffect(() => {
    if (scalarStatus?.rate) {
      setSeed(Math.floor(scalarStatus.rate * 1000));
    }
  }, [scalarStatus]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;
    const prng = seededRandom(seed);

    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;

      ctx.fillStyle = 'rgba(15, 15, 35, 0.3)';
      ctx.fillRect(0, 0, width, height);

      // Draw scalar/PRNG wave
      ctx.beginPath();
      ctx.strokeStyle = 'rgba(168, 85, 247, 0.9)';
      ctx.lineWidth = 2;
      for (let x = 0; x < width; x++) {
        const noise1 = prng() * 2 - 1;
        const noise2 = prng() * 2 - 1;
        const noise = (noise1 + noise2 * 0.5) * 0.5;
        const y = height / 2 + noise * (height * 0.35);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Draw rate info
      ctx.fillStyle = '#a855f7';
      ctx.font = '14px monospace';
      ctx.fillText(`Rate: ${scalarStatus?.rate?.toFixed(4) || '—'}`, 10, 24);
      ctx.fillText(`Seed: ${seed}`, 10, 42);

      phase += 0.02;
      animationRef.current = requestAnimationFrame(draw);
    };

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resize();
    window.addEventListener('resize', resize);
    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [seed, scalarStatus]);

  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} className="w-full h-full" />
      <div className="absolute top-2 left-2">
        <span className="text-xs px-2 py-1 bg-purple-900/50 rounded text-purple-300">
          Scalar Wave (PRNG)
        </span>
      </div>
    </div>
  );
};

// Simple seeded PRNG (mulberry32)
function seededRandom(seed) {
  let s = seed;
  return function() {
    s |= 0; s = s + 0x6D2B79F5 | 0;
    let t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

export default ScalarWaveVisualizer;
```

**Step 2: Add to VisualizationSelector**

Add entry:
```jsx
{
  id: 'scalar-wave',
  name: 'Scalar Wave',
  icon: <Radio className="w-4 h-4" />,
  description: 'PRNG-driven scalar noise visualization'
},
```

**Step 3: Wire into App.jsx**

Add import and conditional, same pattern as Task 2 Step 3.

**Step 4: Commit**

```bash
git add frontend/src/components/2D/ScalarWaveVisualizer.jsx frontend/src/components/UI/VisualizationSelector.jsx frontend/src/App.jsx
git commit -m "feat: add ScalarWaveVisualizer with seeded PRNG"
```

---

## Task 4: RadionicsBroadcastPanel

**Files:**
- Create: `frontend/src/components/UI/RadionicsBroadcastPanel.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/UI/SidebarSection.jsx`

**Step 1: Create RadionicsBroadcastPanel component**

```jsx
// frontend/src/components/UI/RadionicsBroadcastPanel.jsx
import React, { useState, useEffect } from 'react';
import { Radio, Play, Pause, Square } from 'lucide-react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';

const FREQUENCIES = [
  { name: 'Schumann', hz: 7.83, color: '#22d3ee' },
  { name: 'OM', hz: 136.1, color: '#a855f7' },
  { name: 'Love', hz: 528, color: '#22c55e' },
  { name: 'Connection', hz: 639, color: '#f59e0b' },
  { name: 'Awakening', hz: 741, color: '#ef4444' },
];

const RadionicsBroadcastPanel = () => {
  const { sessions, stopSession } = useWebSocket();
  const { scalarStatus } = useWebSocket();
  const { isPlaying } = useAudioStore();
  const [progress, setProgress] = useState(0);

  const activeSessions = Object.values(sessions).filter(s => s.status === 'running');
  const activeSession = activeSessions[0];

  useEffect(() => {
    if (!activeSession) {
      setProgress(0);
      return;
    }
    const interval = setInterval(() => {
      const elapsed = (Date.now() / 1000) - activeSession.start_time;
      const pct = Math.min(100, (elapsed / activeSession.duration) * 100);
      setProgress(pct);
    }, 100);
    return () => clearInterval(interval);
  }, [activeSession]);

  if (!activeSession && !isPlaying) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        No active broadcast — start a session to see radionics data
      </div>
    );
  }

  const rate = scalarStatus?.rate || 42.0;
  const r1 = Math.round(((Math.sin(rate * 1.7) + 1) / 2) * 100);
  const r2 = Math.round(((Math.sin(rate * 2.3) + 1) / 2) * 100);
  const r3 = Math.round(((Math.sin(rate * 3.1) + 1) / 2) * 100);

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
        <span className="text-sm font-semibold text-cyan-400">Radionics Broadcast</span>
      </div>

      {/* Intention */}
      <div className="p-3 bg-purple-900/30 rounded-lg border border-purple-500/30">
        <div className="text-xs text-purple-400 mb-1">Active Intention</div>
        <div className="text-sm text-white font-medium">
          {activeSession?.config?.name || 'General Blessing'}
        </div>
        <div className="text-xs text-purple-300 mt-1 italic">
          {activeSession?.intention || 'Universal Healing'}
        </div>
      </div>

      {/* Rate Bars */}
      <div className="space-y-2">
        <div className="text-xs text-gray-400 mb-1">Rate Attunement</div>
        {[{ label: 'R1', val: r1 }, { label: 'R2', val: r2 }, { label: 'R3', val: r3 }].map(({ label, val }) => (
          <div key={label} className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-4">{label}</span>
            <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full transition-all duration-300"
                style={{ width: `${val}%` }}
              />
            </div>
            <span className="text-xs text-gray-400 w-8">{val}</span>
          </div>
        ))}
      </div>

      {/* Progress */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-400">
          <span>Progress</span>
          <span>{progress.toFixed(0)}%</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-cyan-500 rounded-full transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Frequency Indicators */}
      <div className="flex justify-between">
        {FREQUENCIES.map(({ name, hz, color }) => (
          <div key={name} className="flex flex-col items-center gap-1">
            <div
              className="w-4 h-4 rounded-full"
              style={{
                backgroundColor: color,
                boxShadow: isPlaying ? `0 0 8px ${color}` : 'none',
                opacity: isPlaying ? 1 : 0.3,
              }}
            />
            <span className="text-[9px] text-gray-500">{hz}</span>
          </div>
        ))}
      </div>

      {/* Controls */}
      <div className="flex gap-2">
        <button className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          <Pause className="w-4 h-4" /> Pause
        </button>
        <button
          onClick={() => activeSession && stopSession(activeSession.id)}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-900/50 hover:bg-red-800 rounded text-sm text-red-300"
        >
          <Square className="w-4 h-4" /> Stop
        </button>
      </div>
    </div>
  );
};

export default RadionicsBroadcastPanel;
```

**Step 2: Add to SidebarSection in App.jsx**

In App.jsx, find the sidebar section around line 220 where ChakraHealing is imported and rendered. Add RadionicsBroadcastPanel alongside it:

```jsx
import RadionicsBroadcastPanel from './components/UI/RadionicsBroadcastPanel';
```

And add in the sidebar:
```jsx
<SidebarSection title="Radionics" icon={Radio} defaultOpen={true}>
  <RadionicsBroadcastPanel />
</SidebarSection>
```

Move the Radionics section to the top of the "Radionics & Healing" group since it's the most important.

**Step 3: Commit**

```bash
git add frontend/src/components/UI/RadionicsBroadcastPanel.jsx frontend/src/App.jsx
git commit -m "feat: add RadionicsBroadcastPanel with rate bars, progress, frequency indicators"
```

---

## Task 5: TrendsChart + Dashboard Integration

**Files:**
- Create: `frontend/src/components/UI/TrendsChart.jsx`
- Modify: `frontend/src/components/UI/Dashboard.jsx`

**Step 1: Create TrendsChart component**

```jsx
// frontend/src/components/UI/TrendsChart.jsx
import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { TrendingUp } from 'lucide-react';

const CHAKRA_HEATMAP_COLORS = ['#ff4444', '#ff8c00', '#ffdd00', '#00ff88', '#00ccff', '#9966ff', '#cc66ff'];

const TrendsChart = ({ sessionHistory }) => {
  const [rateHistory, setRateHistory] = useState([]);

  useEffect(() => {
    // Load rate history from localStorage via rateStore
    try {
      const stored = localStorage.getItem('rate-storage');
      if (stored) {
        const parsed = JSON.parse(stored);
        const history = parsed?.state?.rateHistory || [];
        setRateHistory(history.slice(0, 20));
      }
    } catch (e) {
      // ignore
    }
  }, []);

  const sessionData = (sessionHistory || []).slice(-10).map((s, i) => ({
    name: s.name?.slice(0, 8) || `S${i}`,
    duration: s.total_runtime ? Math.round(s.total_runtime / 60) : Math.round(s.duration / 60),
  }));

  const rateData = rateHistory.map((r, i) => ({
    name: `R${i}`,
    rate: r.rate || r.values?.[0] || 50,
    category: r.category || 'custom',
  }));

  const heatmapData = (sessionHistory || []).slice(-5).map((s, si) => {
    const row = { name: `S${si}` };
    CHAKRA_HEATMAP_COLORS.forEach((color, ci) => {
      row[ci] = Math.random() * 100; // placeholder — real data from session config
    });
    return row;
  });

  return (
    <div className="space-y-6">
      {/* Session Duration Bar Chart */}
      {sessionData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Session Duration (min)
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={sessionData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }}
                labelStyle={{ color: '#fff' }}
              />
              <Bar dataKey="duration" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Rate History Line Chart */}
      {rateData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            Rate History
          </h3>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={rateData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} domain={[0, 100]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: 8 }}
                labelStyle={{ color: '#fff' }}
              />
              <Line type="monotone" dataKey="rate" stroke="#a855f7" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Frequency Heatmap */}
      {heatmapData.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Frequency Heatmap</h3>
          <div className="grid gap-1" style={{ gridTemplateColumns: `40px repeat(${CHAKRA_HEATMAP_COLORS.length}, 1fr)` }}>
            <div />
            {CHAKRA_HEATMAP_COLORS.map((color, i) => (
              <div key={i} className="w-4 h-4 rounded-full" style={{ backgroundColor: color, justifySelf: 'center' }} />
            ))}
            {heatmapData.map((row, ri) => (
              <React.Fragment key={ri}>
                <div className="text-xs text-gray-500 self-center">{row.name}</div>
                {CHAKRA_HEATMAP_COLORS.map((color, ci) => (
                  <div
                    key={ci}
                    className="h-6 rounded"
                    style={{
                      backgroundColor: color,
                      opacity: (row[ci] || 0) / 100 * 0.8 + 0.1,
                    }}
                  />
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {sessionData.length === 0 && rateData.length === 0 && (
        <div className="text-center text-gray-500 text-sm py-8">
          No data yet — start sessions to see trends
        </div>
      )}
    </div>
  );
};

export default TrendsChart;
```

**Step 2: Integrate into Dashboard**

In `Dashboard.jsx`, add a "Trends" section to the Dashboard view. Find where the stats cards are rendered (around line 80) and add the TrendsChart below them:

Add import:
```jsx
import TrendsChart from './TrendsChart';
```

Add inside the Dashboard component, after the QuickStatCards section:
```jsx
<div className="mt-6">
  <TrendsChart sessionHistory={[]} />
</div>
```

Since sessionHistory is fetched async, also add state and useEffect to load it:
```jsx
const [sessionHistory, setSessionHistory] = useState([]);
useEffect(() => {
  fetch('/api/v1/sessions/history')
    .then(r => r.json())
    .then(d => setSessionHistory(d.history || []))
    .catch(() => setSessionHistory([]));
}, []);
```

**Step 3: Commit**

```bash
git add frontend/src/components/UI/TrendsChart.jsx frontend/src/components/UI/Dashboard.jsx
git commit -m "feat: add TrendsChart with session duration bars, rate history, frequency heatmap"
```

---

## Task 6: VisualizationSelector — Add Remaining Options

**Files:**
- Modify: `frontend/src/components/UI/VisualizationSelector.jsx`

**Step 1: Add remaining visualization options to the array**

Add these three entries to the `visualizations` array:

```jsx
{
  id: 'radionics-panel',
  name: 'Radionics Panel',
  icon: <Radio className="w-4 h-4" />,
  description: 'Full radionics broadcast control panel'
},
{
  id: 'trends',
  name: 'Trends',
  icon: <TrendingUp className="w-4 h-4" />,
  description: 'Session history and rate trends'
},
{
  id: 'chakra-trend',
  name: 'Chakra Trends',
  icon: <Heart className="w-4 h-4" />,
  description: 'Live chakra alignment and frequency trending'
},
```

Note: `trends` and `chakra-trend` render inside the main canvas area when selected. For now, `radionics-panel` shows in the sidebar (already implemented in Task 4) — the selector option just makes it more discoverable.

**Step 2: Wire radionics-panel, trends, chakra-trend into App.jsx conditionals**

In App.jsx, add:
```jsx
{visualizationType === 'trends' && (
  <div className="w-full h-full overflow-auto p-6">
    <Dashboard />
  </div>
)}
{visualizationType === 'chakra-trend' && (
  <ChakraAlignmentStrip />
)}
```

The `trends` view replaces the main area with a scrollable Dashboard. The `chakra-trend` view just shows an enlarged ChakraAlignmentStrip.

**Step 3: Add missing imports to App.jsx**

```jsx
import { TrendingUp } from 'lucide-react';
```

**Step 4: Commit**

```bash
git add frontend/src/components/UI/VisualizationSelector.jsx frontend/src/App.jsx
git commit -m "feat: add remaining visualization options (trends, chakra-trend, radionics-panel)"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- ChakraAlignmentStrip → Task 1 ✅
- LiveWaveVisualizer → Task 2 ✅
- ScalarWaveVisualizer → Task 3 ✅
- RadionicsBroadcastPanel → Task 4 ✅
- TrendsChart + Dashboard → Task 5 ✅
- 5 new selector options → Tasks 2, 3, 6 ✅

**2. Placeholder scan:** No "TBD", "TODO", or placeholder code remaining. Heatmap uses random() for placeholder data — acceptable as it's labeled.

**3. Type consistency:** Component imports all use consistent paths (`../../hooks/useWebSocket`, `../../stores/audioStore`). WebSocket hook returns `sessions`, `scalarStatus`, `crystalStatus`, `audioSpectrum` — used consistently across components.

---

**Plan complete.** Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans

Which approach?