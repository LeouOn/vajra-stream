/**
 * Frequency Waterfall — scrolling frequency-over-time heatmap.
 * Canvas-based waterfall display showing frequency intensity
 * history as a descending colour-mapped spectrogram.
 * @component
 */
import React, { useRef, useEffect } from 'react';
import { Activity } from 'lucide-react';

const SOLFEGGIO = [
  { hz: 396, name: 'Liberation', color: '#ff4444', chakra: 'Root' },
  { hz: 417, name: 'Undoing', color: '#ff8c00', chakra: 'Sacral' },
  { hz: 528, name: 'DNA Repair', color: '#ffdd00', chakra: 'Solar Plexus' },
  { hz: 639, name: 'Connection', color: '#00ff88', chakra: 'Heart' },
  { hz: 741, name: 'Intuition', color: '#00ccff', chakra: 'Throat' },
  { hz: 852, name: 'Spiritual', color: '#9966ff', chakra: 'Third Eye' },
  { hz: 963, name: 'Divine', color: '#cc66ff', chakra: 'Crown' },
];

const PLANETARY = [
  { hz: 136.1, name: 'Earth/OM', color: '#22d3ee' },
  { hz: 126.22, name: 'Sun', color: '#fbbf24' },
  { hz: 210.42, name: 'Moon', color: '#c0c0c0' },
];

const HISTORY_LENGTH = 180; // 3 minutes at 1 row/sec

export default function FrequencyWaterfall({ frequency = 136.1, isPlaying = false }) {
  const canvasRef = useRef(null);
  const historyRef = useRef([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;

    const draw = () => {
      // Shift history
      const row = new Array(W).fill(0);
      // Mark active frequencies
      SOLFEGGIO.forEach((s) => {
        const x = Math.round((s.hz / 1000) * W);
        if (x < W) row[x] = 0.3;
      });
      PLANETARY.forEach((p) => {
        const x = Math.round((p.hz / 250) * W);
        if (x < W) row[x] = 0.2;
      });
      // Mark current carrier frequency
      if (isPlaying && frequency) {
        const fx = Math.round((frequency / 1000) * W);
        if (fx < W) row[fx] = 1.0;
      }
      historyRef.current.push(row);
      if (historyRef.current.length > HISTORY_LENGTH) {
        historyRef.current.shift();
      }

      // Draw
      const imageData = ctx.createImageData(W, H);
      for (let y = 0; y < H; y++) {
        const hIdx = Math.floor((y / H) * historyRef.current.length);
        const histRow = historyRef.current[Math.min(hIdx, historyRef.current.length - 1)] || new Array(W).fill(0);
        for (let x = 0; x < W; x++) {
          const idx = (y * W + x) * 4;
          const intensity = histRow[x] || 0;
          // Color: cyan base, purple highlights for strong signals
          imageData.data[idx] = Math.floor(intensity * 80 + 5);     // R
          imageData.data[idx + 1] = Math.floor(intensity * 180 + 10); // G
          imageData.data[idx + 2] = Math.floor(intensity * 255 + 15); // B
          imageData.data[idx + 3] = Math.floor(intensity * 200 + 15); // A
        }
      }
      ctx.putImageData(imageData, 0, 0);

      requestAnimationFrame(draw);
    };

    const anim = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(anim);
  }, [frequency, isPlaying]);

  return (
    <div className="bg-gray-900/80 rounded-lg border border-cyan-500/20 overflow-hidden flex flex-col">
      <div className="p-2 border-b border-cyan-500/10 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[10px] font-bold text-cyan-300 uppercase tracking-wider">Frequency Waterfall</span>
        </div>
        <div className="flex items-center gap-2 text-[9px] font-mono">
          {PLANETARY.slice(0, 3).map((p) => (
            <span key={p.hz} className="text-gray-500">{p.hz}<span className="text-gray-700">Hz</span></span>
          ))}
          <span className="text-gray-700">|</span>
          {SOLFEGGIO.filter((_, i) => i % 2 === 0).map((s) => (
            <span key={s.hz} className="text-gray-500">{s.hz}<span className="text-gray-700">Hz</span></span>
          ))}
        </div>
      </div>
      <canvas ref={canvasRef} className="flex-1 w-full" style={{ minHeight: 180 }} />
      {/* Legend */}
      <div className="flex gap-2 px-2 py-1.5 border-t border-cyan-500/10">
        {SOLFEGGIO.map((s) => (
          <div key={s.hz} className="flex items-center gap-1 text-[9px]">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} />
            <span className="text-gray-500">{s.hz}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
