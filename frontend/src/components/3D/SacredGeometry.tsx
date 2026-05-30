/**
 * SacredGeometry — multi-pattern 3D sacred geometry renderer.
 *
 * Renders six sacred geometry patterns as audio-reactive 3D scenes:
 * Flower of Life, Sri Yantra, Metatron's Cube, Toroidal Field,
 * Merkaba (Star Tetrahedron), and Platonic Solids.
 *
 * All patterns respond to live audio spectrum data: pulsing rings,
 * rotating energy fields, particle emissions, and color shifting.
 *
 * @component
 * @param {{ audioSpectrum, isPlaying, frequency, pattern, colorTheme, particleCount }} props
 */
import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

type SacredPattern = 'flower-of-life' | 'sri-yantra' | 'metatrons-cube' | 'toroidal-field' | 'merkaba' | 'platonic-solids';
type ColorTheme = 'rainbow' | 'cyan-gold' | 'purple-fire' | 'ocean' | 'sunset' | 'ethereal';

interface Props {
  audioSpectrum?: number[];
  isPlaying?: boolean;
  frequency?: number;
  pattern?: SacredPattern;
  colorTheme?: ColorTheme;
  particleCount?: number;
}

const THEMES: Record<ColorTheme, { primary: string; secondary: string; accent: string; bg: string }> = {
  'rainbow':       { primary: '#00bcd4', secondary: '#ffd700', accent: '#ff4081', bg: '#0a0a1a' },
  'cyan-gold':     { primary: '#00e5ff', secondary: '#ffd740', accent: '#ff6e40', bg: '#0a0a20' },
  'purple-fire':   { primary: '#9c27b0', secondary: '#ff5722', accent: '#ffc107', bg: '#0d0d1a' },
  'ocean':         { primary: '#0077b6', secondary: '#00b4d8', accent: '#90e0ef', bg: '#020b15' },
  'sunset':        { primary: '#ff6b35', secondary: '#f7c59f', accent: '#efefd0', bg: '#1a0a0a' },
  'ethereal':      { primary: '#c9b1ff', secondary: '#ffb3d9', accent: '#b3fff0', bg: '#0a0a15' },
};

const PATTERN_NAMES: SacredPattern[] = ['flower-of-life', 'sri-yantra', 'metatrons-cube', 'toroidal-field', 'merkaba', 'platonic-solids'];

