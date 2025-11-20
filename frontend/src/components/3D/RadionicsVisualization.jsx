import React, { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Float, Trail } from '@react-three/drei';
import * as THREE from 'three';

// Rotating crystal geometry component
function Crystal({ position, scale, rotationSpeed, color, attunedRate }) {
  const meshRef = useRef();
  const [hovered, setHover] = useState(false);
  
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * rotationSpeed.x;
      meshRef.current.rotation.y += delta * rotationSpeed.y;
      meshRef.current.rotation.z += delta * rotationSpeed.z;
      
      // Pulsing effect based on attuned rate
      const pulseFactor = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.1;
      meshRef.current.scale.setScalar(scale * pulseFactor);
    }
  });

  const geometry = useMemo(() => {
    const shape = new THREE.Shape();
    const outerRadius = 1;
    const innerRadius = 0.4;
    const points = 8;
    
    for (let i = 0; i < points * 2; i++) {
      const radius = i % 2 === 0 ? outerRadius : innerRadius;
      const angle = (i * Math.PI) / points;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      
      if (i === 0) {
        shape.moveTo(x, y);
      } else {
        shape.lineTo(x, y);
      }
    }
    shape.closePath();
    
    return new THREE.ExtrudeGeometry(shape, {
      depth: 0.2,
      bevelEnabled: true,
      bevelThickness: 0.05,
      bevelSize: 0.05,
      bevelSegments: 8
    });
  }, []);

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
      <Trail
        width={hovered ? 0.3 : 0.1}
        length={hovered ? 20 : 10}
        color={color}
        attenuation={(width) => width}
      >
        <mesh
          ref={meshRef}
          position={position}
          geometry={geometry}
          onPointerOver={() => setHover(true)}
          onPointerOut={() => setHover(false)}
        >
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={hovered ? 0.8 : 0.4}
            metalness={0.8}
            roughness={0.2}
          />
        </mesh>
      </Trail>
    </Float>
  );
}

// Energy ring component
function EnergyRing({ radius, rotationSpeed, color, pulseSpeed }) {
  const meshRef = useRef();
  const materialRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.z += rotationSpeed;
      
      // Pulsing effect
      const pulseFactor = 0.5 + Math.sin(state.clock.elapsedTime * pulseSpeed) * 0.5;
      if (materialRef.current) {
        materialRef.current.opacity = 0.3 + pulseFactor * 0.4;
      }
    }
  });

  const geometry = useMemo(() => {
    return new THREE.RingGeometry(radius * 0.9, radius * 1.1, 64);
  }, [radius]);

  return (
    <mesh ref={meshRef} geometry={geometry} rotation={[Math.PI / 2, 0, 0]}>
      <meshStandardMaterial
        ref={materialRef}
        color={color}
        transparent={true}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}

// Particle field component
function ParticleField({ count, attunedRate }) {
  const points = useRef();
  const particlesRef = useRef();
  
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const radius = 3 + Math.random() * 2;
      
      pos[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = radius * Math.cos(phi);
    }
    return pos;
  }, [count]);

  useFrame((state) => {
    if (particlesRef.current) {
      particlesRef.current.rotation.y += 0.001;
      particlesRef.current.rotation.x += 0.0005;
      
      // Scale particles based on attuned rate
      const rateFactor = parseFloat(attunedRate) || 0;
      const scale = 1 + (rateFactor / 100) * 0.5;
      particlesRef.current.scale.setScalar(scale);
    }
  });

  return (
    <points ref={particlesRef}>
      <bufferGeometry ref={points}>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        color="#ffd700"
        size={0.05}
        transparent={true}
        opacity={0.8}
        sizeAttenuation={true}
      />
    </points>
  );
}

// Central core component
function CentralCore({ attunedRate }) {
  const meshRef = useRef();
  const materialRef = useRef();
  
  useFrame((state) => {
    if (meshRef.current && materialRef.current) {
      meshRef.current.rotation.x += 0.01;
      meshRef.current.rotation.y += 0.01;
      
      // Pulsing based on attuned rate
      const rate = parseFloat(attunedRate) || 0;
      const intensity = 0.5 + (rate / 100) * 0.5;
      materialRef.current.emissiveIntensity = intensity;
    }
  });

  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[0.5, 2]} />
      <meshStandardMaterial
        ref={materialRef}
        color="#8a2be2"
        emissive="#8a2be2"
        emissiveIntensity={0.5}
        metalness={0.9}
        roughness={0.1}
      />
    </mesh>
  );
}

