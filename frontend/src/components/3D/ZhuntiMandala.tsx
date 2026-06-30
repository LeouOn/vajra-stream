/**
 * Zhunti (Cundi) Buddha Mother — 3D mandala visualization for Zhunti
 * dharma practice.
 *
 * Renders the eighteen-armed manifestation as radiating golden/white
 * light beams from a central bindu, a rotating dharma wheel with 18
 * spokes, and a lotus throne at the base. The whole composition
 * counter-rotates layered rings for a meditative, ceremonial feel.
 *
 * @component
 */
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type Complexity = 'simple' | 'medium' | 'complex';

interface ZhuntiMandalaProps {
  audioSpectrum: number[];
  isPlaying: boolean;
  frequency: number;
  complexity?: Complexity;
}

interface ArmConfig {
  angle: number;
  length: number;
  width: number;
  layer: number;
}

interface ComplexitySettings {
  armLayers: number;
  rayCount: number;
  spokeCount: number;
  lotusPetalCount: number;
  showOuterHalo: boolean;
}

const ARMS = 18;

const ZHUNTI_GOLD = 0xfbbf24;
const ZHUNTI_GOLD_DEEP = 0xd97706;
const ZHUNTI_WHITE = 0xfff8e7;
const ZHUNTI_ROSE = 0xfda4af;

const COMPLEXITY_TABLE: Record<Complexity, ComplexitySettings> = {
  simple: { armLayers: 1, rayCount: 18, spokeCount: 18, lotusPetalCount: 12, showOuterHalo: false },
  medium: { armLayers: 2, rayCount: 36, spokeCount: 18, lotusPetalCount: 18, showOuterHalo: true },
  complex: { armLayers: 3, rayCount: 54, spokeCount: 18, lotusPetalCount: 24, showOuterHalo: true },
};

/**
 * Build a single radiating "arm" — a thin elongated quad with a gold
 * gradient texture so the beam looks like it's emanating outward.
 */
function createArmGeometry(length: number, width: number): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, 0);
  shape.lineTo(width / 2, 0);
  shape.lineTo(width * 0.35, length);
  shape.lineTo(-width * 0.35, length);
  shape.lineTo(-width / 2, 0);
  return new THREE.ShapeGeometry(shape);
}

function createArmTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 16;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, 'rgba(255, 248, 199, 0)');
    gradient.addColorStop(0.15, 'rgba(255, 235, 130, 0.85)');
    gradient.addColorStop(0.55, 'rgba(251, 191, 36, 0.95)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 1)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const ZhuntiMandala: React.FC<ZhuntiMandalaProps> = ({
  audioSpectrum,
  isPlaying,
  frequency: _frequency,
  complexity = 'medium',
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const armsGroupRef = useRef<THREE.Group>(null);
  const dharmaWheelRef = useRef<THREE.Group>(null);
  const lotusRef = useRef<THREE.Group>(null);
  const innerHaloRef = useRef<THREE.Mesh>(null);
  const outerHaloRef = useRef<THREE.Mesh>(null);
  const centralBinduRef = useRef<THREE.Mesh>(null);

  const settings = COMPLEXITY_TABLE[complexity];

  // 18 radiating arms — always exactly 18 to honor the iconography.
  const arms = useMemo<ArmConfig[]>(() => {
    const list: ArmConfig[] = [];
    const baseLength = 3.6;
    for (let layer = 0; layer < settings.armLayers; layer += 1) {
      for (let i = 0; i < ARMS; i += 1) {
        const layerOffset = (layer * (Math.PI / ARMS)) / Math.max(1, settings.armLayers);
        list.push({
          angle: (i / ARMS) * Math.PI * 2 + layerOffset,
          length: baseLength + layer * 0.55,
          width: 0.32 - layer * 0.08,
          layer,
        });
      }
    }
    return list;
  }, [settings.armLayers]);

  const armTextures = useMemo<THREE.CanvasTexture[]>(() => {
    const tex = createArmTexture();
    return arms.map((arm) => {
      const scale = 1 + arm.layer * 0.15;
      // Each layer reuses the same canvas tex; length scaling handled via geometry
      void scale;
      return tex;
    });
  }, [arms]);

  // Dharma wheel spokes (18).
  const spokes = useMemo<THREE.Line[]>(() => {
    const lines: THREE.Line[] = [];
    const radius = 2.2;
    const material = new THREE.LineBasicMaterial({
      color: new THREE.Color(ZHUNTI_GOLD),
      transparent: true,
      opacity: 0.85,
    });
    for (let i = 0; i < settings.spokeCount; i += 1) {
      const angle = (i / settings.spokeCount) * Math.PI * 2;
      const points = [
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0),
      ];
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      lines.push(new THREE.Line(geo, material));
    }
    return lines;
  }, [settings.spokeCount]);

  // Dharma wheel rim.
  const wheelRim = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.RingGeometry(2.15, 2.25, 64);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(ZHUNTI_GOLD),
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
    });
    return new THREE.Mesh(geo, mat);
  }, []);

  // Lotus throne petals — stacked rings at the base.
  const lotusPetals = useMemo<{ mesh: THREE.Mesh; tier: number }[]>(() => {
    const items: { mesh: THREE.Mesh; tier: number }[] = [];
    const tiers = settings.lotusPetalCount;
    for (let tier = 0; tier < 2; tier += 1) {
      const petalGeo = new THREE.ShapeGeometry(
        (() => {
          const shape = new THREE.Shape();
          const len = 1.0 - tier * 0.2;
          const wid = 0.45 - tier * 0.1;
          shape.moveTo(0, 0);
          shape.bezierCurveTo(wid, len * 0.25, wid * 1.05, len * 0.7, 0, len);
          shape.bezierCurveTo(-wid * 1.05, len * 0.7, -wid, len * 0.25, 0, 0);
          return shape;
        })(),
        18
      );

      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(ZHUNTI_ROSE),
        emissive: new THREE.Color(ZHUNTI_GOLD_DEEP),
        emissiveIntensity: 0.3,
        roughness: 0.4,
        metalness: 0.15,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.92,
      });

      for (let i = 0; i < tiers; i += 1) {
        const mesh = new THREE.Mesh(petalGeo, mat);
        mesh.userData = { baseAngle: (i / tiers) * Math.PI * 2, tier };
        items.push({ mesh, tier });
      }
    }
    return items;
  }, [settings.lotusPetalCount]);

  // Outer halo geometry (only for medium/complex).
  const outerHalo = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.RingGeometry(3.0, 3.6, 64);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(ZHUNTI_GOLD),
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    return new THREE.Mesh(geo, mat);
  }, []);

  // Inner halo always.
  const innerHalo = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.SphereGeometry(1.4, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(ZHUNTI_GOLD),
      transparent: true,
      opacity: 0.12,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    return new THREE.Mesh(geo, mat);
  }, []);

  // Central bindu (point) — pure white-gold sphere.
  const centralBindu = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.SphereGeometry(0.35, 32, 32);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(ZHUNTI_WHITE),
      emissive: new THREE.Color(ZHUNTI_GOLD),
      emissiveIntensity: 0.85,
      roughness: 0.25,
      metalness: 0.35,
    });
    return new THREE.Mesh(geo, mat);
  }, []);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    if (groupRef.current) {
      // Slow contemplative rotation
      groupRef.current.rotation.z += delta * 0.08;
      groupRef.current.rotation.x = Math.sin(time * 0.2) * 0.05;
    }

    // Arms layer — counter-rotate slightly per layer for shimmering rays
    if (armsGroupRef.current) {
      armsGroupRef.current.children.forEach((child, idx) => {
        const layer = arms[idx]?.layer ?? 0;
        const direction = layer % 2 === 0 ? 1 : -1;
        child.rotation.z += delta * 0.3 * direction;

        // Audio reactivity
        let amp = 0;
        if (isPlaying && audioSpectrum.length > 0) {
          const specIdx = Math.floor((idx / armsGroupRef.current.children.length) * audioSpectrum.length);
          amp = audioSpectrum[specIdx] ?? 0;
        }
        // Subtle breathing scale
        const breath = 1 + Math.sin(time * 0.7 + layer * 0.5) * 0.05 + amp * 0.25;
        child.scale.set(1, breath, 1);

        // Material pulse
        const mesh = child.children[0] as THREE.Mesh | undefined;
        if (mesh && mesh.material) {
          const m = mesh.material as THREE.MeshBasicMaterial;
          m.opacity = 0.55 + amp * 0.35 + Math.sin(time + idx) * 0.05;
        }
      });
    }

    // Dharma wheel rotates
    if (dharmaWheelRef.current) {
      dharmaWheelRef.current.rotation.z += delta * 0.2;
    }

    // Lotus throne — gentle vertical breathing, opposite direction
    if (lotusRef.current) {
      lotusRef.current.rotation.z -= delta * 0.05;
      const breath = 1 + Math.sin(time * 0.4) * 0.03;
      lotusRef.current.scale.setScalar(breath);
    }

    // Inner halo breath
    if (innerHaloRef.current) {
      const m = innerHaloRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.1 + Math.sin(time * 0.6) * 0.04;
      innerHaloRef.current.scale.setScalar(1 + Math.sin(time * 0.6) * 0.05);
    }

    // Outer halo subtle shimmer
    if (outerHaloRef.current) {
      const m = outerHaloRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.06 + Math.sin(time * 0.5) * 0.025;
    }

    // Central bindu intense pulse
    if (centralBinduRef.current) {
      const m = centralBinduRef.current.material as THREE.MeshStandardMaterial;
      const pulse = 1 + Math.sin(time * 1.4) * 0.12;
      centralBinduRef.current.scale.setScalar(pulse);
      m.emissiveIntensity = 0.7 + Math.sin(time * 1.4) * 0.25;
    }
  });

  // Render each arm as a pivot with a single mesh — pivot rotates, mesh
  // points outward and we offset by arm.length/2 along y so the shape's
  // base anchors at the pivot center.
  return (
    <group ref={groupRef}>
      <ambientLight intensity={0.4} color={new THREE.Color(ZHUNTI_WHITE)} />
      <pointLight
        position={[0, 0, 6]}
        intensity={1.4}
        color={new THREE.Color(ZHUNTI_GOLD)}
        distance={14}
      />
      <pointLight
        position={[0, 0, -4]}
        intensity={0.6}
        color={new THREE.Color(ZHUNTI_ROSE)}
        distance={10}
      />

      {/* Inner halo */}
      <primitive object={innerHalo} ref={innerHaloRef as unknown as React.RefObject<THREE.Mesh>} />

      {/* 18-armed manifestation */}
      <group ref={armsGroupRef} position={[0, 0, 0.2]}>
        {arms.map((arm, i) => {
          const geo = createArmGeometry(arm.length, arm.width);
          const mat = new THREE.MeshBasicMaterial({
            map: armTextures[i],
            color: new THREE.Color(ZHUNTI_GOLD),
            transparent: true,
            opacity: 0.75,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
          });
          const mesh = new THREE.Mesh(geo, mat);
          // Pivot needs to rotate around z, so we keep mesh oriented along +y
          const pivot = new THREE.Object3D();
          pivot.rotation.z = arm.angle;
          // Move the arm so the wide base sits at origin, tip extends along +y
          mesh.position.set(0, arm.length / 2, 0);
          // Shape extends 0..length along y; that's what we want.
          pivot.add(mesh);
          return (
            <primitive
              key={`arm-${i}`}
              object={pivot}
            />
          );
        })}
      </group>

      {/* Central white-gold bindu */}
      <primitive
        object={centralBindu}
        ref={centralBinduRef as unknown as React.RefObject<THREE.Mesh>}
      />

      {/* Dharma wheel: rim + 18 spokes */}
      <group ref={dharmaWheelRef} position={[0, 0, -0.4]}>
        <primitive object={wheelRim} />
        {spokes.map((spoke, i) => (
          <primitive key={`spoke-${i}`} object={spoke} />
        ))}
        {/* Hub */}
        <mesh>
          <circleGeometry args={[0.25, 32]} />
          <meshBasicMaterial color={new THREE.Color(ZHUNTI_GOLD)} transparent opacity={0.95} />
        </mesh>
      </group>

      {/* Lotus throne at base */}
      <group ref={lotusRef} position={[0, -2.2, -0.2]}>
        {lotusPetals.map((petal, i) => {
          const baseAngle = (petal.mesh.userData as { baseAngle: number }).baseAngle;
          const tier = petal.tier;
          return (
            <primitive
              key={`lotus-${i}`}
              object={
                (() => {
                  const wrapper = new THREE.Object3D();
                  wrapper.add(petal.mesh);
                  wrapper.rotation.z = baseAngle + tier * (Math.PI / settings.lotusPetalCount);
                  wrapper.position.set(0, 0, -tier * 0.1);
                  return wrapper;
                })()
              }
            />
          );
        })}
      </group>

      {/* Optional outer halo */}
      {settings.showOuterHalo && (
        <primitive
          object={outerHalo}
          ref={outerHaloRef as unknown as React.RefObject<THREE.Mesh>}
        />
      )}
    </group>
  );
};

export default ZhuntiMandala;
