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