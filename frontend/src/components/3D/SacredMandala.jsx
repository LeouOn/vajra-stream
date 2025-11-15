import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

/**
 * Sacred Mandala Generator - Advanced sacred geometry patterns
 * Includes: Sri Yantra, Metatron's Cube, Flower of Life variants, Chakra mandalas
 */
const SacredMandala = ({
  audioSpectrum,
  isPlaying,
  frequency,
  pattern = 'sri-yantra',  // sri-yantra, metatron, seed-of-life, tree-of-life, chakra-mandala
  chakra = 'heart',
  complexity = 'medium'  // simple, medium, complex
}) => {
  const groupRef = useRef();
  const elementRefs = useRef([]);

  // Chakra color mappings
  const chakraColors = useMemo(() => ({
    root: { primary: 0xff0000, secondary: 0xcc0000, name: "Root" },
    sacral: { primary: 0xff6600, secondary: 0xcc5500, name: "Sacral" },
    'solar-plexus': { primary: 0xffff00, secondary: 0xcccc00, name: "Solar Plexus" },
    heart: { primary: 0x00ff00, secondary: 0x00cc00, name: "Heart" },
    throat: { primary: 0x0099ff, secondary: 0x0066cc, name: "Throat" },
    'third-eye': { primary: 0x6600ff, secondary: 0x5500cc, name: "Third Eye" },
    crown: { primary: 0xff00ff, secondary: 0xcc00cc, name: "Crown" }
  }), []);

  // Sri Yantra pattern generator
  const createSriYantra = useMemo(() => {
    const elements = [];
    const baseColor = chakraColors[chakra] || chakraColors.heart;

    // Outer square (Bhupura)
    const squareGeometry = new THREE.PlaneGeometry(10, 10);
    const squareMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(baseColor.primary),
      linewidth: 2
    });

    // Create square outline
    const squarePoints = [
      new THREE.Vector3(-5, -5, 0),
      new THREE.Vector3(5, -5, 0),
      new THREE.Vector3(5, 5, 0),
      new THREE.Vector3(-5, 5, 0),
      new THREE.Vector3(-5, -5, 0)
    ];
    const squareLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(squarePoints),
      squareMaterial
    );
    elements.push(squareLine);

    // Concentric circles (3 levels)
    [4, 3, 2].forEach((radius, index) => {
      const circleGeometry = new THREE.RingGeometry(radius - 0.1, radius, 64);
      const circleMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.primary),
        transparent: true,
        opacity: 0.3 - index * 0.05,
        side: THREE.DoubleSide
      });
      const circle = new THREE.Mesh(circleGeometry, circleMaterial);
      elements.push(circle);
    });

    // Nine interlocking triangles
    // 5 downward (Shakti) + 4 upward (Shiva)
    const triangleConfigs = [
      // Downward triangles (feminine)
      { rotation: Math.PI, size: 3.5, offset: 0, inverted: true },
      { rotation: Math.PI, size: 3, offset: 0.3, inverted: true },
      { rotation: Math.PI, size: 2.5, offset: 0.6, inverted: true },
      { rotation: Math.PI, size: 2, offset: 0.9, inverted: true },
      { rotation: Math.PI, size: 1.5, offset: 1.2, inverted: true },
      // Upward triangles (masculine)
      { rotation: 0, size: 3.2, offset: 0.2, inverted: false },
      { rotation: 0, size: 2.7, offset: 0.5, inverted: false },
      { rotation: 0, size: 2.2, offset: 0.8, inverted: false },
      { rotation: 0, size: 1.7, offset: 1.1, inverted: false },
    ];

    triangleConfigs.forEach((config, index) => {
      const triangleShape = new THREE.Shape();
      const h = config.size * Math.sqrt(3) / 2;

      if (config.inverted) {
        // Downward triangle
        triangleShape.moveTo(0, h / 2);
        triangleShape.lineTo(-config.size / 2, -h / 2);
        triangleShape.lineTo(config.size / 2, -h / 2);
        triangleShape.lineTo(0, h / 2);
      } else {
        // Upward triangle
        triangleShape.moveTo(0, -h / 2);
        triangleShape.lineTo(-config.size / 2, h / 2);
        triangleShape.lineTo(config.size / 2, h / 2);
        triangleShape.lineTo(0, -h / 2);
      }

      const triangleGeometry = new THREE.ShapeGeometry(triangleShape);
      const triangleMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(config.inverted ? baseColor.secondary : baseColor.primary),
        transparent: true,
        opacity: 0.2,
        side: THREE.DoubleSide
      });

      const triangle = new THREE.Mesh(triangleGeometry, triangleMaterial);
      triangle.position.y = config.offset;
      elements.push(triangle);
    });

    // Central bindu (point)
    const binduGeometry = new THREE.CircleGeometry(0.1, 32);
    const binduMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(0xffffff),
      transparent: true,
      opacity: 1
    });
    const bindu = new THREE.Mesh(binduGeometry, binduMaterial);
    elements.push(bindu);

    return elements;
  }, [chakra, chakraColors]);

  // Metatron's Cube pattern
  const createMetatronsCube = useMemo(() => {
    const elements = [];
    const baseColor = chakraColors[chakra] || chakraColors.heart;

    // 13 circles (nodes)
    const radius = 3;
    const circlePositions = [
      { x: 0, y: 0 },  // Center
      // Inner hexagon
      { x: radius, y: 0 },
      { x: radius * 0.5, y: radius * 0.866 },
      { x: -radius * 0.5, y: radius * 0.866 },
      { x: -radius, y: 0 },
      { x: -radius * 0.5, y: -radius * 0.866 },
      { x: radius * 0.5, y: -radius * 0.866 },
      // Outer hexagon
      { x: radius * 2, y: 0 },
      { x: radius, y: radius * 1.732 },
      { x: -radius, y: radius * 1.732 },
      { x: -radius * 2, y: 0 },
      { x: -radius, y: -radius * 1.732 },
      { x: radius, y: -radius * 1.732 },
    ];

    // Create circles at each position
    circlePositions.forEach((pos, index) => {
      const circleGeometry = new THREE.CircleGeometry(0.3, 32);
      const circleMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.primary),
        transparent: true,
        opacity: index === 0 ? 0.8 : 0.5
      });
      const circle = new THREE.Mesh(circleGeometry, circleMaterial);
      circle.position.set(pos.x, pos.y, 0);
      elements.push(circle);
    });

    // Connect all circles with lines
    const lineMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(baseColor.primary),
      transparent: true,
      opacity: 0.3
    });

    for (let i = 0; i < circlePositions.length; i++) {
      for (let j = i + 1; j < circlePositions.length; j++) {
        const points = [
          new THREE.Vector3(circlePositions[i].x, circlePositions[i].y, 0),
          new THREE.Vector3(circlePositions[j].x, circlePositions[j].y, 0)
        ];
        const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(lineGeometry, lineMaterial);
        elements.push(line);
      }
    }

    return elements;
  }, [chakra, chakraColors]);

  // Seed of Life pattern
  const createSeedOfLife = useMemo(() => {
    const elements = [];
    const baseColor = chakraColors[chakra] || chakraColors.heart;
    const radius = 2;

    // Center circle + 6 surrounding circles
    const positions = [
      { x: 0, y: 0 },
      { x: radius, y: 0 },
      { x: radius * 0.5, y: radius * 0.866 },
      { x: -radius * 0.5, y: radius * 0.866 },
      { x: -radius, y: 0 },
      { x: -radius * 0.5, y: -radius * 0.866 },
      { x: radius * 0.5, y: -radius * 0.866 },
    ];

    positions.forEach((pos, index) => {
      const circleGeometry = new THREE.RingGeometry(radius - 0.1, radius, 64);
      const circleMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.primary),
        transparent: true,
        opacity: index === 0 ? 0.5 : 0.3,
        side: THREE.DoubleSide
      });
      const circle = new THREE.Mesh(circleGeometry, circleMaterial);
      circle.position.set(pos.x, pos.y, 0);
      elements.push(circle);

      // Add filled center for each circle
      const centerGeometry = new THREE.CircleGeometry(radius * 0.5, 32);
      const centerMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.secondary),
        transparent: true,
        opacity: 0.2
      });
      const center = new THREE.Mesh(centerGeometry, centerMaterial);
      center.position.set(pos.x, pos.y, 0.01);
      elements.push(center);
    });

    return elements;
  }, [chakra, chakraColors]);

  // Tree of Life (Kabbalah)
  const createTreeOfLife = useMemo(() => {
    const elements = [];
    const baseColor = chakraColors[chakra] || chakraColors.heart;

    // 10 Sephiroth positions
    const sephiroth = [
      { x: 0, y: 4, name: "Kether", size: 0.5 },
      { x: -1.5, y: 2.5, name: "Binah", size: 0.4 },
      { x: 1.5, y: 2.5, name: "Chokmah", size: 0.4 },
      { x: -1.5, y: 0.5, name: "Geburah", size: 0.4 },
      { x: 1.5, y: 0.5, name: "Chesed", size: 0.4 },
      { x: 0, y: 1.5, name: "Tiphareth", size: 0.45 },
      { x: -1.5, y: -1.5, name: "Hod", size: 0.4 },
      { x: 1.5, y: -1.5, name: "Netzach", size: 0.4 },
      { x: 0, y: -0.5, name: "Yesod", size: 0.4 },
      { x: 0, y: -3, name: "Malkuth", size: 0.5 },
    ];

    // Create sephiroth circles
    sephiroth.forEach((seph, index) => {
      const circleGeometry = new THREE.CircleGeometry(seph.size, 32);
      const circleMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.primary),
        transparent: true,
        opacity: 0.6
      });
      const circle = new THREE.Mesh(circleGeometry, circleMaterial);
      circle.position.set(seph.x, seph.y, 0);
      elements.push(circle);

      // Glow
      const glowGeometry = new THREE.CircleGeometry(seph.size * 1.5, 32);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(baseColor.secondary),
        transparent: true,
        opacity: 0.2
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      glow.position.set(seph.x, seph.y, -0.01);
      elements.push(glow);
    });

    // Paths connecting sephiroth
    const paths = [
      [0, 1], [0, 2], [1, 2], [1, 3], [2, 4], [1, 5], [2, 5],
      [3, 4], [3, 5], [4, 5], [5, 6], [5, 7], [6, 7], [6, 8],
      [7, 8], [8, 9], [5, 8]
    ];

    const lineMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(baseColor.primary),
      transparent: true,
      opacity: 0.4
    });

    paths.forEach(([i, j]) => {
      const points = [
        new THREE.Vector3(sephiroth[i].x, sephiroth[i].y, 0),
        new THREE.Vector3(sephiroth[j].x, sephiroth[j].y, 0)
      ];
      const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(lineGeometry, lineMaterial);
      elements.push(line);
    });

    return elements;
  }, [chakra, chakraColors]);

  // Select pattern
  const patternElements = useMemo(() => {
    switch (pattern) {
      case 'sri-yantra':
        return createSriYantra;
      case 'metatron':
        return createMetatronsCube;
      case 'seed-of-life':
        return createSeedOfLife;
      case 'tree-of-life':
        return createTreeOfLife;
      default:
        return createSeedOfLife;
    }
  }, [pattern, createSriYantra, createMetatronsCube, createSeedOfLife, createTreeOfLife]);

  // Animation loop
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const time = state.clock.getElapsedTime();

    // Gentle rotation
    groupRef.current.rotation.z += delta * 0.1;

    // Audio reactivity
    if (isPlaying && audioSpectrum.length > 0) {
      const avgAmplitude = audioSpectrum.slice(0, 10).reduce((a, b) => a + b, 0) / 10;

      // Scale pulse
      const scale = 1 + avgAmplitude * 0.2;
      groupRef.current.scale.setScalar(scale);

      // Faster rotation during audio
      groupRef.current.rotation.z += delta * avgAmplitude * 0.5;

      // Update element opacities
      patternElements.forEach((element, index) => {
        if (element.material && element.material.opacity !== undefined) {
          const baseOpacity = element.material.opacity;
          const spectrumIndex = Math.floor((index / patternElements.length) * audioSpectrum.length);
          const amplitude = audioSpectrum[spectrumIndex] || 0;
          element.material.opacity = baseOpacity + amplitude * 0.3;
        }
      });
    } else {
      // Gentle idle animation
      const idleScale = 1 + Math.sin(time * 0.5) * 0.05;
      groupRef.current.scale.setScalar(idleScale);
    }
  });

  return (
    <group ref={groupRef}>
      {patternElements.map((element, index) => (
        <primitive key={index} object={element} ref={(el) => { elementRefs.current[index] = el; }} />
      ))}
    </group>
  );
};

export default SacredMandala;
