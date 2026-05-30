/**
 * RothkoGenerator — CSS color-field meditation visuals.
 *
 * Inspired by Mark Rothko's abstract expressionist color-field paintings.
 * Renders soft-edged luminous rectangles that slowly shift in hue,
 * saturation, and position — creating a contemplative meditative space.
 *
 * No Three.js dependency — pure CSS gradients, SVG filters, and animations.
 * Responds to audio frequency data for gentle color modulation.
 *
 * @component
 * @param {{ audioSpectrum, isPlaying, palette, transitionSpeed, fullscreen }} props
 */
import React, { useState, useEffect, useMemo } from 'react';

type PaletteName = 'compassion' | 'wisdom' | 'peace' | 'awakening' | 'emptiness' | 'earth' | 'transcendence' | 'rainbow-body';

interface Props {
  audioSpectrum?: number[];
  isPlaying?: boolean;
  palette?: PaletteName;
  transitionSpeed?: number; // seconds between palette shifts
  fullscreen?: boolean;
}

interface Palette {
  name: string;
  colors: string[];
  bg: string;
  description: string;
}

const PALETTES: Record<PaletteName, Palette> = {
  compassion: {
    name: 'Compassion',
    colors: ['#e8a0bf', '#c75b7a', '#f2d0d9', '#ba274a', '#f9e4e8'],
    bg: '#1a0a0f',
    description: 'Pinks, soft reds, warm whites — the heart of loving-kindness',
  },
  wisdom: {
    name: 'Wisdom',
    colors: ['#1a1a4e', '#2d2b7a', '#4a47a3', '#6b6bc0', '#9090d8'],
    bg: '#080818',
    description: 'Deep blues, purples, indigos — the depths of insight',
  },
  peace: {
    name: 'Peace',
    colors: ['#1a3a2a', '#2d5a3f', '#4a7a5a', '#8fbc8f', '#c8e6c9'],
    bg: '#081008',
    description: 'Gentle greens, soft teals — tranquillity and stillness',
  },
  awakening: {
    name: 'Awakening',
    colors: ['#3d1a00', '#7a3b00', '#c77d20', '#e8b44f', '#fce38a'],
    bg: '#0f0800',
    description: 'Golds, ambers, warm yellows — the light of realization',
  },
  emptiness: {
    name: 'Emptiness',
    colors: ['#1a1a1a', '#2d2d2d', '#4a4a4a', '#808080', '#c0c0c0'],
    bg: '#050505',
    description: 'Greys through white — the luminous nature of emptiness',
  },
  earth: {
    name: 'Earth',
    colors: ['#2d1a0a', '#5c3a1a', '#8b5e3c', '#c4956a', '#d4a574'],
    bg: '#0d0805',
    description: 'Browns, ochres, warm earth tones — grounded presence',
  },
  transcendence: {
    name: 'Transcendence',
    colors: ['#3d001a', '#7a0033', '#c7004c', '#e84d7a', '#ff99b3'],
    bg: '#0a0008',
    description: 'Deep reds through golds — Tibetan thangka colors, sacred fire',
  },
  'rainbow-body': {
    name: 'Rainbow Body',
    colors: ['#ff0000', '#ff8800', '#ffff00', '#00ff00', '#0088ff', '#8800ff', '#ff00ff'],
    bg: '#080818',
    description: 'Full spectrum — the dissolution into pure light',
  },
};

interface ColorBlock {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  color1: string;
  color2: string;
  opacity: number;
  blur: number;
  animDelay: number;
}

