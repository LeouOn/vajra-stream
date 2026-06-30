/**
 * Green Tara Lotus — 3D visualization for Green Tara dharma practice.
 *
 * Renders a blooming green lotus flower with petals opening via per-petal
 * rotation, green ambient light, an upward-floating particle system
 * representing merit/compassion, and a soft green glow. Petal count and
 * particle density scale with the `complexity` prop.
 *
 * @component
 */
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type Complexity = 'simple' | 'medium' | 'complex';

interface TaraGreenLotusProps {
  audioSpectrum: number[];
  isPlaying: boolean;
  frequency: number;
  complexity?: Complexity;
}

interface PetalConfig {
  index: number;
  outerAngle: number;
  innerAngle: number;
}

interface ParticleData {
  basePosition: THREE.Vector3;
  speed: number;
  radius: number;
  phase: number;
}

interface ComplexitySettings {
  petalCount: number;
  particleCount: number;
  innerRingCount: number;
  petalSize: number;
}

const TARA_GREEN_PRIMARY = 0x10b981;
const TARA_GREEN_EMERALD = 0x059669;
const TARA_GREEN_SOFT = 0x34d399;
const TARA_GOLD_CORE = 0xfbbf24;

const COMPLEXITY_TABLE: Record<Complexity, ComplexitySettings> = {
  simple: { petalCount: 8, particleCount: 80, innerRingCount: 1, petalSize: 1.0 },
  medium: { petalCount: 12, particleCount: 160, innerRingCount: 2, petalSize: 1.15 },
  complex: { petalCount: 16, particleCount: 260, innerRingCount: 3, petalSize: 1.3 },
};

/**
 * Build a single petal as a curved Shape geometry — wider at the tip,
 * tapered toward the center. The shape is bent slightly forward (z+) to
 * mimic a real lotus petal cupping the center.
 */
function createPetalGeometry(size: number): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  const length = 2.4 * size;
  const halfWidth = 0.9 * size;

  shape.moveTo(0, 0);
  shape.bezierCurveTo(halfWidth, length * 0.15, halfWidth * 1.05, length * 0.6, 0, length);
  shape.bezierCurveTo(-halfWidth * 1.05, length * 0.6, -halfWidth, length * 0.15, 0, 0);

  const geometry = new THREE.ShapeGeometry(shape, 24);
  // Slight forward cup: bend vertices along z proportional to y
  const positions = geometry.attributes.position;
  if (positions) {
    for (let i = 0; i < positions.count; i += 1) {
      const y = positions.getY(i);
      const z = (y / length) * 0.45 * size;
      positions.setZ(i, z);
    }
    positions.needsUpdate = true;
  }
  geometry.computeVertexNormals();
  return geometry;
}

