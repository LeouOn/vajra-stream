import React, { useRef, useMemo, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Astrocartography 3D Globe Visualization
 *
 * Displays planetary lines on a rotating Earth globe with:
 * - Planetary Ascendant/Descendant/MC/IC lines
 * - Birth location marker
 * - Power spot indicators
 * - Real-time astrological data integration
 */
export default function Astrocartography({
  birthLocation = { lat: 0, lon: 0, name: "Earth Center" },
  planetaryLines = [],
  audioSpectrum = [],
  isPlaying = false,
  frequency = 136.1,
  showPowerSpots = true,
  autoRotate = true
}) {
  const groupRef = useRef();
  const globeRef = useRef();
  const linesRef = useRef();
  const [rotation, setRotation] = useState(0);
  const [astrologyData, setAstrologyData] = useState(null);

  // Fetch current astrological data
  useEffect(() => {
    const fetchAstrologyData = async () => {
      try {
        const response = await fetch('/api/v1/astrology/planetary-positions');
        const data = await response.json();
        setAstrologyData(data);
      } catch (error) {
        console.error('Failed to fetch astrology data:', error);
      }
    };

    fetchAstrologyData();
    const interval = setInterval(fetchAstrologyData, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  // Convert lat/lon to 3D sphere coordinates
  const latLonToVector3 = (lat, lon, radius = 5) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);

    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);

    return new THREE.Vector3(x, y, z);
  };

  // Create Earth globe texture (simple for now, can be enhanced)
  const globeTexture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 2048;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');

    // Ocean
    ctx.fillStyle = '#0a1128';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Continents (simplified - in production use actual Earth texture)
    ctx.fillStyle = '#1a3a2a';
    ctx.strokeStyle = '#2a5a4a';
    ctx.lineWidth = 2;

    // Draw simplified continents
    const continents = [
      // North America
      { x: 200, y: 300, w: 400, h: 300 },
      // South America
      { x: 300, y: 600, w: 200, h: 250 },
      // Europe
      { x: 900, y: 250, w: 200, h: 150 },
      // Africa
      { x: 950, y: 400, w: 300, h: 400 },
      // Asia
      { x: 1200, y: 200, w: 600, h: 400 },
      // Australia
      { x: 1500, y: 650, w: 200, h: 150 },
    ];

    continents.forEach(cont => {
      ctx.fillRect(cont.x, cont.y, cont.w, cont.h);
      ctx.strokeRect(cont.x, cont.y, cont.w, cont.h);
    });

    // Grid lines (latitude/longitude)
    ctx.strokeStyle = 'rgba(100, 200, 255, 0.2)';
    ctx.lineWidth = 1;

    // Latitude lines
    for (let i = 0; i <= 8; i++) {
      const y = (canvas.height / 8) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Longitude lines
    for (let i = 0; i <= 16; i++) {
      const x = (canvas.width / 16) * i;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }

    return new THREE.CanvasTexture(canvas);
  }, []);

  // Create planetary line curves on the globe
  const planetaryLineMeshes = useMemo(() => {
    if (!planetaryLines || planetaryLines.length === 0) {
      // Default example lines if none provided
      return createDefaultLines();
    }

    return planetaryLines.map((line, index) => {
      const points = [];
      const radius = 5.05; // Slightly above globe surface

      // Create line along longitude (simplified - actual ACG lines are more complex)
      for (let lat = -85; lat <= 85; lat += 5) {
        const pos = latLonToVector3(lat, line.longitude, radius);
        points.push(pos);
      }

      const curve = new THREE.CatmullRomCurve3(points);
      const curvePoints = curve.getPoints(100);
      const geometry = new THREE.BufferGeometry().setFromPoints(curvePoints);

      const color = getPlanetColor(line.planet);

      return (
        <line key={`planetary-line-${index}`}>
          <bufferGeometry attach="geometry" {...geometry} />
          <lineBasicMaterial
            attach="material"
            color={color}
            linewidth={2}
            transparent
            opacity={0.8}
          />
        </line>
      );
    });
  }, [planetaryLines]);

  // Default planetary lines for demonstration
  function createDefaultLines() {
    const defaultPlanets = [
      { planet: 'Sun', longitude: 0, type: 'MC' },
      { planet: 'Moon', longitude: 45, type: 'ASC' },
      { planet: 'Venus', longitude: 90, type: 'DSC' },
      { planet: 'Jupiter', longitude: 135, type: 'IC' },
      { planet: 'Saturn', longitude: 180, type: 'MC' },
      { planet: 'Neptune', longitude: -90, type: 'ASC' },
    ];

    return defaultPlanets.map((line, index) => {
      const points = [];
      const radius = 5.05;

      for (let lat = -85; lat <= 85; lat += 5) {
        const pos = latLonToVector3(lat, line.longitude, radius);
        points.push(pos);
      }

      const curve = new THREE.CatmullRomCurve3(points);
      const curvePoints = curve.getPoints(100);
      const geometry = new THREE.BufferGeometry().setFromPoints(curvePoints);

      const color = getPlanetColor(line.planet);

      return (
        <line key={`default-line-${index}`}>
          <bufferGeometry attach="geometry" {...geometry} />
          <lineBasicMaterial
            attach="material"
            color={color}
            linewidth={3}
            transparent
            opacity={0.7}
          />
        </line>
      );
    });
  }

  // Get color for each planet
  function getPlanetColor(planet) {
    const colors = {
      Sun: '#FFD700',      // Gold
      Moon: '#C0C0C0',     // Silver
      Mercury: '#87CEEB',  // Sky Blue
      Venus: '#FF69B4',    // Pink
      Mars: '#FF4500',     // Red-Orange
      Jupiter: '#9370DB',  // Purple
      Saturn: '#4169E1',   // Royal Blue
      Uranus: '#00CED1',   // Turquoise
      Neptune: '#4B0082',  // Indigo
      Pluto: '#8B4513',    // Brown
    };
    return colors[planet] || '#FFFFFF';
  }

  // Birth location marker
  const birthMarker = useMemo(() => {
    const pos = latLonToVector3(birthLocation.lat, birthLocation.lon, 5.2);
    return (
      <group position={pos.toArray()}>
        <mesh>
          <sphereGeometry args={[0.15, 16, 16]} />
          <meshStandardMaterial
            color="#FF1493"
            emissive="#FF1493"
            emissiveIntensity={1.5}
          />
        </mesh>
        {/* Pulsing ring around birth location */}
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.2, 0.3, 32]} />
          <meshBasicMaterial
            color="#FF1493"
            transparent
            opacity={0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      </group>
    );
  }, [birthLocation]);

  // Power spots (example locations)
  const powerSpots = useMemo(() => {
    if (!showPowerSpots) return null;

    const spots = [
      { lat: 19.8968, lon: -155.5828, name: 'Mauna Kea' },
      { lat: 27.9881, lon: 86.9250, name: 'Mount Everest' },
      { lat: 29.9792, lon: 31.1342, name: 'Giza' },
      { lat: 51.1789, lon: -1.8262, name: 'Stonehenge' },
      { lat: -13.1631, lon: -72.5450, name: 'Machu Picchu' },
      { lat: 36.0965, lon: -112.1129, name: 'Grand Canyon' },
    ];

    return spots.map((spot, index) => {
      const pos = latLonToVector3(spot.lat, spot.lon, 5.15);
      return (
        <mesh key={`power-spot-${index}`} position={pos.toArray()}>
          <sphereGeometry args={[0.08, 12, 12]} />
          <meshStandardMaterial
            color="#00FFFF"
            emissive="#00FFFF"
            emissiveIntensity={1.0}
          />
        </mesh>
      );
    });
  }, [showPowerSpots]);

  // Audio-reactive glow
  const audioReactiveGlow = useMemo(() => {
    const avgAmplitude = audioSpectrum.length > 0
      ? audioSpectrum.reduce((a, b) => a + b, 0) / audioSpectrum.length
      : 0;

    return 0.5 + avgAmplitude * 2;
  }, [audioSpectrum]);

  // Animation loop
  useFrame((state, delta) => {
    if (groupRef.current) {
      // Auto-rotate
      if (autoRotate) {
        groupRef.current.rotation.y += delta * 0.1;
      }

      // Audio-reactive effects
      if (isPlaying && audioSpectrum.length > 0) {
        const avgAmplitude = audioSpectrum.reduce((a, b) => a + b, 0) / audioSpectrum.length;
        groupRef.current.scale.setScalar(1 + avgAmplitude * 0.05);

        // Pulse birth marker
        const birthMarkerGroup = groupRef.current.children.find(child =>
          child.children && child.children[0]?.geometry?.type === 'SphereGeometry'
        );
        if (birthMarkerGroup) {
          birthMarkerGroup.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 3) * 0.2);
        }
      }
    }
  });

  return (
    <group ref={groupRef}>
      {/* Earth Globe */}
      <mesh ref={globeRef}>
        <sphereGeometry args={[5, 64, 64]} />
        <meshStandardMaterial
          map={globeTexture}
          roughness={0.8}
          metalness={0.2}
          emissive="#001540"
          emissiveIntensity={audioReactiveGlow * 0.3}
        />
      </mesh>

      {/* Atmosphere glow */}
      <mesh>
        <sphereGeometry args={[5.2, 64, 64]} />
        <meshBasicMaterial
          color="#4488ff"
          transparent
          opacity={0.1}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Planetary lines */}
      <group ref={linesRef}>
        {planetaryLineMeshes}
      </group>

      {/* Birth location marker */}
      {birthMarker}

      {/* Power spots */}
      {powerSpots}

      {/* Ambient particles around globe */}
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={1000}
            array={new Float32Array(Array.from({ length: 3000 }, () =>
              (Math.random() - 0.5) * 15
            ))}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.05}
          color="#00ffff"
          transparent
          opacity={0.6}
          sizeAttenuation
        />
      </points>

      {/* Orbital ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[7, 0.02, 16, 100]} />
        <meshBasicMaterial
          color="#9370DB"
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* Info overlay (if astrology data available) */}
      {astrologyData && (
        <group position={[0, 6, 0]}>
          {/* This could be enhanced with HTML overlay using @react-three/drei Html component */}
        </group>
      )}
    </group>
  );
}