const RothkoGenerator: React.FC<Props> = ({
  audioSpectrum = [],
  isPlaying = false,
  palette = 'compassion',
  transitionSpeed = 30,
  fullscreen = false,
}) => {
  const [phase, setPhase] = useState(0);
  const [currentPalette, setCurrentPalette] = useState<Palette>(PALETTES[palette]);

  // Palette cycling
  useEffect(() => {
    setCurrentPalette(PALETTES[palette]);
  }, [palette]);

  // Auto-cycle through palettes
  useEffect(() => {
    const paletteKeys = Object.keys(PALETTES) as PaletteName[];
    const interval = setInterval(() => {
      setPhase((p) => (p + 1) % paletteKeys.length);
      setCurrentPalette(PALETTES[paletteKeys[(phase + 1) % paletteKeys.length]]);
    }, transitionSpeed * 1000);
    return () => clearInterval(interval);
  }, [phase, transitionSpeed]);

  // Generate color blocks
  const blocks: ColorBlock[] = useMemo(() => {
    const result: ColorBlock[] = [];
    const count = 5 + Math.floor(Math.random() * 3);

    for (let i = 0; i < count; i++) {
      const c1 = currentPalette.colors[i % currentPalette.colors.length];
      const c2 = currentPalette.colors[(i + 1) % currentPalette.colors.length];

      result.push({
        id: i,
        x: 15 + Math.random() * 20,
        y: 10 + i * 14 + Math.random() * 4,
        w: 40 + Math.random() * 30,
        h: 10 + Math.random() * 6,
        color1: c1,
        color2: c2,
        opacity: 0.55 + Math.random() * 0.35,
        blur: 12 + Math.random() * 24,
        animDelay: i * 1.5,
      });
    }

    return result;
  }, [currentPalette, phase]);

  // Audio reactivity
  const audioBoost = isPlaying && audioSpectrum.length > 0
    ? audioSpectrum.slice(0, 6).reduce((a, b) => a + b, 0) / 6
    : 0;

  // Breathing overlay
  const BreathOverlay = () => (
    <div
      className="absolute inset-0 pointer-events-none transition-opacity duration-1000"
      style={{
        background: `radial-gradient(ellipse at center, ${currentPalette.colors[2]}08 0%, transparent 70%)`,
        opacity: isPlaying ? 0.3 + audioBoost * 0.4 : 0,
      }}
    />
  );

  return (
    <div
      className={`relative overflow-hidden ${fullscreen ? 'fixed inset-0 z-50' : 'w-full h-full min-h-[400px]'}`}
      style={{ backgroundColor: currentPalette.bg }}
    >
      {/* SVG filter definitions */}
      <svg className="absolute w-0 h-0" aria-hidden="true">
        <defs>
          <filter id="rothko-blur">
            <feGaussianBlur in="SourceGraphic" stdDeviation="20" />
          </filter>
          <filter id="rothko-glow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="40" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
      </svg>

      {/* Color blocks */}
      {blocks.map((block) => (
        <div
          key={`${block.id}-${phase}`}
          className="absolute transition-all"
          style={{
            left: `${block.x}%`,
            top: `${block.y}%`,
            width: `${block.w}%`,
            height: `${block.h}%`,
            background: `linear-gradient(180deg, ${block.color1} 0%, ${block.color2} 100%)`,
            opacity: block.opacity + audioBoost * 0.07,
            filter: `blur(${block.blur + audioBoost * 8}px)`,
            transform: `translateX(${Math.sin(phase + block.id) * 3 + audioBoost * 5}px)`,
            animation: `rothkoFloat ${8 + block.animDelay}s ease-in-out infinite`,
            animationDelay: `${block.animDelay}s`,
          }}
        />
      ))}

      {/* Center glow */}
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
        style={{
          width: '60%',
          height: '40%',
          background: `radial-gradient(ellipse, ${currentPalette.colors[3]}15 0%, transparent 70%)`,
          filter: 'blur(50px)',
          opacity: 0.6 + audioBoost * 0.3,
        }}
      />

      <BreathOverlay />

      {/* Overlay text */}
      <div className="absolute bottom-6 left-0 right-0 text-center pointer-events-none">
        <h3
          className="text-xl font-serif tracking-widest transition-all duration-2000"
          style={{
            color: currentPalette.colors[2],
            opacity: 0.5 + audioBoost * 0.3,
            textShadow: `0 0 20px ${currentPalette.colors[2]}30`,
          }}
        >
          {currentPalette.name}
        </h3>
        <p className="text-xs mt-1 opacity-30" style={{ color: currentPalette.colors[3] }}>
          {currentPalette.description}
        </p>
      </div>

      {/* CSS keyframe animation */}
      <style>{`
        @keyframes rothkoFloat {
          0%, 100% { transform: translateY(0px) scale(1); }
          33% { transform: translateY(-8px) scale(1.02); }
          66% { transform: translateY(4px) scale(0.98); }
        }
        .transition-all {
          transition: left 3s ease, top 3s ease, background 3s ease, opacity 2s ease, filter 2s ease;
        }
      `}</style>
    </div>
  );
};

export { PALETTES };
export default RothkoGenerator;
