import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const SacredGeometry = ({ audioSpectrum, isPlaying, frequency }) => {
  const groupRef = useRef();
  const meshRefs = useRef([]);
  
  // Create sacred geometry pattern - Flower of Life
  const geometry = useMemo(() => {
    const group = new THREE.Group();
    const meshes = [];
    
    // Configuration
    const radius = 3;
    const circles = [
      // Center circle
      { x: 0, y: 0, z: 0, scale: 1 },
      // First ring - 6 circles
      { x: radius, y: 0, z: 0, scale: 1 },
      { x: radius * 0.5, y: radius * 0.866, z: 0, scale: 1 },
      { x: -radius * 0.5, y: radius * 0.866, z: 0, scale: 1 },
      { x: -radius, y: 0, z: 0, scale: 1 },
      { x: -radius * 0.5, y: -radius * 0.866, z: 0, scale: 1 },
      { x: radius * 0.5, y: -radius * 0.866, z: 0, scale: 1 },
      // Second ring - 12 circles
      { x: radius * 2, y: 0, z: 0, scale: 0.8 },
      { x: radius * 1.5, y: radius * 0.866, z: 0, scale: 0.8 },
      { x: radius, y: radius * 1.732, z: 0, scale: 0.8 },
      { x: 0, y: radius * 2, z: 0, scale: 0.8 },
      { x: -radius, y: radius * 1.732, z: 0, scale: 0.8 },
      { x: -radius * 1.5, y: radius * 0.866, z: 0, scale: 0.8 },
      { x: -radius * 2, y: 0, z: 0, scale: 0.8 },
      { x: -radius * 1.5, y: -radius * 0.866, z: 0, scale: 0.8 },
      { x: -radius, y: -radius * 1.732, z: 0, scale: 0.8 },
      { x: 0, y: -radius * 2, z: 0, scale: 0.8 },
      { x: radius, y: -radius * 1.732, z: 0, scale: 0.8 },
      { x: radius * 1.5, y: -radius * 0.866, z: 0, scale: 0.8 },
    ];
    
    circles.forEach((circle, index) => {
      // Create ring geometry for each circle
      const geometry = new THREE.RingGeometry(0, radius * circle.scale, 32);
      
      // Create material with color based on position
      const hue = (index / circles.length) * 0.8 + 0.1; // Range from cyan to purple
      const material = new THREE.MeshBasicMaterial({
        color: new THREE.Color().setHSL(hue, 0.7, 0.5),
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(circle.x, circle.y, circle.z);
      
      // Add to group
      group.add(mesh);
      meshes.push(mesh);
    });
    
    // Store mesh references for animation
    meshRefs.current = meshes;
    
    return group;
  }, []);

  // Animation loop
  useFrame((state, delta) => {
    if (groupRef.current && meshRefs.current.length > 0) {
      const time = state.clock.getElapsedTime();
      
      // Base rotation speed
      const baseRotationSpeed = 0.1;
      
      // Audio-reactive rotation speed
      const audioReactivity = isPlaying && audioSpectrum.length > 0 
        ? (audioSpectrum[0] || 0) * 0.5 
        : 0;
      
      const rotationSpeed = baseRotationSpeed + audioReactivity;
      
      // Rotate entire group
      groupRef.current.rotation.z += rotationSpeed * delta;
      groupRef.current.rotation.x += rotationSpeed * delta * 0.3;
      
      // Animate individual circles
      meshRefs.current.forEach((mesh, index) => {
        if (mesh && isPlaying && audioSpectrum.length > 0) {
          // Get frequency data for this circle
          const spectrumIndex = Math.floor((index / meshRefs.current.length) * audioSpectrum.length);
          const frequencyValue = audioSpectrum[spectrumIndex] || 0;
          
          // Scale based on frequency
          const scale = 1 + frequencyValue * 0.3;
          mesh.scale.setScalar(scale);
          
          // Pulse opacity
          const opacity = 0.3 + frequencyValue * 0.4;
          mesh.material.opacity = opacity;
          
          // Individual rotation
          mesh.rotation.z += delta * (index % 2 === 0 ? 0.5 : -0.5);
          
          // Vertical movement based on frequency
          const verticalOffset = Math.sin(time * 2 + index * 0.5) * frequencyValue * 0.5;
          mesh.position.z = verticalOffset;
        } else {
          // Gentle animation when not playing
          const gentleScale = 1 + Math.sin(time * 0.5 + index * 0.3) * 0.05;
          mesh.scale.setScalar(gentleScale);
          mesh.material.opacity = 0.3;
        }
      });
      
      // Frequency-based color shifting
      if (isPlaying && audioSpectrum.length > 0) {
        const avgFrequency = audioSpectrum.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
        
        meshRefs.current.forEach((mesh, index) => {
          const baseHue = (index / meshRefs.current.length) * 0.8 + 0.1;
          const hueShift = avgFrequency * 0.2;
          const newHue = (baseHue + hueShift) % 1;
          
          mesh.material.color.setHSL(newHue, 0.7, 0.5);
        });
      }
    }
  });

  // Update based on frequency changes
  useEffect(() => {
    if (groupRef.current) {
      // Adjust geometry based on frequency
      const frequencyScale = Math.log10(frequency) / 2; // Logarithmic scaling
      groupRef.current.scale.setScalar(frequencyScale);
    }
  }, [frequency]);

  return (
    <group ref={groupRef}>
      <primitive object={geometry} />
    </group>
  );
};

export default SacredGeometry;