// Main Radionics Visualization component
function RadionicsVisualization({ attunedRate, isPlaying }) {
  const rate = parseFloat(attunedRate) || 0;
  
  return (
    <>
      <Stars
        radius={100}
        depth={50}
        count={2000}
        factor={4}
        saturation={0}
        fade
        speed={0.5}
      />
      
      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#8a2be2" />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#ffd700" />
      
      {/* Central Core */}
      <CentralCore attunedRate={attunedRate} />
      
      {/* Energy Rings */}
      <EnergyRing
        radius={1.5}
        rotationSpeed={0.01}
        color="#8a2be2"
        pulseSpeed={2 + rate / 50}
      />
      <EnergyRing
        radius={2.2}
        rotationSpeed={-0.008}
        color="#4b0082"
        pulseSpeed={1.5 + rate / 100}
      />
      <EnergyRing
        radius={3}
        rotationSpeed={0.005}
        color="#ffd700"
        pulseSpeed={1 + rate / 150}
      />
      
      {/* Rotating Crystals */}
      <Crystal
        position={[2, 0, 0]}
        scale={0.3}
        rotationSpeed={{ x: 0.01, y: 0.02, z: 0.005 }}
        color="#8a2be2"
        attunedRate={attunedRate}
      />
      <Crystal
        position={[-2, 0, 0]}
        scale={0.3}
        rotationSpeed={{ x: -0.01, y: 0.015, z: 0.01 }}
        color="#4b0082"
        attunedRate={attunedRate}
      />
      <Crystal
        position={[0, 2, 0]}
        scale={0.3}
        rotationSpeed={{ x: 0.02, y: 0.005, z: -0.01 }}
        color="#9370db"
        attunedRate={attunedRate}
      />
      <Crystal
        position={[0, -2, 0]}
        scale={0.3}
        rotationSpeed={{ x: 0.005, y: -0.01, z: 0.02 }}
        color="#dda0dd"
        attunedRate={attunedRate}
      />
      <Crystal
        position={[0, 0, 2]}
        scale={0.3}
        rotationSpeed={{ x: -0.005, y: 0.01, z: 0.015 }}
        color="#ba55d3"
        attunedRate={attunedRate}
      />
      <Crystal
        position={[0, 0, -2]}
        scale={0.3}
        rotationSpeed={{ x: 0.015, y: -0.005, z: -0.005 }}
        color="#8b008b"
        attunedRate={attunedRate}
      />
      
      {/* Particle Field */}
      <ParticleField count={500} attunedRate={attunedRate} />
      
      <OrbitControls
        enableZoom={true}
        enablePan={false}
        enableRotate={true}
        autoRotate={true}
        autoRotateSpeed={0.5}
        minDistance={5}
        maxDistance={20}
      />
    </>
  );
}

export default function RadionicsVisualizationCanvas({ attunedRate, isPlaying }) {
  return (
    <div className="w-full h-full">
      <Canvas
        camera={{ position: [0, 0, 10], fov: 60 }}
        className="w-full h-full"
      >
        <RadionicsVisualization attunedRate={attunedRate} isPlaying={isPlaying} />
      </Canvas>
      
      {/* Overlay Info Panel */}
      <div className="absolute top-4 right-4 glassmorphism p-4 rounded-xl mystical-border max-w-xs">
        <h3 className="text-lg font-semibold mb-2 text-vajra-cyan glow-cyan">Radionics Field</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-purple-300">Attuned Rate:</span>
            <span className="frequency-display font-bold">{attunedRate || '0.00'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-purple-300">Field Status:</span>
            <span className={`font-bold ${isPlaying ? 'text-green-400 pulse-glow' : 'text-gray-400'}`}>
              {isPlaying ? 'Active' : 'Idle'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-purple-300">Crystals:</span>
            <span className="text-vajra-purple font-bold">6 Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}