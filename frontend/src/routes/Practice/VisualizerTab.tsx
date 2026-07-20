/**
 * VisualizerTab — 3D sacred geometry + stars (R3F Canvas) with a small
 * in-tab visualization selector.
 *
 * Extracted from the legacy `/visualizers` route's `sacred-geometry` and
 * `sacred-mandala` branches in App.tsx as part of the 12 → 7 nav
 * consolidation (UI rework 2026-06-20). The old header-wide
 * VisualizationSelector dropdown is replaced by this self-contained
 * tab-local selector (Sacred Geometry / Sacred Mandala), matching the
 * spec's "Visualization selector (Sacred Geometry / Mandala / Flower of
 * Life)" requirement.
 *
 * Uses the shared hooks directly (no prop drilling) so the tab stays
 * self-contained inside the Practice tabbed layout.
 *
 * @component
 * @route /practice/visualizers
 */
import React, { Suspense, lazy, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';
import { useWebSocketStable } from '../../hooks/useWebSocketStable';
import { useAudioStore } from '../../stores/audioStore';

const SacredGeometry = lazy(() => import('../../components/3D/SacredGeometry'));
const SacredMandala = lazy(() => import('../../components/3D/SacredMandala'));

type Viz3DMode = 'sacred-geometry' | 'sacred-mandala';

const SELECT_OPTIONS: Array<{ key: Viz3DMode; label: string }> = [
  { key: 'sacred-geometry', label: 'Sacred Geometry' },
  { key: 'sacred-mandala', label: 'Sacred Mandala' },
];

function Loading({ label, tone }: { label: string; tone: string }): React.ReactElement {
  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-900/50">
      <div className={`animate-pulse text-sm ${tone}`}>{label}</div>
    </div>
  );
}

export default function VisualizerTab(): React.ReactElement {
  const [mode, setMode] = useState<Viz3DMode>('sacred-geometry');
  const { audioSpectrum } = useWebSocketStable();
  const isPlaying = useAudioStore((s) => s.isPlaying);
  const frequency = useAudioStore((s) => s.frequency);

  return (
    <div className="relative w-full h-full">
      {/* In-tab visualization selector (replaces the old header dropdown) */}
      <div className="absolute top-3 left-3 z-20 flex gap-2">
        {SELECT_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            onClick={() => setMode(opt.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
              mode === opt.key
                ? 'bg-purple-900 border border-purple-500/30 text-white'
                : 'bg-white/5 border border-transparent text-gray-400 hover:text-white'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {mode === 'sacred-geometry' ? (
        <Suspense fallback={<Loading label="Loading Sacred Geometry..." tone="text-purple-400" />}>
          <Canvas key="sacred-geometry" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
            <SacredGeometry
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              pattern="flower-of-life"
              colorTheme="cyan-gold"
              particleCount={200}
            />
            <OrbitControls enableZoom enablePan={false} enableRotate autoRotate autoRotateSpeed={0.5} />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      ) : (
        <Suspense fallback={<Loading label="Loading Sacred Mandala..." tone="text-amber-400" />}>
          <Canvas key="sacred-mandala" camera={{ position: [0, 0, 8], fov: 60 }} className="w-full h-full">
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <Stars radius={120} depth={50} count={4000} factor={3} saturation={0.1} fade speed={0.8} />
            <SacredMandala
              audioSpectrum={audioSpectrum}
              isPlaying={isPlaying}
              frequency={frequency}
              pattern="sri-yantra"
              chakra="heart"
              complexity="medium"
            />
            <OrbitControls enableZoom enablePan={false} enableRotate autoRotate autoRotateSpeed={0.4} />
            <Environment preset="sunset" />
          </Canvas>
        </Suspense>
      )}
    </div>
  );
}
