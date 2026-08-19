/**
 * Radionics Globe — 3D Earth with astrological and blessing overlays.
 * React Three Fiber scene displaying a globe with planetary line
 * projections, blessing target markers, and energy emanation effects.
 * @component
 */
import { apiUrl } from '../../utils/api';
import React, { useRef, useState, useEffect, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Text } from '@react-three/drei';
import * as THREE from 'three';
import { DEFAULT_LAT, DEFAULT_LNG } from '../../lib/geo';
import {
  COUNTRY_COORDS,
  resolveTargetCoords as resolveCoords,
  latLonToVec3,
  planetToLatLon,
  createEarthTexture,
  PLANET_COLORS,
  ASPECT_COLORS,
} from './worldEmanationHelpers';

interface PlanetPosition {
  longitude?: number;
  sign?: string;
  retrograde?: boolean;
}
type PlanetPositions = Record<string, PlanetPosition> | null;

interface Aspect {
  planet1: string;
  planet2: string;
  aspect: string;
  exactness?: number;
}

interface Disaster {
  location?: string;
  country?: string;
  title?: string;
  severity?: string;
  lat?: number;
  lon?: number;
}

interface BroadcastTarget {
  location?: string;
  name?: string;
  lat?: number;
  lon?: number;
}

interface MarkerData {
  pos: THREE.Vector3;
  color: string;
  size: number;
  pulseSpeed: number;
  label: string;
  isDisaster?: boolean;
  isTarget?: boolean;
  isPlanet?: boolean;
}

