import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Crystal Grid 3D Visualization
 * Displays crystal arrangements for radionics operations
 */
const CrystalGrid = ({
  audioSpectrum,
  isPlaying,
  frequency,
  gridType = 'hexagon',  // hexagon, double-hexagon, star, grid
  crystalType = 'quartz',
  showEnergyField = true,
  intention = null
}) => {
  const groupRef = useRef();
  const crystalRefs = useRef([]);
  const energyFieldRef = useRef();

  // Crystal configurations
  const configurations = useMemo(() => ({
    // Level 2: Basic hexagon (6 crystals)
    hexagon: {
      name: "Hexagon Grid",
      radius: 4,
      crystals: [
        { angle: 0, distance: 1, size: 1 },
        { angle: 60, distance: 1, size: 1 },
        { angle: 120, distance: 1, size: 1 },
        { angle: 180, distance: 1, size: 1 },
        { angle: 240, distance: 1, size: 1 },
        { angle: 300, distance: 1, size: 1 },
      ]
    },

    // Double hexagon (12 crystals + center)
    'double-hexagon': {
      name: "Double Hexagon Grid",
      radius: 5,
      crystals: [
        // Center crystal
        { angle: 0, distance: 0, size: 1.2 },
        // Inner hexagon
        { angle: 0, distance: 0.8, size: 1 },
        { angle: 60, distance: 0.8, size: 1 },
        { angle: 120, distance: 0.8, size: 1 },
        { angle: 180, distance: 0.8, size: 1 },
        { angle: 240, distance: 0.8, size: 1 },
        { angle: 300, distance: 0.8, size: 1 },
        // Outer hexagon
        { angle: 30, distance: 1.6, size: 0.9 },
        { angle: 90, distance: 1.6, size: 0.9 },
        { angle: 150, distance: 1.6, size: 0.9 },
        { angle: 210, distance: 1.6, size: 0.9 },
        { angle: 270, distance: 1.6, size: 0.9 },
        { angle: 330, distance: 1.6, size: 0.9 },
      ]
    },

    // Star of David pattern (sacred geometry)
    star: {
      name: "Star of David Grid",
      radius: 5,
      crystals: [
        // Center
        { angle: 0, distance: 0, size: 1.3 },
        // Upward triangle
        { angle: 90, distance: 1.5, size: 1.1 },
        { angle: 210, distance: 1.5, size: 1.1 },
        { angle: 330, distance: 1.5, size: 1.1 },
        // Downward triangle
        { angle: 270, distance: 1.5, size: 1.1 },
        { angle: 30, distance: 1.5, size: 1.1 },
        { angle: 150, distance: 1.5, size: 1.1 },
        // Outer points
        { angle: 0, distance: 2.2, size: 0.8 },
        { angle: 60, distance: 2.2, size: 0.8 },
        { angle: 120, distance: 2.2, size: 0.8 },
        { angle: 180, distance: 2.2, size: 0.8 },
        { angle: 240, distance: 2.2, size: 0.8 },
        { angle: 300, distance: 2.2, size: 0.8 },
      ]
    },

    // 3x3 Grid pattern
    grid: {
      name: "3x3 Grid",
      radius: 4,
      crystals: [
        // 3x3 arrangement
        { x: -1, y: -1, size: 1 },
        { x: 0, y: -1, size: 1 },
        { x: 1, y: -1, size: 1 },
        { x: -1, y: 0, size: 1.2 },  // Center row larger
        { x: 0, y: 0, size: 1.4 },   // Center largest
        { x: 1, y: 0, size: 1.2 },
        { x: -1, y: 1, size: 1 },
        { x: 0, y: 1, size: 1 },
        { x: 1, y: 1, size: 1 },
      ]
    }
  }), []);

  // Crystal material properties
  const crystalMaterials = useMemo(() => ({
    quartz: {
      color: new THREE.Color(0xffffff),
      emissive: new THREE.Color(0xccccff),
      opacity: 0.7,
      name: "Clear Quartz"
    },
    amethyst: {
      color: new THREE.Color(0x9966ff),
      emissive: new THREE.Color(0x6633cc),
      opacity: 0.75,
      name: "Amethyst"
    },
    'rose-quartz': {
      color: new THREE.Color(0xffb6c1),
      emissive: new THREE.Color(0xff99aa),
      opacity: 0.7,
      name: "Rose Quartz"
    },
    citrine: {
      color: new THREE.Color(0xffd700),
      emissive: new THREE.Color(0xffaa00),
      opacity: 0.7,
      name: "Citrine"
    },
    'black-tourmaline': {
      color: new THREE.Color(0x222222),
      emissive: new THREE.Color(0x111111),
      opacity: 0.9,
      name: "Black Tourmaline"
    },
    selenite: {
      color: new THREE.Color(0xffffff),
      emissive: new THREE.Color(0xffffee),
      opacity: 0.6,
      name: "Selenite"
    }
  }), []);

  // Create crystal geometries
  const crystals = useMemo(() => {
    const config = configurations[gridType] || configurations.hexagon;
    const material = crystalMaterials[crystalType] || crystalMaterials.quartz;
    const crystalObjects = [];

    config.crystals.forEach((crystal, index) => {
      // Calculate position
      let x, y;
      if (crystal.x !== undefined && crystal.y !== undefined) {
        // Grid layout
        x = crystal.x * 2;
        y = crystal.y * 2;
      } else {
        // Polar layout (angle + distance)
        const angleRad = (crystal.angle * Math.PI) / 180;
        x = Math.cos(angleRad) * crystal.distance * 2;
        y = Math.sin(angleRad) * crystal.distance * 2;
      }

      // Create crystal geometry (pointed hexagonal prism)
      const crystalGeometry = new THREE.ConeGeometry(
        0.3 * crystal.size,  // radius
        1.5 * crystal.size,  // height
        6,                   // segments (hexagonal)
        1,                   // height segments
        false                // open ended
      );

      // Create glowing material
      const crystalMaterial = new THREE.MeshPhysicalMaterial({
        color: material.color,
        emissive: material.emissive,
        emissiveIntensity: 0.3,
        transparent: true,
        opacity: material.opacity,
        metalness: 0.1,
        roughness: 0.2,
        clearcoat: 1.0,
        clearcoatRoughness: 0.1,
        transmission: 0.5,
        thickness: 0.5,
        side: THREE.DoubleSide
      });

      const mesh = new THREE.Mesh(crystalGeometry, crystalMaterial);
      mesh.position.set(x, y, 0.75 * crystal.size);  // Lift up half height
      mesh.rotation.x = 0;  // Point upward

      // Add glow effect
      const glowGeometry = new THREE.SphereGeometry(0.4 * crystal.size, 16, 16);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: material.emissive,
        transparent: true,
        opacity: 0.2
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.copy(mesh.position);
      glow.position.z += 0.5 * crystal.size;

      crystalObjects.push({ mesh, glow, baseSize: crystal.size });
    });

    return crystalObjects;
  }, [gridType, crystalType, configurations, crystalMaterials]);

  // Create energy field visualization
  const energyField = useMemo(() => {
    if (!showEnergyField) return null;

    const config = configurations[gridType] || configurations.hexagon;

    // Create torus (energy ring)
    const geometry = new THREE.TorusGeometry(config.radius, 0.1, 16, 100);
    const material = new THREE.MeshBasicMaterial({
      color: new THREE.Color(0x00ffff),
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide
    });

    return new THREE.Mesh(geometry, material);
  }, [gridType, showEnergyField, configurations]);

  // Create intention text (if provided)
  const intentionObject = useMemo(() => {
    if (!intention) return null;

    // Create canvas for text
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 128;

    // Draw text
    context.fillStyle = '#ffffff';
    context.font = 'bold 32px Arial';
    context.textAlign = 'center';
    context.fillText(intention, 256, 64);

    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas);

    // Create plane for text
    const geometry = new THREE.PlaneGeometry(4, 1);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      opacity: 0.8,
      side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(0, 0, 0.05);  // Slightly above ground

    return mesh;
  }, [intention]);

  // Animation loop
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const time = state.clock.getElapsedTime();

    // Rotate entire group slowly
    groupRef.current.rotation.z += delta * 0.1;

    // Animate crystals
    crystals.forEach((crystal, index) => {
      if (!crystal.mesh) return;

      // Audio reactivity
      if (isPlaying && audioSpectrum.length > 0) {
        const spectrumIndex = Math.floor((index / crystals.length) * audioSpectrum.length);
        const amplitude = audioSpectrum[spectrumIndex] || 0;

        // Pulse scale
        const scale = crystal.baseSize * (1 + amplitude * 0.3);
        crystal.mesh.scale.setScalar(scale);

        // Pulse glow
        if (crystal.glow) {
          crystal.glow.material.opacity = 0.2 + amplitude * 0.4;
          crystal.glow.scale.setScalar(1 + amplitude * 0.5);
        }

        // Increase emissive intensity
        crystal.mesh.material.emissiveIntensity = 0.3 + amplitude * 0.5;

        // Gentle rotation
        crystal.mesh.rotation.y += delta * (1 + amplitude);
      } else {
        // Gentle idle animation
        const idleScale = crystal.baseSize * (1 + Math.sin(time * 0.5 + index * 0.5) * 0.05);
        crystal.mesh.scale.setScalar(idleScale);

        if (crystal.glow) {
          crystal.glow.material.opacity = 0.2 + Math.sin(time + index) * 0.1;
        }

        crystal.mesh.material.emissiveIntensity = 0.3 + Math.sin(time * 0.3 + index * 0.3) * 0.1;
        crystal.mesh.rotation.y += delta * 0.2;
      }

      // Vertical float
      const baseZ = 0.75 * crystal.baseSize;
      crystal.mesh.position.z = baseZ + Math.sin(time * 0.7 + index * 0.4) * 0.1;
      if (crystal.glow) {
        crystal.glow.position.z = crystal.mesh.position.z + 0.5 * crystal.baseSize;
      }
    });

    // Animate energy field
    if (energyFieldRef.current) {
      energyFieldRef.current.rotation.z += delta * 0.3;

      // Pulse opacity based on audio
      if (isPlaying && audioSpectrum.length > 0) {
        const avgAmplitude = audioSpectrum.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
        energyFieldRef.current.material.opacity = 0.3 + avgAmplitude * 0.4;
        energyFieldRef.current.scale.setScalar(1 + avgAmplitude * 0.2);
      } else {
        energyFieldRef.current.material.opacity = 0.3 + Math.sin(time * 0.5) * 0.1;
      }
    }
  });

  return (
    <group ref={groupRef}>
      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[20, 20]} />
        <meshStandardMaterial
          color={new THREE.Color(0x111111)}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Intention text */}
      {intentionObject && <primitive object={intentionObject} />}

      {/* Crystals */}
      {crystals.map((crystal, index) => (
        <React.Fragment key={index}>
          <primitive object={crystal.mesh} ref={(el) => { crystalRefs.current[index] = el; }} />
          {crystal.glow && <primitive object={crystal.glow} />}
        </React.Fragment>
      ))}

      {/* Energy field */}
      {energyField && <primitive object={energyField} ref={energyFieldRef} />}

      {/* Ambient light for crystals */}
      <pointLight position={[0, 0, 10]} intensity={0.5} color={0xffffff} />
      <pointLight position={[5, 5, 5]} intensity={0.3} color={0xccffff} />
      <pointLight position={[-5, -5, 5]} intensity={0.3} color={0xffccff} />
    </group>
  );
};

export default CrystalGrid;
