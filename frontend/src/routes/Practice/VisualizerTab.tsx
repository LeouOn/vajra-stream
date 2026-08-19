/**
 * VisualizerTab — 3D sacred geometry, mandalas, and deity visualizers (R3F Canvas)
 * with an interactive pattern & chakra parameter drawer.
 *
 * Supported Visualizer Modes:
 *   - Sacred Geometry: Flower of Life, Sri Yantra, Metatron's Cube, Toroid, Merkaba, Platonic Solids
 *   - Sacred Mandala: Sri Yantra, Metatron, Seed of Life, Tree of Life, Chakra Mandala
 *   - Zhunti Mandala: 18-arm Cundi Buddha Mother radiating golden light rays
 *   - Green Tara Lotus: 8-16 petal blooming emerald lotus with merit particles
 *
 * Uses the shared audio & WebSocket hooks directly for audio reactivity.
 *
 * @component
 * @route /practice/visualizers
 */
import React, { Suspense, lazy, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import { Select, Switch, Space, Tag, Tooltip } from 'antd';
import { Sparkles, Eye, RotateCw, Palette, Layers } from 'lucide-react';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';

const SacredGeometry = lazy(() => import('../../components/3D/SacredGeometry'));
const SacredMandala = lazy(() => import('../../components/3D/SacredMandala'));
const ZhuntiMandala = lazy(() => import('../../components/3D/ZhuntiMandala'));
const TaraGreenLotus = lazy(() => import('../../components/3D/TaraGreenLotus'));

type Viz3DMode = 'sacred-geometry' | 'sacred-mandala' | 'zhunti' | 'green-tara';
type GeometryPattern =
  | 'flower-of-life'
  | 'sri-yantra'
  | 'metatrons-cube'
  | 'toroidal-field'
  | 'merkaba'
  | 'platonic-solids';
type MandalaPattern =
  | 'sri-yantra'
  | 'metatron'
  | 'seed-of-life'
  | 'tree-of-life'
  | 'chakra-mandala';
type Chakra =
  | 'root'
  | 'sacral'
  | 'solar-plexus'
  | 'heart'
  | 'throat'
  | 'third-eye'
  | 'crown';
type ColorTheme =
  | 'rainbow'
  | 'cyan-gold'
  | 'purple-fire'
  | 'ocean'
  | 'sunset'
  | 'ethereal';
type Complexity = 'simple' | 'medium' | 'complex';

const MODE_OPTIONS: Array<{ key: Viz3DMode; label: string; icon: string }> = [
  { key: 'sacred-geometry', label: 'Sacred Geometry', icon: '✦' },
  { key: 'sacred-mandala', label: 'Sacred Mandala', icon: '☸' },
  { key: 'zhunti', label: 'Zhunti Mother', icon: '☀️' },
  { key: 'green-tara', label: 'Green Tara Lotus', icon: '🪷' },
];

const GEOMETRY_PATTERNS: Array<{ value: GeometryPattern; label: string }> = [
  { value: 'flower-of-life', label: 'Flower of Life' },
  { value: 'sri-yantra', label: 'Sri Yantra' },
  { value: 'metatrons-cube', label: "Metatron's Cube" },
  { value: 'toroidal-field', label: 'Toroidal Field' },
  { value: 'merkaba', label: 'Merkaba Star' },
  { value: 'platonic-solids', label: 'Platonic Solids' },
];

const MANDALA_PATTERNS: Array<{ value: MandalaPattern; label: string }> = [
  { value: 'sri-yantra', label: 'Sri Yantra 9-Triangles' },
  { value: 'metatron', label: 'Metatron Cube Network' },
  { value: 'seed-of-life', label: 'Seed of Life Genesis' },
  { value: 'tree-of-life', label: 'Tree of Life Sephirot' },
  { value: 'chakra-mandala', label: 'Chakra Resonator' },
];

const COLOR_THEMES: Array<{ value: ColorTheme; label: string }> = [
  { value: 'cyan-gold', label: 'Cyan Gold' },
  { value: 'purple-fire', label: 'Purple Fire' },
  { value: 'ocean', label: 'Ocean Blue' },
  { value: 'rainbow', label: 'Rainbow Spectrum' },
  { value: 'sunset', label: 'Sunset Glow' },
  { value: 'ethereal', label: 'Ethereal Violet' },
];

const CHAKRAS: Array<{ value: Chakra; label: string; color: string }> = [
  { value: 'root', label: 'Root (Muladhara)', color: '#ef4444' },
  { value: 'sacral', label: 'Sacral (Svadhisthana)', color: '#f97316' },
  { value: 'solar-plexus', label: 'Solar Plexus (Manipura)', color: '#eab308' },
  { value: 'heart', label: 'Heart (Anahata)', color: '#22c55e' },
  { value: 'throat', label: 'Throat (Vishuddha)', color: '#06b6d4' },
  { value: 'third-eye', label: 'Third Eye (Ajna)', color: '#6366f1' },
  { value: 'crown', label: 'Crown (Sahasrara)', color: '#a855f7' },
];

function Loading({ label, tone }: { label: string; tone: string }): React.ReactElement {
  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-900/50">
      <div className={`animate-pulse text-sm font-mono ${tone}`}>{label}</div>
    </div>
  );
}