const SacredGeometry: React.FC<Props> = ({
  audioSpectrum = [],
  isPlaying = false,
  frequency = 528,
  pattern = 'flower-of-life',
  colorTheme = 'cyan-gold',
  particleCount = 200,
}) => {
  const groupRef = useRef<THREE.Group>(null);
  const particlesRef = useRef<THREE.Points>(null);
  const theme = THEMES[colorTheme];

  // --- Particle system ---
  const particles = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);

    const primaryColor = new THREE.Color(theme.primary);
    const accentColor = new THREE.Color(theme.accent);

    for (let i = 0; i < particleCount; i++) {
      // Toroidal distribution
      const angle = (i / particleCount) * Math.PI * 2;
      const radius = 4 + Math.sin(i * 0.3) * 2;
      const height = Math.cos(i * 0.7) * 3;

      positions[i * 3] = Math.cos(angle) * radius;
      positions[i * 3 + 1] = height;
      positions[i * 3 + 2] = Math.sin(angle) * radius;

      const mixColor = primaryColor.clone().lerp(accentColor, Math.random());
      colors[i * 3] = mixColor.r;
      colors[i * 3 + 1] = mixColor.g;
      colors[i * 3 + 2] = mixColor.b;

      sizes[i] = Math.random() * 0.08 + 0.02;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

    return geo;
  }, [particleCount, theme]);

  // --- Flower of Life ---
  const flowerOfLife = useMemo(() => {
    const group = new THREE.Group();
    const baseRadius = 3;
    const rings: { x: number; y: number; scale: number }[] = [
      { x: 0, y: 0, scale: 1.0 },
      { x: baseRadius, y: 0, scale: 1.0 },
      { x: baseRadius * 0.5, y: baseRadius * 0.866, scale: 1.0 },
      { x: -baseRadius * 0.5, y: baseRadius * 0.866, scale: 1.0 },
      { x: -baseRadius, y: 0, scale: 1.0 },
      { x: -baseRadius * 0.5, y: -baseRadius * 0.866, scale: 1.0 },
      { x: baseRadius * 0.5, y: -baseRadius * 0.866, scale: 1.0 },
      // Second ring
      { x: baseRadius * 2, y: 0, scale: 0.85 },
      { x: baseRadius * 1.5, y: baseRadius * 0.866, scale: 0.85 },
      { x: baseRadius, y: baseRadius * 1.732, scale: 0.85 },
      { x: 0, y: baseRadius * 2, scale: 0.85 },
      { x: -baseRadius, y: baseRadius * 1.732, scale: 0.85 },
      { x: -baseRadius * 1.5, y: baseRadius * 0.866, scale: 0.85 },
      { x: -baseRadius * 2, y: 0, scale: 0.85 },
      { x: -baseRadius * 1.5, y: -baseRadius * 0.866, scale: 0.85 },
      { x: -baseRadius, y: -baseRadius * 1.732, scale: 0.85 },
      { x: 0, y: -baseRadius * 2, scale: 0.85 },
      { x: baseRadius, y: -baseRadius * 1.732, scale: 0.85 },
      { x: baseRadius * 1.5, y: -baseRadius * 0.866, scale: 0.85 },
    ];

    rings.forEach((ring, i) => {
      const geo = new THREE.TorusGeometry(baseRadius * ring.scale, 0.04, 16, 64);
      const mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(theme.primary),
        transparent: true,
        opacity: i === 0 ? 0.7 : 0.35,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(ring.x, ring.y, 0);
      mesh.userData = { baseOpacity: i === 0 ? 0.7 : 0.35, index: i };
      group.add(mesh);
    });

    return group;
  }, [theme]);

  // --- Metatron's Cube ---
  const metatronsCube = useMemo(() => {
    const group = new THREE.Group();
    const r = 2.5;
    const nodes = [
      [0, 0], [r, 0], [r * 0.5, r * 0.866], [-r * 0.5, r * 0.866],
      [-r, 0], [-r * 0.5, -r * 0.866], [r * 0.5, -r * 0.866],
      [r * 2, 0], [r, r * 1.732], [-r, r * 1.732],
      [-r * 2, 0], [-r, -r * 1.732], [r, -r * 1.732],
    ];

    // Spheres at nodes
    nodes.forEach(([x, y], i) => {
      const geo = new THREE.SphereGeometry(i === 0 ? 0.2 : 0.12, 16, 16);
      const mat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(i === 0 ? theme.accent : theme.primary),
        transparent: true,
        opacity: i === 0 ? 0.9 : 0.5,
      });
      const sphere = new THREE.Mesh(geo, mat);
      sphere.position.set(x, y, 0);
      sphere.userData = { baseOpacity: i === 0 ? 0.9 : 0.5, index: i };
      group.add(sphere);
    });

    // Connecting lines
    const lineMat = new THREE.LineBasicMaterial({ color: new THREE.Color(theme.secondary), transparent: true, opacity: 0.2 });
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const pts = [new THREE.Vector3(nodes[i][0], nodes[i][1], 0), new THREE.Vector3(nodes[j][0], nodes[j][1], 0)];
        group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat));
      }
    }

    return group;
  }, [theme]);

  // --- Toroidal Field ---
  const toroidalField = useMemo(() => {
    const group = new THREE.Group();
    // Central torus
    const torusGeo = new THREE.TorusGeometry(3, 0.15, 32, 128);
    const torusMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.primary), transparent: true, opacity: 0.5, wireframe: true });
    group.add(new THREE.Mesh(torusGeo, torusMat));

    // Inner glow torus
    const innerTorus = new THREE.Mesh(
      new THREE.TorusGeometry(2.5, 0.3, 32, 96),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.accent), transparent: true, opacity: 0.2 }),
    );
    group.add(innerTorus);

    // Flow rings
    for (let i = 0; i < 5; i++) {
      const ringGeo = new THREE.TorusGeometry(2.8 + i * 0.15, 0.03, 8, 80);
      const ringMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.secondary), transparent: true, opacity: 0.4 - i * 0.06 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2 + i * 0.3;
      ring.userData = { rotationSpeed: 0.2 + i * 0.1, index: i };
      group.add(ring);
    }

    return group;
  }, [theme]);

  // --- Merkaba (Star Tetrahedron) ---
  const merkaba = useMemo(() => {
    const group = new THREE.Group();
    const size = 3.5;

    // Upward tetrahedron
    const upGeo = new THREE.TetrahedronGeometry(size, 1);
    const upWire = new THREE.Mesh(upGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.primary), wireframe: true, transparent: true, opacity: 0.4 }));
    const upFill = new THREE.Mesh(upGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.primary), transparent: true, opacity: 0.08 }));
    group.add(upWire);
    group.add(upFill);

    // Downward tetrahedron (inverted)
    const downGroup = new THREE.Group();
    const downGeo = new THREE.TetrahedronGeometry(size, 1);
    const downWire = new THREE.Mesh(downGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.secondary), wireframe: true, transparent: true, opacity: 0.4 }));
    const downFill = new THREE.Mesh(downGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.secondary), transparent: true, opacity: 0.08 }));
    downGroup.rotation.z = Math.PI;
    downGroup.add(downWire);
    downGroup.add(downFill);
    group.add(downGroup);

    // Central octahedron
    const octGeo = new THREE.OctahedronGeometry(size * 0.4, 0);
    const octMesh = new THREE.Mesh(octGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.accent), transparent: true, opacity: 0.6 }));
    group.add(octMesh);

    return group;
  }, [theme]);

  // --- Platonic Solids ---
  const platonicSolids = useMemo(() => {
    const group = new THREE.Group();
    const solids = [
      { geo: new THREE.TetrahedronGeometry(1.2, 0), pos: [-2.5, 1.5, 0], color: theme.primary },
      { geo: new THREE.BoxGeometry(1.5, 1.5, 1.5), pos: [2.5, 1.5, 0], color: theme.secondary },
      { geo: new THREE.OctahedronGeometry(1.2, 0), pos: [-2.5, -1.5, 0], color: theme.accent },
      { geo: new THREE.IcosahedronGeometry(1.2, 0), pos: [2.5, -1.5, 0], color: theme.primary },
      { geo: new THREE.DodecahedronGeometry(1.0, 0), pos: [0, 0, 0], color: theme.accent },
    ];

    solids.forEach((s) => {
      const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(s.color), wireframe: true, transparent: true, opacity: 0.5 });
      const mesh = new THREE.Mesh(s.geo, mat);
      mesh.position.set(...s.pos);
      mesh.userData = { rx: Math.random() * 0.5, ry: Math.random() * 0.5, rz: Math.random() * 0.5 };
      group.add(mesh);
    });

    return group;
  }, [theme]);

  // --- Select active pattern ---
  const activeGeometry = useMemo(() => {
    switch (pattern) {
      case 'flower-of-life': return flowerOfLife;
      case 'metatrons-cube': return metatronsCube;
      case 'toroidal-field': return toroidalField;
      case 'merkaba': return merkaba;
      case 'platonic-solids': return platonicSolids;
      default: return flowerOfLife;
    }
  }, [pattern, flowerOfLife, metatronsCube, toroidalField, merkaba, platonicSolids]);

  // --- Animation loop ---
  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const t = state.clock.getElapsedTime();
    const audioBoost = isPlaying && audioSpectrum.length > 0 ? audioSpectrum.slice(0, 8).reduce((a, b) => a + b, 0) / 8 : 0;

    groupRef.current.rotation.z += delta * (0.15 + audioBoost * 0.8);
    groupRef.current.rotation.x += delta * 0.05;

    // Pulse scale
    const scale = 1 + audioBoost * 0.15 + Math.sin(t * 0.7) * 0.03;
    groupRef.current.scale.setScalar(scale);

    // Animate children
    groupRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh && child.userData?.baseOpacity !== undefined) {
        const spectrumIndex = child.userData.index % audioSpectrum.length;
        const amp = audioSpectrum[spectrumIndex] || 0;
        child.material.opacity = (child.userData.baseOpacity as number) + amp * 0.3;
      }
      if (child instanceof THREE.Mesh && child.userData?.rotationSpeed !== undefined) {
        child.rotation.z += delta * (child.userData.rotationSpeed as number);
      }
      if (child instanceof THREE.Mesh && child.userData?.rx !== undefined) {
        child.rotation.x += delta * child.userData.rx;
        child.rotation.y += delta * child.userData.ry;
        child.rotation.z += delta * child.userData.rz;
      }
      // Toroidal field: extra rotation on children
      if (pattern === 'toroidal-field' && child instanceof THREE.Mesh && child.userData?.rotationSpeed !== undefined) {
        child.rotation.y += delta * 0.3;
      }
    });

    // Animate particles
    if (particlesRef.current) {
      particlesRef.current.rotation.y += delta * 0.1;
      particlesRef.current.rotation.z += delta * 0.05;
      const posAttr = particlesRef.current.geometry.attributes.position;
      if (posAttr) {
        for (let i = 0; i < posAttr.count; i++) {
          posAttr.array[i * 3 + 2] += Math.sin(t * 2 + i) * 0.003;
        }
        posAttr.needsUpdate = true;
      }
    }
  });

  return (
    <group ref={groupRef}>
      <primitive object={activeGeometry} />
      <points ref={particlesRef}>
        <bufferGeometry attach="geometry" {...particles} />
        <pointsMaterial
          attach="material"
          size={0.06}
          vertexColors
          transparent
          opacity={0.4 + (isPlaying ? audioSpectrum[0] || 0 : 0) * 0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </points>
    </group>
  );
};

export { PATTERN_NAMES, THEMES };
export default SacredGeometry;
