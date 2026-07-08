/**
 * Medicine Buddha (Bhaisajyaguru) Healing — 3D visualization for
 * Medicine Buddha dharma practice.
 *
 * Renders a lapis lazuli blue aura radiating outward, healing rays
 * reaching toward the viewer, a subtle breathing pulse, a central
 * medicine bowl/crystal, and a flowing blue particle field representing
 * healing nectar.
 *
 * @component
 */
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type Complexity = 'simple' | 'medium' | 'complex';

interface MedicineBuddhaHealingProps {
  audioSpectrum: number[];
  isPlaying: boolean;
  frequency: number;
  complexity?: Complexity;
}

interface ComplexitySettings {
  rayCount: number;
  particleCount: number;
  haloCount: number;
  pulseSpeed: number;
}

const MEDICINE_BLUE_PRIMARY = 0x3b82f6;
const MEDICINE_LAPIS_DEEP = 0x1e40af;
const MEDICINE_BLUE_SOFT = 0x60a5fa;
const MEDICINE_BLUE_AURA = 0x93c5fd;
const MEDICINE_BOWL_GOLD = 0xfbbf24;
const MEDICINE_NECTAR_GLOW = 0x67e8f9;

const COMPLEXITY_TABLE: Record<Complexity, ComplexitySettings> = {
  simple: { rayCount: 12, particleCount: 90, haloCount: 2, pulseSpeed: 0.8 },
  medium: { rayCount: 18, particleCount: 160, haloCount: 3, pulseSpeed: 1.0 },
  complex: { rayCount: 24, particleCount: 260, haloCount: 4, pulseSpeed: 1.2 },
};

/**
 * Build a beam aimed OUTWARD at the viewer (z+) — a tapered, slightly
 * bowed plane. Points at the camera to enhance "rays reaching the viewer".
 */
function createHealingRayGeometry(): THREE.BufferGeometry {
  const geo = new THREE.PlaneGeometry(0.6, 4.0, 1, 1);
  // Taper top vertexes — pinch z=0 plane slightly along y for visual taper
  const pos = geo.attributes.position;
  if (pos) {
    for (let i = 0; i < pos.count; i += 1) {
      const y = pos.getY(i);
      if (y > 0) {
        pos.setX(i, pos.getX(i) * (1 - y * 0.15));
      }
    }
    pos.needsUpdate = true;
  }
  return geo;
}

