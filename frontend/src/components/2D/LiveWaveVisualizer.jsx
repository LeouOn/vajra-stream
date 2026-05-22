import React, { useRef, useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAudioStore } from '../../stores/audioStore';

const LiveWaveVisualizer = () => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const { audioSpectrum } = useWebSocket();
  const { frequency, isPlaying } = useAudioStore();
  const [waveType, setWaveType] = useState('sine');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let phase = 0;

    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;

      ctx.fillStyle = 'rgba(15, 15, 35, 0.3)';
      ctx.fillRect(0, 0, width, height);

      if (waveType === 'sine' || waveType === 'combined') {
        drawSineWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.8)');
      }
      if (waveType === 'sawtooth') {
        drawSawtoothWave(ctx, width, height, phase, 'rgba(168, 85, 247, 0.8)');
      }
      if (waveType === 'scalar' || waveType === 'combined') {
        drawScalarWave(ctx, width, height, phase, 'rgba(34, 211, 238, 0.5)');
      }

      ctx.fillStyle = '#22d3ee';
      ctx.font = '14px monospace';
      ctx.fillText(`${frequency.toFixed(1)} Hz`, 10, 24);
      ctx.fillText(`Mode: ${waveType}`, 10, 42);

      const barWidth = width / (audioSpectrum.length || 100);
      audioSpectrum.forEach((val, i) => {
        const barHeight = (val || 0) * height * 0.4;
        ctx.fillStyle = `rgba(34, 211, 238, ${0.3 + (val || 0) * 0.5})`;
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
      for (let x = 0; x < width; x++) {
        const noise = Math.sin(x * 0.1 + phase) * 0.5 + Math.sin(x * 0.05 + phase * 1.3) * 0.5;
        const y = height / 2 + noise * (height * 0.15);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
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
  }, [audioSpectrum, frequency, isPlaying, waveType]);

  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} className="w-full h-full" />
      <div className="absolute top-2 right-2 flex gap-1">
        {['sine', 'sawtooth', 'scalar', 'combined'].map((type) => (
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