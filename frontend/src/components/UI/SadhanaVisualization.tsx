import React, { useEffect, useRef } from 'react';
import type { DeityVisualization } from '../lib/deityVisualizations';

interface SadhanaVisualizationProps {
  deity: DeityVisualization;
  size?: number;
  animate?: boolean;
  showLabels?: boolean;
}

export default function SadhanaVisualization({
  deity,
  size = 300,
  animate = true,
  showLabels = true,
}: SadhanaVisualizationProps) {
  const glowRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!animate || !glowRef.current) return;
    const svg = glowRef.current;
    let frame = 0;
    let raf = 0;
    const animate_pulse = () => {
      frame += 0.02;
      const glow = svg.querySelector('#radiance-glow') as SVGCircleElement | null;
      if (glow) {
        const pulse = 0.5 + 0.3 * Math.sin(frame);
        glow.setAttribute('opacity', String(0.3 + pulse * 0.4));
      }
      const rays = svg.querySelectorAll('.light-ray') as NodeListOf<SVGLineElement>;
      rays.forEach((ray, i) => {
        const phase = frame + (i * Math.PI * 2) / rays.length;
        const opacity = 0.2 + 0.3 * Math.abs(Math.sin(phase));
        ray.setAttribute('opacity', String(opacity));
      });
      raf = requestAnimationFrame(animate_pulse);
    };
    raf = requestAnimationFrame(animate_pulse);
    return () => cancelAnimationFrame(raf);
  }, [animate]);

  const cx = size / 2;
  const moonR = size * 0.28;
  const moonCy = size * 0.42;
  const lotusCy = size * 0.68;
  const lotusR = size * 0.2;
  const sunR = size * 0.06;
  const rayCount = 12;
  const rayInner = moonR * 1.15;
  const rayOuter = size * 0.48;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        ref={glowRef}
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[320px]"
        style={{ filter: 'drop-shadow(0 0 20px rgba(0,0,0,0.5))' }}
      >
        <defs>
          <radialGradient id="dharmadhatu-bg">
            <stop offset="0%" stopColor={deity.bodyColor} stopOpacity={0.06} />
            <stop offset="40%" stopColor={deity.bodyColor} stopOpacity={0.02} />
            <stop offset="100%" stopColor="#020617" stopOpacity={0} />
          </radialGradient>

          <radialGradient id="radiance">
            <stop offset="0%" stopColor={deity.radianceColor} stopOpacity={0.4} />
            <stop offset="50%" stopColor={deity.radianceColor} stopOpacity={0.1} />
            <stop offset="100%" stopColor={deity.radianceColor} stopOpacity={0} />
          </radialGradient>

          <radialGradient id="moon-disk">
            <stop offset="0%" stopColor="#ffffff" stopOpacity={0.95} />
            <stop offset="70%" stopColor="#e2e8f0" stopOpacity={0.7} />
            <stop offset="100%" stopColor="#cbd5e1" stopOpacity={0.3} />
          </radialGradient>

          <radialGradient id="bija-glow">
            <stop offset="0%" stopColor={deity.emissionColor} stopOpacity={1} />
            <stop offset="100%" stopColor={deity.emissionColor} stopOpacity={0} />
          </radialGradient>

          <radialGradient id="sun-disk-grad">
            <stop offset="0%" stopColor="#fef08a" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.3} />
          </radialGradient>

          <filter id="bija-blur">
            <feGaussianBlur stdDeviation="1.5" />
          </filter>
        </defs>

        <rect x="0" y="0" width={size} height={size} fill="url(#dharmadhatu-bg)" />

        <circle id="radiance-glow" cx={cx} cy={moonCy} r={size * 0.45} fill="url(#radiance)" opacity={0.5} />

        {Array.from({ length: rayCount }).map((_, i) => {
          const angle = (i / rayCount) * Math.PI * 2;
          const x1 = cx + Math.cos(angle) * rayInner;
          const y1 = moonCy + Math.sin(angle) * rayInner;
          const x2 = cx + Math.cos(angle) * rayOuter;
          const y2 = moonCy + Math.sin(angle) * rayOuter;
          return (
            <line
              key={`ray-${i}`}
              className="light-ray"
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={deity.emissionColor}
              strokeWidth={1.5}
              strokeLinecap="round"
              opacity={0.3}
            />
          );
        })}

        {deity.hasSunDisk && deity.sunDiskPosition === 'below' && (
          <ellipse cx={cx} cy={lotusCy + lotusR * 0.8} rx={lotusR * 1.4} ry={sunR} fill="url(#sun-disk-grad)" opacity={0.5} />
        )}

        {drawLotus(cx, lotusCy, lotusR, deity.lotusColor)}

        {deity.hasSunDisk && deity.sunDiskPosition === 'above' && (
          <circle cx={cx} cy={moonCy - moonR * 0.9} r={sunR} fill="url(#sun-disk-grad)" opacity={0.7} />
        )}

        <circle cx={cx} cy={moonCy} r={moonR} fill="url(#moon-disk)" opacity={0.92} />

        <circle cx={cx} cy={moonCy} r={moonR * 0.6} fill="url(#bija-glow)" opacity={0.3} />

        <text
          x={cx}
          y={moonCy + size * 0.06}
          textAnchor="middle"
          fontSize={size * 0.16}
          fontFamily="'Noto Sans Devanagari', 'Noto Sans SC', serif"
          fontWeight="bold"
          fill={deity.emissionColor}
          filter="url(#bija-blur)"
          opacity={0.4}
        >
          {deity.bija}
        </text>
        <text
          x={cx}
          y={moonCy + size * 0.06}
          textAnchor="middle"
          fontSize={size * 0.16}
          fontFamily="'Noto Sans Devanagari', 'Noto Sans SC', serif"
          fontWeight="bold"
          fill={deity.emissionColor}
        >
          {deity.bija}
        </text>

        <text
          x={cx}
          y={moonCy + moonR * 0.7}
          textAnchor="middle"
          fontSize={size * 0.04}
          fontFamily="monospace"
          fill={deity.emissionColor}
          opacity={0.6}
          letterSpacing={2}
        >
          {deity.bijaRomaji}
        </text>
      </svg>

      {showLabels && (
        <div className="text-center space-y-0.5 mt-1">
          <div className="text-sm font-bold" style={{ color: deity.bodyColor }}>
            {deity.name}
          </div>
          <div className="text-[10px] font-mono text-gray-500">
            {deity.sanskritName}
          </div>
          <div className="text-[10px] text-gray-400 max-w-[260px] leading-relaxed mt-1">
            {deity.bodyColorName} · {deity.mudra}
          </div>
          <div className="text-[9px] font-mono text-gray-600 mt-1">
            {deity.bijā_ || deity.bijaRomaji} · {deity.frequencyHz} Hz · {deity.element}
          </div>
        </div>
      )}
    </div>
  );
}

function drawLotus(cx: number, cy: number, r: number, color: string): React.ReactElement[] {
  const petals: React.ReactElement[] = [];
  const petalCount = 8;
  for (let i = 0; i < petalCount; i++) {
    const angle = (i / petalCount) * Math.PI * 2 + Math.PI / petalCount;
    const px = cx + Math.cos(angle) * r * 0.6;
    const py = cy + Math.sin(angle) * r * 0.3;
    const rotDeg = (angle * 180) / Math.PI + 90;
    petals.push(
      <ellipse
        key={`petal-${i}`}
        cx={px}
        cy={py}
        rx={r * 0.3}
        ry={r * 0.6}
        fill={color}
        opacity={0.15 + (i % 2) * 0.1}
        transform={`rotate(${rotDeg} ${px} ${py})`}
      />
    );
  }
  petals.push(
    <ellipse key="lotus-center" cx={cx} cy={cy} rx={r * 0.5} ry={r * 0.2} fill={color} opacity={0.12} />
  );
  return petals;
}