export default function VisualizerTab(): React.ReactElement {
  const [mode, setMode] = useState<Viz3DMode>('sacred-geometry');
  const [geomPattern, setGeomPattern] = useState<GeometryPattern>('flower-of-life');
  const [mandalaPattern, setMandalaPattern] = useState<MandalaPattern>('sri-yantra');
  const [colorTheme, setColorTheme] = useState<ColorTheme>('cyan-gold');
  const [chakra, setChakra] = useState<Chakra>('heart');
  const [complexity, setComplexity] = useState<Complexity>('medium');
  const [autoRotate, setAutoRotate] = useState<boolean>(true);
  const [particleCount, setParticleCount] = useState<number>(250);

  const { audioSpectrum } = useWebSocketStable();
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const frequency = useAudioStore((s) => s.frequency);

  return (
    <div className="relative w-full h-full bg-[#050510] overflow-hidden">
      {/* ── Top-Left: Mode Selector ─────────────────────────────────── */}
      <div className="absolute top-3 left-3 z-20 flex gap-2 flex-wrap">
        {MODE_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setMode(opt.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wider transition-all duration-300 flex items-center gap-1.5 ${
              mode === opt.key
                ? 'bg-purple-900/90 border border-purple-400/50 text-white shadow-[0_0_12px_rgba(168,85,247,0.4)]'
                : 'bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:bg-white/10'
            }`}
          >
            <span>{opt.icon}</span>
            <span>{opt.label}</span>
          </button>
        ))}
      </div>

      {/* ── Top-Right: Quick Parameter Controls ─────────────────────── */}
      <div className="absolute top-3 right-3 z-20 flex items-center gap-2.5 p-2 rounded-xl bg-[rgba(20,10,30,0.75)] backdrop-blur-[12px] border border-purple-400/20 text-white text-xs">
        {mode === 'sacred-geometry' && (
          <>
            <Select<GeometryPattern>
              value={geomPattern}
              onChange={setGeomPattern}
              options={GEOMETRY_PATTERNS}
              size="small"
              style={{ width: 145 }}
              popupMatchSelectWidth={false}
            />
            <Select<ColorTheme>
              value={colorTheme}
              onChange={setColorTheme}
              options={COLOR_THEMES}
              size="small"
              style={{ width: 135 }}
              popupMatchSelectWidth={false}
            />
          </>
        )}

        {mode === 'sacred-mandala' && (
          <>
            <Select<MandalaPattern>
              value={mandalaPattern}
              onChange={setMandalaPattern}
              options={MANDALA_PATTERNS}
              size="small"
              style={{ width: 170 }}
              popupMatchSelectWidth={false}
            />
            <Select<Chakra>
              value={chakra}
              onChange={setChakra}
              options={CHAKRAS.map((c) => ({
                value: c.value,
                label: (
                  <span style={{ color: c.color }}>{c.label}</span>
                ),
              }))}
              size="small"
              style={{ width: 165 }}
              popupMatchSelectWidth={false}
            />
          </>
        )}

        {(mode === 'zhunti' || mode === 'green-tara' || mode === 'sacred-mandala') && (
          <Select<Complexity>
            value={complexity}
            onChange={setComplexity}
            options={[
              { value: 'simple', label: 'Simple' },
              { value: 'medium', label: 'Medium' },
              { value: 'complex', label: 'Complex' },
            ]}
            size="small"
            style={{ width: 95 }}
          />
        )}

        <Tooltip title="Toggle 3D auto-rotation">
          <div className="flex items-center gap-1.5 pl-1.5 border-l border-white/10">
            <RotateCw size={13} className={autoRotate ? 'text-purple-300' : 'text-gray-500'} />
            <Switch
              size="small"
              checked={autoRotate}
              onChange={setAutoRotate}
              aria-label="Toggle 3D auto-rotation"
            />
          </div>
        </Tooltip>
      </div>

      {/* ── 3D Canvas Viewport ──────────────────────────────────────── */}
      {mode === 'sacred-geometry' && (
        <Suspense fallback={<Loading label="Loading Sacred Geometry..." tone="text-purple-400" />}>
          <Canvas key="sacred-geometry" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
            <SacredGeometry
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              pattern={geomPattern}
              colorTheme={colorTheme}
              particleCount={particleCount}
            />
            <OrbitControls
              enableZoom
              enablePan={false}
              enableRotate
              autoRotate={autoRotate}
              autoRotateSpeed={0.5}
            />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      )}

      {mode === 'sacred-mandala' && (
        <Suspense fallback={<Loading label="Loading Sacred Mandala..." tone="text-amber-400" />}>
          <Canvas key="sacred-mandala" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <Stars radius={120} depth={50} count={4000} factor={3} saturation={0.1} fade speed={0.8} />
            <SacredMandala
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              pattern={mandalaPattern}
              chakra={chakra}
              complexity={complexity}
            />
            <OrbitControls
              enableZoom
              enablePan={false}
              enableRotate
              autoRotate={autoRotate}
              autoRotateSpeed={0.4}
            />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      )}

      {mode === 'zhunti' && (
        <Suspense fallback={<Loading label="Loading Zhunti Mother Mandala..." tone="text-amber-300" />}>
          <Canvas key="zhunti" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.6} />
            <pointLight position={[10, 10, 10]} intensity={1.2} />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color="#fbbf24" />
            <Stars radius={100} depth={50} count={4500} factor={4} saturation={0.2} fade speed={0.7} />
            <ZhuntiMandala
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              complexity={complexity}
            />
            <OrbitControls
              enableZoom
              enablePan={false}
              enableRotate
              autoRotate={autoRotate}
              autoRotateSpeed={0.35}
            />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      )}

      {mode === 'green-tara' && (
        <Suspense fallback={<Loading label="Loading Green Tara Lotus..." tone="text-emerald-400" />}>
          <Canvas key="green-tara" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.6} />
            <pointLight position={[0, 10, 10]} intensity={1.2} color="#34d399" />
            <pointLight position={[0, -5, 5]} intensity={0.8} color="#10b981" />
            <Stars radius={100} depth={50} count={4000} factor={3} saturation={0.3} fade speed={0.6} />
            <TaraGreenLotus
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              complexity={complexity}
            />
            <OrbitControls
              enableZoom
              enablePan={false}
              enableRotate
              autoRotate={autoRotate}
              autoRotateSpeed={0.4}
            />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      )}

      {/* ── Frequency & Live Status Badge (Bottom-Left) ─────────────── */}
      <div className="absolute bottom-3 left-3 z-20 flex items-center gap-2 pointer-events-none">
        <span className="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-black/60 backdrop-blur-md border border-white/10 text-purple-300">
          λ {frequency.toFixed(1)} Hz {isPlaying ? '• Audio Reactive' : ''}
        </span>
      </div>
    </div>
  );
}