function createRayTexture(): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 32;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
    grad.addColorStop(0, 'rgba(147, 197, 253, 0)');
    grad.addColorStop(0.2, 'rgba(96, 165, 250, 0.55)');
    grad.addColorStop(0.7, 'rgba(59, 130, 246, 0.9)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 1)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

const MedicineBuddhaHealing: React.FC<MedicineBuddhaHealingProps> = ({
  audioSpectrum,
  isPlaying,
  frequency: _frequency,
  complexity = 'medium',
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const raysGroupRef = useRef<THREE.Group>(null);
  const bowlRef = useRef<THREE.Group>(null);
  const crystalRef = useRef<THREE.Mesh>(null);
  const auraRef = useRef<THREE.Mesh>(null);
  const halosGroupRef = useRef<THREE.Group>(null);
  const particlesRef = useRef<THREE.Points>(null);
  const lightRef = useRef<THREE.PointLight>(null);

  const settings = COMPLEXITY_TABLE[complexity];

  // Healing rays pivots — each ray is a pivot so we can bloom outward.
  const rays = useMemo<Array<{ pivot: THREE.Object3D; mesh: THREE.Mesh; angle: number }>>(() => {
    const list: Array<{ pivot: THREE.Object3D; mesh: THREE.Mesh; angle: number }> = [];
    const geo = createHealingRayGeometry();
    const tex = createRayTexture();
    for (let i = 0; i < settings.rayCount; i += 1) {
      const angle = (i / settings.rayCount) * Math.PI * 2;
      const mat = new THREE.MeshBasicMaterial({
        map: tex,
        color: new THREE.Color(MEDICINE_BLUE_SOFT),
        transparent: true,
        opacity: 0.55,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(geo, mat);
      // Pivot points at the bowl; mesh translated forward so the base sits at pivot.
      const pivot = new THREE.Object3D();
      pivot.rotation.z = angle;
      pivot.rotation.y = -0.15; // tilt slightly toward viewer
      mesh.position.set(0, 1.5, 0.4);
      pivot.add(mesh);
      list.push({ pivot, mesh, angle });
    }
    return list;
  }, [settings.rayCount]);

  // Medicine bowl — a wide, shallow cone-like lathe shape.
  const bowl = useMemo<THREE.Group>(() => {
    const g = new THREE.Group();
    const bowlGeo = new THREE.LatheGeometry(
      [
        new THREE.Vector2(0.0, 0),
        new THREE.Vector2(0.5, 0),
        new THREE.Vector2(0.85, 0.45),
        new THREE.Vector2(0.95, 0.6),
        new THREE.Vector2(0.85, 0.6),
        new THREE.Vector2(0.92, 0.5),
        new THREE.Vector2(0.0, 0.5),
      ],
      48
    );
    const bowlMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(MEDICINE_BOWL_GOLD),
      emissive: new THREE.Color(MEDICINE_NECTAR_GLOW),
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.85,
    });
    const bowlMesh = new THREE.Mesh(bowlGeo, bowlMat);
    g.add(bowlMesh);

    // Liquid surface disc inside the bowl (the healing nectar)
    const nectarGeo = new THREE.CircleGeometry(0.78, 48);
    const nectarMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(MEDICINE_NECTAR_GLOW),
      emissive: new THREE.Color(MEDICINE_BLUE_AURA),
      emissiveIntensity: 0.7,
      transparent: true,
      opacity: 0.85,
      roughness: 0.1,
      metalness: 0.1,
    });
    const nectar = new THREE.Mesh(nectarGeo, nectarMat);
    nectar.rotation.x = -Math.PI / 2;
    nectar.position.y = 0.45;
    g.add(nectar);

    return g;
  }, []);

  // Crystal at center — small icosahedron with bright emissive
  const crystal = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.IcosahedronGeometry(0.32, 1);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(MEDICINE_BLUE_AURA),
      emissive: new THREE.Color(MEDICINE_BLUE_SOFT),
      emissiveIntensity: 0.9,
      roughness: 0.1,
      metalness: 0.4,
      transparent: true,
      opacity: 0.95,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(0, 0.6, 0);
    return mesh;
  }, []);

  // Concentric aura halos
  const halos = useMemo<THREE.Mesh[]>(() => {
    const meshes: THREE.Mesh[] = [];
    for (let i = 0; i < settings.haloCount; i += 1) {
      const radius = 1.4 + i * 0.55;
      const geo = new THREE.RingGeometry(radius - 0.05, radius, 64);
      const mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(MEDICINE_BLUE_PRIMARY),
        transparent: true,
        opacity: 0.18 - i * 0.04,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.z = -0.1 + i * 0.05;
      meshes.push(mesh);
    }
    return meshes;
  }, [settings.haloCount]);

  // Outer aura sphere (large back-side sphere)
  const aura = useMemo<THREE.Mesh>(() => {
    const geo = new THREE.SphereGeometry(4.0, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(MEDICINE_BLUE_PRIMARY),
      transparent: true,
      opacity: 0.08,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    return new THREE.Mesh(geo, mat);
  }, []);

  // Particles — healing energy in motion, more vertical than Tara.
  const particleData = useMemo<{
    geometry: THREE.BufferGeometry;
    material: THREE.PointsMaterial;
    seeds: Array<{ base: THREE.Vector3; speed: number; phase: number }>;
  }>(() => {
    const count = settings.particleCount;
    const positions = new Float32Array(count * 3);
    const seeds: Array<{ base: THREE.Vector3; speed: number; phase: number }> = [];

    for (let i = 0; i < count; i += 1) {
      const radius = 0.4 + Math.random() * 3.5;
      const angle = Math.random() * Math.PI * 2;
      const yBase = -1 + Math.random() * 4;
      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = yBase;
      positions[i * 3 + 2] = Math.sin(angle) * radius;
      seeds.push({
        base: new THREE.Vector3(Math.cos(angle) * radius, yBase, Math.sin(angle) * radius),
        speed: 0.4 + Math.random() * 0.7,
        phase: Math.random() * Math.PI * 2,
      });
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: new THREE.Color(MEDICINE_BLUE_SOFT),
      size: 0.09,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    return { geometry: geo, material: mat, seeds };
  }, [settings.particleCount]);

  useFrame((state, delta) => {
    const time = state.clock.getElapsedTime();

    // Subtle whole-scene breathing — slower than Tara, more meditative.
    if (groupRef.current) {
      const breath = 1 + Math.sin(time * settings.pulseSpeed) * 0.06;
      groupRef.current.scale.setScalar(breath);
      groupRef.current.rotation.y += delta * 0.06;
    }

    // Rays radiate and pulse opacity with breathing.
    if (raysGroupRef.current) {
      rays.forEach((r, idx) => {
        const breathe = Math.sin(time * settings.pulseSpeed + idx * 0.4) * 0.5 + 0.5;
        r.mesh.scale.setScalar(0.9 + breathe * 0.4);

        // Audio boost
        let amp = 0;
        if (isPlaying && audioSpectrum.length > 0) {
          const idx2 = Math.floor((idx / rays.length) * audioSpectrum.length);
          amp = audioSpectrum[idx2] ?? 0;
        }
        const mat = r.mesh.material as THREE.MeshBasicMaterial;
        mat.opacity = 0.4 + breathe * 0.3 + amp * 0.25;
      });
    }

    // Halos expand and fade in a continuous ripple
    if (halosGroupRef.current) {
      halos.forEach((halo, idx) => {
        const phase = (time * 0.4 + idx / halos.length) % 1;
        const mat = halo.material as THREE.MeshBasicMaterial;
        mat.opacity = (1 - phase) * 0.25;
        const haloScale = 1 + phase * 0.15;
        halo.scale.setScalar(haloScale);
      });
    }

    // Crystal rotates + pulses
    if (crystalRef.current) {
      crystalRef.current.rotation.y += delta * 0.6;
      crystalRef.current.rotation.x += delta * 0.3;
      const pulse = 1 + Math.sin(time * settings.pulseSpeed * 1.4) * 0.15;
      crystalRef.current.scale.setScalar(pulse);
      const m = crystalRef.current.material as THREE.MeshStandardMaterial;
      m.emissiveIntensity = 0.7 + Math.sin(time * settings.pulseSpeed * 1.4) * 0.3;
    }

    // Bowl gentle wobble
    if (bowlRef.current) {
      bowlRef.current.rotation.y = Math.sin(time * 0.3) * 0.08;
      const m = bowlRef.current.children[0] as THREE.Mesh | undefined;
      if (m) {
        const bowlMat = m.material as THREE.MeshStandardMaterial;
        bowlMat.emissiveIntensity = 0.35 + Math.sin(time * settings.pulseSpeed) * 0.1;
      }
    }

    // Outer aura breathing
    if (auraRef.current) {
      const m = auraRef.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.06 + Math.sin(time * settings.pulseSpeed * 0.5) * 0.03;
      auraRef.current.scale.setScalar(1 + Math.sin(time * settings.pulseSpeed * 0.5) * 0.05);
    }

    // Point light pulse (the source of "radiating outward" feel)
    if (lightRef.current) {
      const breath = 1 + Math.sin(time * settings.pulseSpeed) * 0.2;
      lightRef.current.intensity = 1.4 * breath;
    }

    // Particles spiral upward
    if (particlesRef.current) {
      const positions = particlesRef.current.geometry.attributes.position;
      if (positions) {
        for (let i = 0; i < particleData.seeds.length; i += 1) {
          const seed = particleData.seeds[i];
          if (!seed) continue;
          const y = positions.getY(i);
          let newY = y + delta * seed.speed;
          if (newY > 4) {
            newY = -1.5;
          }
          positions.setY(i, newY);
          // Gentle spiral outward
          const radius = seed.base.length();
          const theta = time * 0.4 + seed.phase;
          positions.setX(i, Math.cos(theta) * radius);
          positions.setZ(i, Math.sin(theta) * radius);
        }
        positions.needsUpdate = true;
      }

      const mat = particlesRef.current.material as THREE.PointsMaterial;
      mat.opacity = 0.7 + Math.sin(time * settings.pulseSpeed) * 0.15;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Lighting */}
      <ambientLight intensity={0.3} color={new THREE.Color(MEDICINE_BLUE_AURA)} />
      <pointLight
        ref={lightRef}
        position={[0, 0.6, 1.5]}
        intensity={1.4}
        color={new THREE.Color(MEDICINE_BLUE_PRIMARY)}
        distance={10}
      />
      <pointLight
        position={[0, 1.0, -2]}
        intensity={0.6}
        color={new THREE.Color(MEDICINE_LAPIS_DEEP)}
        distance={8}
      />

      {/* Outer aura */}
      <primitive object={aura} ref={auraRef as unknown as React.RefObject<THREE.Mesh>} />

      {/* Concentric halo ripples */}
      <group ref={halosGroupRef} position={[0, 0, 0]}>
        {halos.map((halo, i) => (
          <primitive key={`halo-${i}`} object={halo} />
        ))}
      </group>

      {/* Healing rays fanning out toward viewer */}
      <group ref={raysGroupRef} position={[0, 0, 0]}>
        {rays.map((ray, i) => (
          <primitive key={`ray-${i}`} object={ray.pivot} />
        ))}
      </group>

      {/* Medicine bowl at center */}
      <group ref={bowlRef} position={[0, -0.3, 0.5]}>
        <primitive object={bowl} />
      </group>

      {/* Crystal on top of bowl */}
      <primitive object={crystal} ref={crystalRef as unknown as React.RefObject<THREE.Mesh>} />

      {/* Healing particles */}
      <primitive
        object={
          new THREE.Points(particleData.geometry, particleData.material)
        }
        ref={particlesRef as unknown as React.RefObject<THREE.Points>}
      />
    </group>
  );
};

export default MedicineBuddhaHealing;
