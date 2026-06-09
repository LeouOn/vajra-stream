/**
 * Lazy-loaded 3D Sacred Mandala wrapper.
 * Isolates Three.js / @react-three/fiber / @react-three/drei
 * into a single code-split chunk loaded only when the mandala card
 * is rendered (Western system active on the wheel tab).
 */
import React from 'react';
import SacredMandala from '../3D/SacredMandala';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Environment } from '@react-three/drei';

export default function LazySacredMandala({ isPlaying, frequency }) {
  return (
    <Canvas camera={{ position: [0, 0, 12], fov: 55 }}>
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <Stars radius={100} depth={40} count={3000} factor={3} saturation={0.1} fade speed={0.6} />
      <SacredMandala
        isPlaying={isPlaying}
        frequency={frequency}
        pattern="sri-yantra"
        chakra="third-eye"
        complexity="medium"
      />
      <OrbitControls
        enableZoom={true}
        enablePan={false}
        enableRotate={true}
        autoRotate={true}
        autoRotateSpeed={0.3}
      />
      <Environment preset="sunset" />
    </Canvas>
  );
}