// ─── Atmosphere Glow ───
const Atmosphere: React.FC = () => {
  return (
    <mesh>
      <sphereGeometry args={[2.12, 64, 64]} />
      <shaderMaterial
        transparent
        depthWrite={false}
        uniforms={{
          uTime: { value: 0 },
        }}
        vertexShader={/* glsl */ `
          varying vec3 vNormal;
          varying vec3 vPosition;
          void main() {
            vec4 worldPos = modelMatrix * vec4(position, 1.0);
            vNormal = normalize(mat3(modelMatrix) * normal);
            vPosition = worldPos.xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={/* glsl */ `
          varying vec3 vNormal;
          varying vec3 vPosition;
          void main() {
            vec3 viewDir = normalize(cameraPosition - vPosition);
            float intensity = pow(0.72 - dot(vNormal, viewDir), 3.0);
            gl_FragColor = vec4(0.13, 0.4, 0.93, intensity * 0.35);
          }
        `}
      />
    </mesh>
  );
};

// ─── Pulsing Marker ───
interface MarkerProps {
  position: THREE.Vector3;
  color?: string;
  size?: number;
  pulseSpeed?: number;
}

interface RingProps {
  size: number;
  color: string;
}

const Ring: React.FC<RingProps> = ({ size, color }) => {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ref.current) {
      ref.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 3) * 0.3);
      const mat = ref.current.material as THREE.MeshBasicMaterial;
      mat.opacity = 0.2 + Math.sin(state.clock.elapsedTime * 3) * 0.15;
    }
  });
  return (
    <mesh ref={ref}>
      <ringGeometry args={[size * 0.85, size, 32]} />
      <meshBasicMaterial color={color} transparent opacity={0.3} side={THREE.DoubleSide} />
    </mesh>
  );
};

const Marker: React.FC<MarkerProps> = ({ position, color = '#ff4444', size = 0.06, pulseSpeed = 2 }) => {
  const ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (ref.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * pulseSpeed) * 0.4;
      ref.current.scale.setScalar(hovered ? s * 1.6 : s);
      const mat = ref.current.material as THREE.MeshBasicMaterial;
      mat.opacity = hovered ? 1 : 0.7 + Math.sin(state.clock.elapsedTime * pulseSpeed) * 0.3;
    }
  });

  return (
    <mesh
      ref={ref}
      position={position}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    >
      <sphereGeometry args={[size, 16, 16]} />
      <meshBasicMaterial color={color} transparent opacity={0.8} />
      <Ring size={size * 2.5} color={color} />
    </mesh>
  );
};

// ─── Grid Lines (lat/lon) ───
const GridLines: React.FC = () => {
  const lines = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const R = 2.03;
    // Latitude lines
    for (let lat = -60; lat <= 60; lat += 30) {
      const phi = (90 - lat) * (Math.PI / 180);
      const r = R * Math.cos(phi);
      const y = R * Math.sin(phi);
      for (let i = 0; i <= 64; i++) {
        const theta = (i / 64) * Math.PI * 2;
        pts.push(new THREE.Vector3(r * Math.cos(theta), y, r * Math.sin(theta)));
      }
    }
    // Longitude lines
    for (let lon = 0; lon < 360; lon += 30) {
      const theta = lon * (Math.PI / 180);
      for (let i = 0; i <= 64; i++) {
        const phi = (i / 64) * Math.PI;
        pts.push(new THREE.Vector3(R * Math.sin(phi) * Math.cos(theta), R * Math.cos(phi), R * Math.sin(phi) * Math.sin(theta)));
      }
    }
    return pts;
  }, []);

  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setFromPoints(lines);
    return g;
  }, [lines]);

  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial color="#1e3a5f" transparent opacity={0.25} />
    </lineSegments>
  );
};

// ─── Golden Blessing Rays ───
interface BlessingRaysProps {
  count?: number;
  isActive?: boolean;
}

interface RayConfig {
  angle: number;
  height: number;
  spread: number;
  speed: number;
}

const BlessingRays: React.FC<BlessingRaysProps> = ({ count = 24, isActive = false }) => {
  const groupRef = useRef<THREE.Group>(null);
  const rays = useMemo<RayConfig[]>(() => {
    const r: RayConfig[] = [];
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const height = 2.5 + Math.random() * 3;
      const spread = 0.3 + Math.random() * 0.5;
      r.push({ angle, height, spread, speed: 0.5 + Math.random() * 1.5 });
    }
    return r;
  }, [count]);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    groupRef.current.children.forEach((child, i) => {
      if (rays[i] && child instanceof THREE.Mesh) {
        const s = isActive ? 1 + Math.sin(t * rays[i].speed) * 0.3 : 0.4;
        child.scale.setScalar(s);
        const mat = child.material as THREE.MeshBasicMaterial;
        mat.opacity = isActive ? 0.15 + Math.sin(t * rays[i].speed) * 0.1 : 0.05;
      }
    });
  });

  return (
    <group ref={groupRef}>
      {rays.map((r, i) => {
        const x = Math.cos(r.angle) * r.spread;
        const z = Math.sin(r.angle) * r.spread;
        return (
          <mesh key={i} position={[x, 0, z]} rotation={[0, 0, r.angle]}>
            <cylinderGeometry args={[0.02, 0.08, r.height, 8]} />
            <meshBasicMaterial
              color={i % 3 === 0 ? '#ffd700' : i % 3 === 1 ? '#ff8c42' : '#ffec80'}
              transparent
              opacity={0.1}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </group>
  );
};

// ─── Rainbow Blessing Ring ───
interface RainbowRingProps {
  radius?: number;
  isActive?: boolean;
}

const RainbowRing: React.FC<RainbowRingProps> = ({ radius = 2.25, isActive = false }) => {
  const ref = useRef<THREE.Group>(null);
  const colors = ['#ff4444', '#ff8c00', '#ffdd00', '#00ff88', '#00ccff', '#9966ff', '#cc66ff'];

  useFrame((state) => {
    if (ref.current) {
      const t = state.clock.elapsedTime;
      ref.current.rotation.z += 0.002;
      ref.current.rotation.x = Math.sin(t * 0.3) * 0.1;
      const s = isActive ? 1 + Math.sin(t * 2) * 0.05 : 1;
      ref.current.scale.setScalar(s);
    }
  });

  return (
    <group ref={ref}>
      {colors.map((color, i) => {
        const angle = (i / colors.length) * Math.PI * 2;
        const nextAngle = ((i + 1) / colors.length) * Math.PI * 2;
        const innerR = radius;
        const outerR = radius + 0.12;
        const shape = new THREE.Shape();
        shape.moveTo(Math.cos(angle) * innerR, Math.sin(angle) * innerR);
        shape.lineTo(Math.cos(nextAngle) * innerR, Math.sin(nextAngle) * innerR);
        shape.lineTo(Math.cos(nextAngle) * outerR, Math.sin(nextAngle) * outerR);
        shape.lineTo(Math.cos(angle) * outerR, Math.sin(angle) * outerR);
        shape.closePath();
        return (
          <mesh key={i} rotation={[Math.PI / 2, 0, 0]}>
            <shapeGeometry args={[shape]} />
            <meshBasicMaterial color={color} transparent opacity={0.35} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
        );
      })}
    </group>
  );
};

// Great-circle arc between two points on a sphere
interface AspectLineProps {
  start: THREE.Vector3;
  end: THREE.Vector3;
  color: string;
  aspectType: string;
  exactness?: number;
}

const AspectLine: React.FC<AspectLineProps> = ({ start, end, color, aspectType: _aspectType, exactness = 0.5 }) => {
  const points = useMemo(() => {
    const mid = new THREE.Vector3().addVectors(start, end).normalize().multiplyScalar(2.25 + exactness * 0.3);
    const curve = new THREE.QuadraticBezierCurve3(
      start.clone().normalize().multiplyScalar(2.08),
      mid,
      end.clone().normalize().multiplyScalar(2.08),
    );
    return curve.getPoints(40);
  }, [start, end, exactness]);

  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry().setFromPoints(points);
    return g;
  }, [points]);

  return (
    <line geometry={geo}>
      <lineBasicMaterial color={color} transparent opacity={0.3 + exactness * 0.4} linewidth={1} depthWrite={false} />
    </line>
  );
};

interface AspectLinesProps {
  planetPositions: PlanetPositions;
  aspects: Aspect[] | undefined;
}

const AspectLines: React.FC<AspectLinesProps> = ({ planetPositions, aspects }) => {
  if (!planetPositions || !aspects || aspects.length === 0) return null;

  const lines = aspects.slice(0, 8).map((asp, i) => {
    const p1 = planetPositions[asp.planet1];
    const p2 = planetPositions[asp.planet2];
    if (!p1 || !p2) return null;
    const [lat1, lon1] = planetToLatLon(p1.longitude || 0);
    const [lat2, lon2] = planetToLatLon(p2.longitude || 0);
    const start = latLonToVec3(lat1, lon1);
    const end = latLonToVec3(lat2, lon2);
    const color = ASPECT_COLORS[asp.aspect] || '#94a3b8';
    return (
      <AspectLine key={i} start={start} end={end} color={color} aspectType={asp.aspect} exactness={asp.exactness || 0.5} />
    );
  });

  return <group>{lines}</group>;
};

// ─── Globe Content ───
interface GlobeContentProps {
  disasters?: Disaster[];
  broadcastTargets?: BroadcastTarget[];
  onLocationClick?: (location: unknown) => void;
  showBlessings?: boolean;
  planetPositions?: PlanetPositions;
  aspects?: Aspect[];
}

const GlobeContent: React.FC<GlobeContentProps> = ({
  disasters,
  broadcastTargets,
  onLocationClick: _onLocationClick,
  showBlessings = true,
  planetPositions,
  aspects,
}) => {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
    }
  });

  const earthTex = useMemo(() => createEarthTexture(), []);

  const markerData = useMemo<MarkerData[]>(() => {
    const markers: MarkerData[] = [];
    (disasters || []).forEach((d) => {
      const coords = (d.lat !== undefined && d.lon !== undefined && d.lat !== null && d.lon !== null)
        ? [d.lat, d.lon] as [number, number]
        : resolveCoords(d.location || d.country || d.title || '');
      if (coords) {
        markers.push({
          pos: latLonToVec3(coords[0], coords[1]),
          color: d.severity === 'critical' ? '#ff2222' : d.severity === 'high' ? '#ff8800' : '#ffcc00',
          size: d.severity === 'critical' ? 0.07 : 0.05,
          pulseSpeed: d.severity === 'critical' ? 3 : 2,
          label: (d.title || '').slice(0, 30),
          isDisaster: true,
        });
      }
    });
    (broadcastTargets || []).forEach((t) => {
      const coords = (t.lat !== undefined && t.lon !== undefined && t.lat !== null && t.lon !== null)
        ? [t.lat, t.lon] as [number, number]
        : resolveCoords(t.location || t.name || '');
      if (coords) {
        markers.push({
          pos: latLonToVec3(coords[0], coords[1]),
          color: '#22d3ee',
          size: 0.05,
          pulseSpeed: 1.5,
          label: (t.name || t.location || 'Broadcast').slice(0, 30),
          isTarget: true,
        });
      }
    });
    // Planet markers
    if (planetPositions) {
      Object.entries(planetPositions).forEach(([name, pos]) => {
        if (['ascendant', 'midheaven'].includes(name)) return;
        const [lat, lon] = planetToLatLon(pos.longitude || 0);
        markers.push({
          pos: latLonToVec3(lat, lon),
          color: PLANET_COLORS[name] || '#ffffff',
          size: name === 'sun' ? 0.08 : name === 'moon' ? 0.07 : 0.045,
          pulseSpeed: name === 'sun' ? 1 : name === 'moon' ? 2 : 1.5,
          label: `${name} ${pos.sign || ''} ${pos.retrograde ? '℞' : ''}`,
          isPlanet: true,
        });
      });
    }
    return markers;
  }, [disasters, broadcastTargets, planetPositions]);

  return (
    <group ref={groupRef}>
      <mesh>
        <sphereGeometry args={[2, 64, 64]} />
        <meshStandardMaterial map={earthTex} roughness={0.7} metalness={0.1} />
      </mesh>
      <GridLines />
      <Atmosphere />
      {showBlessings && <BlessingRays isActive={(broadcastTargets || []).length > 0} />}
      {showBlessings && <RainbowRing isActive={(broadcastTargets || []).length > 0} />}
      <AspectLines planetPositions={planetPositions || null} aspects={aspects} />
      {markerData.map((m, i) => (
        <Marker key={i} position={m.pos} color={m.color} size={m.size} pulseSpeed={m.pulseSpeed} />
      ))}
    </group>
  );
};

// ─── Mini Globe for dashboard embedding ───
interface MiniGlobeProps {
  isActive?: boolean;
  size?: 'small' | 'large';
}

export function MiniGlobe({ isActive = false, size = 'small' }: MiniGlobeProps) {
  const h = size === 'small' ? 200 : 320;
  return (
    <div style={{ width: h, height: h }} className="relative">
      <Canvas camera={{ position: [0, 0.3, 4.5], fov: 50 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 3, 5]} intensity={1.0} />
        <Stars radius={30} depth={20} count={800} factor={2} saturation={0} fade speed={0.3} />
        <GlobeContent disasters={[]} broadcastTargets={isActive ? [{ name: 'Active', location: '' }] : []} showBlessings={true} />
        <OrbitControls enableZoom={false} enablePan={false} enableRotate={true} autoRotate={true} autoRotateSpeed={0.3} />
      </Canvas>
    </div>
  );
}

// ─── Main Component ───
interface RadionicsGlobeProps {
  disasters?: Disaster[];
  broadcastTargets?: BroadcastTarget[];
}

export default function RadionicsGlobe({ disasters, broadcastTargets }: RadionicsGlobeProps) {
  const [worldData, setWorldData] = useState<{ disasters: Disaster[]; events: unknown[] }>({ disasters: [], events: [] });
  const [planetPositions, setPlanetPositions] = useState<PlanetPositions>(null);
  const [aspects, setAspects] = useState<Aspect[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(apiUrl(`/operator/world-context`));
        if (res.ok) {
          const data = await res.json() as { disasters?: Disaster[]; events?: unknown[] };
          setWorldData({ disasters: data.disasters || [], events: data.events || [] });
        }
      } catch {
        /* swallow — non-critical telemetry */
      }
    };
    const fetchAstro = async () => {
      try {
        const res = await fetch(apiUrl(`/astrology/current?latitude=${DEFAULT_LAT}&longitude=${DEFAULT_LNG}`));
        if (res.ok) {
          const data = await res.json() as { astrology?: { western?: { positions?: PlanetPositions; aspects?: Aspect[] } } };
          const western = data.astrology?.western;
          setPlanetPositions(western?.positions || null);
          setAspects(western?.aspects || []);
        }
      } catch {
        /* swallow — non-critical telemetry */
      }
    };
    fetchData();
    fetchAstro();
    const interval = setInterval(fetchData, 120000);
    return () => clearInterval(interval);
  }, []);

  const allDisasters = disasters || worldData.disasters;
  const allTargets = broadcastTargets || [];

  return (
    <div className="w-full h-full relative">
      <Canvas camera={{ position: [0, 0.5, 5.5], fov: 45 }}>
        <ambientLight intensity={0.3} />
        <directionalLight position={[5, 3, 5]} intensity={0.8} />
        <Stars radius={50} depth={30} count={2000} factor={3} saturation={0} fade speed={0.5} />
        <GlobeContent
          disasters={allDisasters}
          broadcastTargets={allTargets}
          planetPositions={planetPositions}
          aspects={aspects}
        />
        <OrbitControls
          enableZoom={true}
          enablePan={false}
          minDistance={3.5}
          maxDistance={10}
          autoRotate={false}
        />
      </Canvas>
      {/* Overlay stats */}
      <div className="absolute bottom-3 left-3 flex gap-3 text-[10px] font-mono">
        <div className="bg-black/60 px-2 py-1 rounded border border-red-500/20 text-red-400">
          {allDisasters.length} disasters
        </div>
        <div className="bg-black/60 px-2 py-1 rounded border border-cyan-500/20 text-cyan-400">
          {allTargets.length} targets
        </div>
        {planetPositions && (
          <div className="bg-black/60 px-2 py-1 rounded border border-yellow-500/20 text-yellow-400">
            {Object.values(planetPositions).filter(p => p.retrograde).length} ℞
          </div>
        )}
      </div>
    </div>
  );
}