const TaraGreenLotus: React.FC<TaraGreenLotusProps> = ({
  audioSpectrum,
  isPlaying,
  frequency: _frequency,
  complexity = 'medium',
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const petalGroupRef = useRef<THREE.Group>(null);
  const innerRingRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const particlesRef = useRef<THREE.Points>(null);
  const haloRef = useRef<THREE.Mesh>(null);

  const settings = COMPLEXITY_TABLE[complexity];

  // Petal layout: outer ring always; inner rings scale with complexity.
  const petalConfigs = useMemo<PetalConfig[]>(() => {
    const configs: PetalConfig[] = [];
    const outerCount = settings.petalCount;
    for (let i = 0; i < outerCount; i += 1) {
      configs.push({
        index: i,
        outerAngle: (i / outerCount) * Math.PI * 2,
        innerAngle: ((i + 0.5) / outerCount) * Math.PI * 2,
      });
    }
    return configs;
  }, [settings.petalCount]);

  // Pre-build shared petal geometries/materials once per complexity.
  const petals = useMemo<Array<{ mesh: THREE.Mesh; isInner: boolean }>>(() => {
    const petalGeo = createPetalGeometry(settings.petalSize);
    const innerGeo = createPetalGeometry(settings.petalSize * 0.7);

    const outerMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(TARA_GREEN_PRIMARY),
      emissive: new THREE.Color(TARA_GREEN_EMERALD),
      emissiveIntensity: 0.45,
      roughness: 0.35,
      metalness: 0.05,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.92,
    });

    const innerMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(TARA_GREEN_SOFT),
      emissive: new THREE.Color(TARA_GREEN_PRIMARY),
      emissiveIntensity: 0.55,
      roughness: 0.4,
      metalness: 0.05,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95,
    });

    const outerPivots: THREE.Mesh[] = [];
    for (let i = 0; i < petalConfigs.length; i += 1) {
      const pivot = new THREE.Object3D();
      const mesh = new THREE.Mesh(petalGeo, outerMat);
      mesh.position.set(0, 0, 0);
      pivot.add(mesh);
      outerPivots.push(mesh as unknown as THREE.Mesh);
    }

    const innerPivots: THREE.Mesh[] = [];
    if (settings.innerRingCount >= 1) {
      for (let i = 0; i < petalConfigs.length; i += 1) {
        const mesh = new THREE.Mesh(innerGeo, innerMat);
        innerPivots.push(mesh as unknown as THREE.Mesh);
      }
    }

    return [
      ...outerPivots.map((m) => ({ mesh: m, isInner: false })),
      ...innerPivots.map((m) => ({ mesh: m, isInner: true })),
    ];
  }, [petalConfigs, settings.petalSize, settings.innerRingCount]);

  // Particle field representing merit/compassion floating upward.
  const particleData = useMemo<{
    geometry: THREE.BufferGeometry;
    material: THREE.PointsMaterial;
    particles: ParticleData[];
  }>(() => {
    const count = settings.particleCount;
    const positions = new Float32Array(count * 3);
    const particles: ParticleData[] = [];

    for (let i = 0; i < count; i += 1) {
      const radius = 0.4 + Math.random() * 3.2;
      const angle = Math.random() * Math.PI * 2;
      const baseY = (Math.random() - 0.3) * 4.5;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      positions[i * 3] = x;
      positions[i * 3 + 1] = baseY;
      positions[i * 3 + 2] = z;

      particles.push({
        basePosition: new THREE.Vector3(x, baseY, z),
        speed: 0.3 + Math.random() * 0.6,
        radius,
        phase: Math.random() * Math.PI * 2,
      });
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      color: new THREE.Color(TARA_GREEN_SOFT),
      size: 0.08,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    return { geometry, material, particles };
  }, [settings.particleCount]);

  // Halo sphere geometry — shared, single mesh.
  const halo = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.SphereGeometry(2.0, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(TARA_GREEN_PRIMARY),
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.BackSide,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, 0.5, 0);
    return mesh;
  }, []);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    // Slow, contemplative whole-lotus rotation
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.12;
      const breath = 1 + Math.sin(time * 0.6) * 0.04;
      groupRef.current.scale.setScalar(breath);
    }

    // Petal bloom — outer petals opened fully; inner ring rotates closed.
    if (petalGroupRef.current) {
      const bloomProgress = Math.min(1, time * 0.35); // 0 → 1 over ~3s
      const eased = 1 - Math.pow(1 - bloomProgress, 3); // easeOutCubic
      petalGroupRef.current.children.forEach((child, idx) => {
        const cfg = petals[idx];
        if (!cfg) return;
        const targetTilt = cfg.isInner ? -0.05 - eased * 0.05 : -1.45 + eased * 0.3;
        if (cfg.isInner) {
          // Inner petals stand more upright, opposite ring offset
          const offset = cfg.isInner ? Math.PI / petals.length : 0;
          child.rotation.z = targetTilt;
          child.rotation.y = (idx / petals.length) * Math.PI * 2 + offset;
          child.position.set(0, 0.1, 0);
        } else {
          const baseAngle = petalConfigs[idx % petalConfigs.length]?.outerAngle ?? 0;
          child.rotation.y = baseAngle;
          child.rotation.z = targetTilt;
          child.position.set(0, 0, 0);
        }

        // Gentle idle sway
        const sway = Math.sin(time * 0.8 + idx) * 0.04;
        child.rotation.z += sway * 0.1;
      });
    }

    // Inner ring counter-rotates for a layered spinning effect.
    if (innerRingRef.current) {
      innerRingRef.current.rotation.y -= delta * 0.18;
      innerRingRef.current.rotation.x = Math.sin(time * 0.4) * 0.05;
    }

    // Gold core pulse.
    if (coreRef.current) {
      const coreMat = coreRef.current.material as THREE.MeshStandardMaterial;
      const pulse = 1 + Math.sin(time * 1.2) * 0.08;
      coreRef.current.scale.setScalar(pulse);
      coreMat.emissiveIntensity = 0.6 + Math.sin(time * 1.2) * 0.2;
    }

    // Halo breathing.
    if (haloRef.current) {
      const haloMat = haloRef.current.material as THREE.MeshBasicMaterial;
      const haloScale = 1 + Math.sin(time * 0.5) * 0.08;
      haloRef.current.scale.setScalar(haloScale);
      haloMat.opacity = 0.1 + Math.sin(time * 0.5) * 0.04;
    }

    // Particles float upward, loop when too high.
    if (particlesRef.current) {
      const positions = particlesRef.current.geometry.attributes.position;
      if (positions) {
        for (let i = 0; i < particleData.particles.length; i += 1) {
          const p = particleData.particles[i];
          if (!p) continue;
          const y = positions.getY(i);
          let newY = y + delta * p.speed;
          if (newY > 5) {
            newY = -2.5;
          }
          positions.setY(i, newY);
          // Gentle horizontal swirl
          const swirl = Math.sin(time * 0.6 + p.phase) * 0.0015;
          positions.setX(i, positions.getX(i) + swirl);
          positions.setZ(i, positions.getZ(i) + Math.cos(time * 0.6 + p.phase) * 0.0015);
        }
        positions.needsUpdate = true;
      }

      // Audio-reactive boost
      const mat = particlesRef.current.material as THREE.PointsMaterial;
      if (isPlaying && audioSpectrum.length > 0) {
        const avg = audioSpectrum.slice(0, 6).reduce((a, b) => a + b, 0) / 6;
        mat.opacity = 0.6 + avg * 0.4;
        mat.size = 0.08 + avg * 0.1;
      } else {
        mat.opacity = 0.75 + Math.sin(time * 0.5) * 0.1;
        mat.size = 0.08;
      }
    }
  });

  // Distribute petal pivots into the appropriate subgroup on the JSX side.
  const renderPetals = () => {
    const outer = petals.filter((p) => !p.isInner);
    const inner = petals.filter((p) => p.isInner);
    return (
      <>
        <group ref={petalGroupRef}>
          {outer.map((p, i) => (
            <primitive key={`outer-${i}`} object={p.mesh} />
          ))}
        </group>
        {inner.length > 0 && (
          <group ref={innerRingRef}>
            {inner.map((p, i) => (
              <primitive key={`inner-${i}`} object={p.mesh} />
            ))}
          </group>
        )}
      </>
    );
  };

  return (
    <group ref={groupRef}>
      {/* Lighting — soft green ambient + key fill */}
      <ambientLight intensity={0.35} color={new THREE.Color(TARA_GREEN_SOFT)} />
      <pointLight
        position={[0, 3, 4]}
        intensity={1.4}
        color={new THREE.Color(TARA_GREEN_PRIMARY)}
        distance={12}
      />
      <pointLight
        position={[0, -2, 3]}
        intensity={0.8}
        color={new THREE.Color(TARA_GREEN_EMERALD)}
      />

      {/* Soft outer halo */}
      <primitive object={halo} ref={haloRef as unknown as React.RefObject<THREE.Mesh>} />

      {/* Lotus bloom */}
      {renderPetals()}

      {/* Gold core at center */}
      <mesh ref={coreRef} position={[0, 0.2, 0.05]}>
        <icosahedronGeometry args={[0.35, 2]} />
        <meshStandardMaterial
          color={new THREE.Color(TARA_GOLD_CORE)}
          emissive={new THREE.Color(TARA_GOLD_CORE)}
          emissiveIntensity={0.6}
          roughness={0.3}
          metalness={0.4}
        />
      </mesh>

      {/* Rising merit/compassion particles */}
      <primitive
        object={
          new THREE.Points(particleData.geometry, particleData.material)
        }
        ref={particlesRef as unknown as React.RefObject<THREE.Points>}
      />
    </group>
  );
};

export default TaraGreenLotus;
