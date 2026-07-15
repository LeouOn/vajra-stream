import React, { useEffect, useRef, useState } from 'react';
import { DHYANI_BUDDHAS, type DhyaniBuddha, type BuddhaFamily, type MandalaDirection } from '../../lib/deityVisualizations';

interface FiveBuddhaMandalaProps {
  activeFamily?: BuddhaFamily;
  size?: number;
  showLabels?: boolean;
}

const DIRECTION_POSITIONS: Record<MandalaDirection, { angle: number; label: string }> = {
  center: { angle: -90, label: 'CENTER' },
  east: { angle: 0, label: 'EAST' },
  south: { angle: 90, label: 'SOUTH' },
  west: { angle: 180, label: 'WEST' },
  north: { angle: 270, label: 'NORTH' },
};

export default function FiveBuddhaMandala({
  activeFamily,
  size = 400,
  showLabels = true,
}: FiveBuddhaMandalaProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredFamily, setHoveredFamily] = useState<BuddhaFamily | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = svgRef.current;
    let frame = 0;
    let raf = 0;
    const animate = () => {
      frame += 0.015;
      const ring = svg.querySelector('#mandala-outer-ring') as SVGCircleElement | null;
      if (ring) {
        const pulse = 0.3 + 0.15 * Math.sin(frame);
        ring.setAttribute('opacity', String(pulse));
      }
      const innerRing = svg.querySelector('#mandala-inner-ring') as SVGCircleElement | null;
      if (innerRing) {
        const pulse = 0.5 + 0.2 * Math.sin(frame + 1.5);
        innerRing.setAttribute('opacity', String(pulse));
      }
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, []);

  const cx = size / 2;
  const cy = size / 2;
  const outerR = size * 0.44;
  const innerR = size * 0.18;
  const buddhaR = size * 0.085;
  const centerR = size * 0.11;

  const getPosition = (direction: MandalaDirection) => {
    if (direction === 'center') return { x: cx, y: cy };
    const { angle } = DIRECTION_POSITIONS[direction];
    const rad = (angle * Math.PI) / 180;
    return {
      x: cx + Math.cos(rad) * (outerR * 0.65),
      y: cy + Math.sin(rad) * (outerR * 0.65),
    };
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${size} ${size}`}
        className="w-full max-w-[440px]"
        style={{ filter: 'drop-shadow(0 0 24px rgba(0,0,0,0.4))' }}
      >
        <defs>
          <radialGradient id="mandala-bg">
            <stop offset="0%" stopColor="#1e1b4b" stopOpacity={0.4} />
            <stop offset="60%" stopColor="#0f0a1e" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#020617" stopOpacity={0} />
          </radialGradient>
        </defs>

        <rect x="0" y="0" width={size} height={size} fill="url(#mandala-bg)" />

        <circle id="mandala-outer-ring" cx={cx} cy={cy} r={outerR} fill="none" stroke="rgba(139, 92, 246, 0.3)" strokeWidth={1.5} />
        <circle cx={cx} cy={cy} r={outerR * 0.82} fill="none" stroke="rgba(139, 92, 246, 0.12)" strokeWidth={1} strokeDasharray="4 8" />
        <circle id="mandala-inner-ring" cx={cx} cy={cy} r={innerR * 1.8} fill="none" stroke="rgba(6, 182, 212, 0.25)" strokeWidth={1.5} />

        {DHYANI_BUDDHAS.filter(b => b.direction !== 'center').map((buddha) => {
          const pos = getPosition(buddha.direction);
          const nextDir = DHYANI_BUDDHAS.find(b => b.direction === getNextDirection(buddha.direction));
          const nextPos = nextDir ? getPosition(nextDir.direction) : pos;
          return (
            <line
              key={`connect-${buddha.direction}`}
              x1={pos.x}
              y1={pos.y}
              x2={nextPos.x}
              y2={nextPos.y}
              stroke="rgba(139, 92, 246, 0.1)"
              strokeWidth={1}
            />
          );
        })}

        {DHYANI_BUDDHAS.filter(b => b.direction !== 'center').map((buddha) => {
          const pos = getPosition(buddha.direction);
          return (
            <line
              key={`spoke-${buddha.direction}`}
              x1={cx}
              y1={cy}
              x2={pos.x}
              y2={pos.y}
              stroke="rgba(139, 92, 246, 0.08)"
              strokeWidth={1}
            />
          );
        })}

        {DHYANI_BUDDHAS.map((buddha) => {
          const pos = getPosition(buddha.direction);
          const isActive = activeFamily === buddha.family;
          const isHovered = hoveredFamily === buddha.family;
          const r = isActive ? buddhaR * 1.35 : isHovered ? buddhaR * 1.15 : buddhaR;
          const isCenter = buddha.direction === 'center';

          return (
            <g
              key={buddha.family}
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredFamily(buddha.family)}
              onMouseLeave={() => setHoveredFamily(null)}
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill={buddha.color}
                opacity={isActive ? 0.25 : isHovered ? 0.15 : 0.08}
              />
              <circle
                cx={pos.x}
                cy={pos.y}
                r={r}
                fill="none"
                stroke={buddha.color}
                strokeWidth={isActive ? 2.5 : 1.5}
                opacity={isActive ? 0.8 : 0.4}
              />

              <text
                x={pos.x}
                y={pos.y + (isCenter ? 5 : 4)}
                textAnchor="middle"
                fontSize={isCenter ? size * 0.055 : size * 0.045}
                fontFamily="'Noto Sans Devanagari', 'Noto Sans SC', serif"
                fontWeight="bold"
                fill={buddha.color}
                opacity={isActive ? 1 : 0.7}
              >
                {buddha.bija}
              </text>

              {showLabels && (
                <>
                  <text
                    x={pos.x}
                    y={pos.y + r + 14}
                    textAnchor="middle"
                    fontSize={size * 0.028}
                    fontFamily="monospace"
                    fill={isActive ? buddha.color : '#94a3b8'}
                    opacity={isActive ? 1 : 0.6}
                    fontWeight={isActive ? 'bold' : 'normal'}
                  >
                    {buddha.name}
                  </text>
                  <text
                    x={pos.x}
                    y={pos.y + r + 26}
                    textAnchor="middle"
                    fontSize={size * 0.02}
                    fontFamily="monospace"
                    fill="#64748b"
                    opacity={0.5}
                  >
                    {buddha.element} · {buddha.wisdom.split(' ')[0]}
                  </text>
                </>
              )}
            </g>
          );
        })}
      </svg>

      {showLabels && (
        <div className="text-center max-w-md">
          {hoveredFamily ? (
            <div className="space-y-1">
              {DHYANI_BUDDHAS.filter(b => b.family === hoveredFamily).map(b => (
                <div key={b.family} className="text-xs space-y-0.5">
                  <div style={{ color: b.color }} className="font-bold">
                    {b.name} ({b.bijaRomaji})
                  </div>
                  <div className="text-gray-400">{b.wisdom}</div>
                  <div className="text-[10px] text-gray-500 font-mono">{b.defilementPurified}</div>
                </div>
              ))}
            </div>
          ) : activeFamily ? (
            <div className="text-[10px] font-mono text-gray-500">
              This practice belongs to the <span className="font-bold" style={{ color: DHYANI_BUDDHAS.find(b => b.family === activeFamily)?.color }}>{activeFamily}</span> family
            </div>
          ) : (
            <div className="text-[10px] font-mono text-gray-600">
              Hover over a Buddha to see their wisdom and defilement purified
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function getNextDirection(dir: MandalaDirection): MandalaDirection {
  const order: MandalaDirection[] = ['east', 'south', 'west', 'north'];
  const idx = order.indexOf(dir);
  return order[(idx + 1) % order.length];
}
