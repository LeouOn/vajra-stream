/**
 * Live Wave Visualizer — real-time audio waveform oscilloscope.
 * Renders the live audio waveform from WebSocket spectrum data
 * as an animated canvas. DPR-aware + RAF-stable.
 * @component
 */
import React, { useRef, useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';

type WaveType = 'sine' | 'sawtooth' | 'scalar' | 'combined';

const WAVE_TYPES: WaveType[] = ['sine', 'sawtooth', 'scalar', 'combined'];

// Cap the spectrum draw loop to 64 bars (matches AudioSpectrum.tsx).
// Without this, a large spectrum array causes 256+ fillRect calls per frame.
const MAX_SPECTRUM_BARS = 64;

const LiveWaveVisualizer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const { audioSpectrum } = useWebSocket();
  const frequency = useAudioStore((s) => s.frequency);
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const [waveType, setWaveType] = useState<WaveType>('sine');

  // BUG FIX: audioSpectrum was in the useEffect dep array, which caused the
  // entire RAF loop to be torn down + recreated on every WebSocket audio
  // spectrum push. The WS pushes spectrum data continuously, so this was
  // constant setup/teardown. Now we read spectrum from a ref instead.
  const spectrumRef = useRef<number[]>(audioSpectrum);
  spectrumRef.current = audioSpectrum;
  // Same treatment for frequency/isPlaying — avoids restart on every store update.
  const frequencyRef = useRef(frequency);
  frequencyRef.current = frequency;
  const isPlayingRef = useRef(isPlaying);
  isPlayingRef.current = isPlaying;
  // Keep waveType in a ref too so the draw loop sees the latest value without
  // restarting on every change (we DO restart on waveType change via the dep
  // array, but the ref is read inside the loop for consistency with the others).
  const waveTypeRef = useRef<WaveType>(waveType);
  waveTypeRef.current = waveType;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let phase = 0;

    const draw = (): void => {
      const width = canvas.width;
      const height = canvas.height;
      // Read latest spectrum from ref — no effect restart on WS updates
      const spectrum = spectrumRef.current;

      ctx.fillStyle = 'rgba(15, 15, 35, 0.3)';
      ctx.fillRect(0, 0, width, height);

      const currentWaveType = waveTypeRef.current;
      if (currentWaveType === 'sine' || currentWaveType === 'combined') {
        drawSineWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.8)');
      }
      if (currentWaveType === 'sawtooth') {
        drawSawtoothWave(ctx, width, height, phase, 'rgba(168, 85, 247, 0.8)');
      }
      if (currentWaveType === 'scalar' || currentWaveType === 'combined') {
        drawScalarWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.5)');
      }

      ctx.fillStyle = '#22d3ee';
      ctx.font = '14px monospace';
      ctx.fillText(`${frequencyRef.current.toFixed(1)} Hz`, 10, 24);
      ctx.fillText(`Mode: ${currentWaveType}`, 10, 42);

      // Cap to MAX_SPECTRUM_BARS to keep draw cost bounded.
      const barCount = Math.min(spectrum.length, MAX_SPECTRUM_BARS);
      const barWidth = width / (barCount || 100);
      for (let i = 0; i < barCount; i++) {
        const val = spectrum[i] || 0;
        const barHeight = val * height * 0.4;
        ctx.fillStyle = `rgba(34, 211, 238, ${0.3 + val * 0.5})`;
        ctx.fillRect(i * barWidth, height - barHeight, barWidth - 1, barHeight);
      }

      phase += isPlayingRef.current ? 0.05 : 0;
      animationRef.current = requestAnimationFrame(draw);
    };

    const drawSineWave = (ctx: CanvasRenderingContext2D, width: number, height: number, phase: number, color: string): void => {
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

    const drawSawtoothWave = (ctx: CanvasRenderingContext2D, width: number, height: number, phase: number, color: string): void => {
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

    const drawScalarWave = (ctx: CanvasRenderingContext2D, width: number, height: number, phase: number, color: string): void => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      for (let x = 0; x < width; x++) {
        const noise = Math.sin(x * 0.1 + phase) * 0.5 + Math.sin(x * 0.05 + phase * 1.3) * 0.5;
        const y = height / 2 + noise * (height * 0.15);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    // DPR-aware resize so the canvas is sharp on retina/4K displays.
    // Coalesced via requestAnimationFrame to avoid thrash on window drag.
    let resizeRaf = 0;
    const resize = (): void => {
      if (resizeRaf) return;
      resizeRaf = requestAnimationFrame(() => {
        resizeRaf = 0;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      });
    };
    resize();
    window.addEventListener('resize', resize);

    draw();

    return () => {
      if (animationRef.current !== null) {
        cancelAnimationFrame(animationRef.current);
      }
      if (resizeRaf) cancelAnimationFrame(resizeRaf);
      window.removeEventListener('resize', resize);
    };
  // waveType is the ONLY thing that should restart the loop now.
  // audioSpectrum / frequency / isPlaying / waveType are all read from refs
  // inside the loop, so this effect only fires when the user picks a new
  // wave type from the UI.
  }, [waveType]);

  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} className="w-full h-full" />
      <div className="absolute top-2 right-2 flex gap-1">
        {WAVE_TYPES.map((type) => (
          <button
            key={type}
            onClick={() => setWaveType(type)}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              waveType === type ? 'bg-cyan-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
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