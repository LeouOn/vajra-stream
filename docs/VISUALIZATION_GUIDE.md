# 🔮 Visualization Systems Guide

## Overview

Vajra.Stream now features three advanced 3D visualization systems for meditation, radionics operations, and sacred geometry exploration. All visualizations are fully audio-reactive and integrate with the frequency generation system.

## Visualization Types

### 1. Crystal Grid Visualization

Interactive 3D representation of physical crystal grids used in radionics operations.

**Features:**
- Multiple grid patterns (hexagon, double hexagon, star, 3x3 grid)
- 6 crystal types with authentic materials (quartz, amethyst, rose quartz, etc.)
- Energy field visualization
- Intention text display
- Full audio reactivity
- Realistic crystal rendering with transparency and refraction

**File**: `frontend/src/components/3D/CrystalGrid.jsx`

#### Available Grid Patterns

##### Hexagon Grid (Basic - Level 2)
```javascript
gridType="hexagon"
```
- 6 crystals in hexagonal arrangement
- Perfect for basic radionics operations
- Mirrors physical Level 2 setup

##### Double Hexagon Grid (Advanced)
```javascript
gridType="double-hexagon"
```
- 13 crystals: 1 center + 2 hexagonal rings
- Enhanced power and complexity
- Recommended for serious practice

##### Star of David Grid (Sacred Geometry)
```javascript
gridType="star"
```
- 13 crystals in Star of David pattern
- Combines masculine/feminine energies
- Sacred geometry amplification

##### 3x3 Grid
```javascript
gridType="grid"
```
- 9 crystals in square arrangement
- Structured, grounding energy
- Good for specific targeting

#### Crystal Types

```javascript
// Clear Quartz (default) - Amplification, clarity
crystalType="quartz"

// Amethyst - Spiritual connection, transmutation
crystalType="amethyst"

// Rose Quartz - Love, heart healing
crystalType="rose-quartz"

// Citrine - Manifestation, abundance
crystalType="citrine"

// Black Tourmaline - Protection, grounding
crystalType="black-tourmaline"

// Selenite - Cleansing, angelic connection
crystalType="selenite"
```

#### Usage Example

```jsx
<CrystalGrid
  audioSpectrum={audioSpectrum}
  isPlaying={isPlaying}
  frequency={frequency}
  gridType="double-hexagon"
  crystalType="amethyst"
  showEnergyField={true}
  intention="May all beings be healed"
/>
```

#### Customization Options

```jsx
// Props available
{
  gridType: 'hexagon' | 'double-hexagon' | 'star' | 'grid',
  crystalType: 'quartz' | 'amethyst' | 'rose-quartz' | 'citrine' | 'black-tourmaline' | 'selenite',
  showEnergyField: boolean,  // Show torus energy field
  intention: string,         // Text displayed in center
  audioSpectrum: number[],   // Audio spectrum data
  isPlaying: boolean,        // Audio playing state
  frequency: number          // Base frequency
}
```

### 2. Sacred Mandala Visualization

Advanced sacred geometry patterns from various spiritual traditions.

**Features:**
- Sri Yantra (Tantric sacred geometry)
- Metatron's Cube (Hermetic sacred geometry)
- Seed of Life (Creation pattern)
- Tree of Life (Kabbalah)
- Chakra-based coloring
- Full audio reactivity
- Multiple complexity levels

**File**: `frontend/src/components/3D/SacredMandala.jsx`

#### Available Patterns

##### Sri Yantra
```javascript
pattern="sri-yantra"
```
**Description**: The supreme sacred geometry of Tantric tradition
- 9 interlocking triangles (5 Shakti + 4 Shiva)
- Central bindu (divine point)
- 3 concentric circles
- Outer square (Bhupura)
- Represents cosmic creation

**Best for**: Deep meditation, cosmic connection, manifestation

##### Metatron's Cube
```javascript
pattern="metatron"
```
**Description**: Contains all Platonic solids, foundation of creation
- 13 circles (nodes)
- All points interconnected
- Hermetic tradition
- Contains all 5 Platonic solids

**Best for**: Understanding universal structure, sacred geometry study

##### Seed of Life
```javascript
pattern="seed-of-life"
```
**Description**: Genesis pattern, foundation of Flower of Life
- 7 circles (1 center + 6 surrounding)
- Represents 7 days of creation
- Fundamental pattern

**Best for**: New beginnings, creativity, manifestation

##### Tree of Life
```javascript
pattern="tree-of-life"
```
**Description**: Kabbalistic diagram of divine emanation
- 10 Sephiroth (divine attributes)
- 22 paths connecting them
- Maps spiritual journey
- Hebrew mysticism

**Best for**: Spiritual development, understanding divine attributes

#### Chakra Coloring

```javascript
// Root Chakra - Red
chakra="root"

// Sacral Chakra - Orange
chakra="sacral"

// Solar Plexus - Yellow
chakra="solar-plexus"

// Heart Chakra - Green (default)
chakra="heart"

// Throat Chakra - Blue
chakra="throat"

// Third Eye - Indigo
chakra="third-eye"

// Crown Chakra - Violet
chakra="crown"
```

#### Usage Example

```jsx
<SacredMandala
  audioSpectrum={audioSpectrum}
  isPlaying={isPlaying}
  frequency={frequency}
  pattern="sri-yantra"
  chakra="heart"
  complexity="medium"
/>
```

### 3. Flower of Life (Sacred Geometry)

The original sacred geometry visualization, now enhanced.

**Features:**
- Classic Flower of Life pattern
- Multiple rings of circles
- Audio-reactive scaling and color
- Smooth animations
- Frequency-based transformations

**File**: `frontend/src/components/3D/SacredGeometry.jsx`

#### Usage Example

```jsx
<SacredGeometry
  audioSpectrum={audioSpectrum}
  isPlaying={isPlaying}
  frequency={frequency}
/>
```

## Integration with Audio System

All visualizations respond to audio in real-time:

### Audio Spectrum Data
- Frequency bands mapped to visual elements
- Higher frequencies = brighter colors
- Lower frequencies = larger movements

### Audio Reactivity Features

**Crystal Grid:**
- Crystals pulse and scale with frequency bands
- Glow intensity increases with amplitude
- Energy field expands during audio
- Individual crystal rotation speeds vary

**Sacred Mandala:**
- Patterns scale with average amplitude
- Element opacity pulses with spectrum
- Rotation speed increases during playback
- Color shifts based on frequency content

**Flower of Life:**
- Circles pulse with their frequency band
- Rotation speed audio-reactive
- Color hue shifts with audio
- Vertical movement based on amplitude

## Selecting Visualizations

### In the Frontend

Users can switch between visualizations using the dropdown menu:

1. Click "Visualization" button in header
2. Select from:
   - Flower of Life
   - Crystal Grid
   - Sacred Mandala
   - Audio Spectrum
   - Planetary System (coming soon)

### Programmatic Selection

```javascript
const [visualizationType, setVisualizationType] = useState('crystal-grid');

// Switch visualization
setVisualizationType('sacred-mandala');
```

## Performance Optimization

### Rendering Performance

**Good Performance** (60 FPS):
- Flower of Life: ~19 meshes
- Crystal Grid (hexagon): ~6 crystals
- Seed of Life: ~14 elements

**Medium Performance** (30-60 FPS):
- Crystal Grid (double-hexagon): ~13 crystals
- Sri Yantra: ~30+ elements
- Metatron's Cube: ~100+ lines

**Consider Simplification**:
- Star Grid: ~13 large crystals
- Complex mandalas on slower devices

### Optimization Tips

1. **Reduce particle count** in Stars component
2. **Lower shadow quality** in Environment preset
3. **Disable auto-rotate** for static viewing
4. **Use simpler patterns** on mobile devices
5. **Adjust camera distance** for better framing

## Camera Controls

All visualizations support interactive camera controls:

```javascript
<OrbitControls
  enableZoom={true}      // Mouse wheel zoom
  enablePan={true}       // Right-click pan
  enableRotate={true}    // Left-click rotate
  autoRotate={true}      // Automatic rotation
  autoRotateSpeed={0.5}  // Rotation speed
/>
```

### Recommended Camera Positions

```javascript
// Crystal Grid - View from above/front
camera={{ position: [0, -8, 12], fov: 60 }}

// Sacred Mandala - Direct front view
camera={{ position: [0, 0, 15], fov: 60 }}

// Flower of Life - Distant view
camera={{ position: [0, 0, 20], fov: 60 }}
```

## Use Cases

### For Meditation

**Seed of Life**: Beginners, calming, simple
**Flower of Life**: Intermediate, traditional
**Sri Yantra**: Advanced, deep meditation
**Tree of Life**: Contemplative, study

### For Radionics Operations

**Crystal Grid**: Direct representation of physical setup
- Use matching gridType to physical grid
- Set intention text to match operation
- Choose crystal type for specific work

### For Chakra Work

**Sacred Mandala with Chakra Colors**:
- Set `chakra` to target chakra
- Use Sri Yantra for powerful work
- Combine with matching frequencies

### For Teaching/Study

**Metatron's Cube**: Understanding sacred geometry
**Tree of Life**: Kabbalistic studies
**Flower of Life**: Universal patterns

## Creating Custom Visualizations

### Template Structure

```jsx
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const CustomVisualization = ({ audioSpectrum, isPlaying, frequency }) => {
  const groupRef = useRef();

  // Create geometry
  const geometry = useMemo(() => {
    // Your geometry creation here
    return elements;
  }, [/* dependencies */]);

  // Animation loop
  useFrame((state, delta) => {
    if (!groupRef.current) return;

    // Audio reactivity
    if (isPlaying && audioSpectrum.length > 0) {
      const avgAmplitude = audioSpectrum.slice(0, 10).reduce((a, b) => a + b, 0) / 10;
      groupRef.current.scale.setScalar(1 + avgAmplitude * 0.2);
    }

    // Rotation
    groupRef.current.rotation.z += delta * 0.1;
  });

  return (
    <group ref={groupRef}>
      {/* Your meshes here */}
    </group>
  );
};

export default CustomVisualization;
```

## Technical Details

### Dependencies

```json
{
  "@react-three/fiber": "^8.15.0",  // React Three.js renderer
  "@react-three/drei": "^9.88.0",    // Three.js helpers
  "three": "^0.157.0"                // Three.js core
}
```

### Material Properties

**Crystal Materials** (MeshPhysicalMaterial):
```javascript
{
  color: baseColor,
  emissive: emissiveColor,
  emissiveIntensity: 0.3,
  transparent: true,
  opacity: 0.7,
  metalness: 0.1,
  roughness: 0.2,
  clearcoat: 1.0,
  transmission: 0.5,  // Light transmission through crystal
  thickness: 0.5
}
```

**Sacred Geometry** (MeshBasicMaterial):
```javascript
{
  color: patternColor,
  transparent: true,
  opacity: 0.3,
  side: THREE.DoubleSide
}
```

## Future Enhancements

### Planned Features

- [ ] Planetary positions visualization (astrological timing)
- [ ] Chakra system 3D model
- [ ] Merkaba (3D Star Tetrahedron)
- [ ] Fibonacci spiral visualization
- [ ] Torus field (energy anatomy)
- [ ] Custom grid designer (drag-and-drop crystals)
- [ ] AR support (view grids in physical space)
- [ ] VR support (immersive meditation)
- [ ] Recording/screenshots
- [ ] Preset saving/loading
- [ ] Multi-user synchronized viewing

### Integration Ideas

- Link mandala pattern to astrological timing
- Auto-select chakra based on frequency
- Sync crystal grid with physical IoT sensors
- Real-time collaboration (multiple users, same grid)
- Biofeedback integration (change based on meditation state)

## Best Practices

### For Radionics Operations

1. **Match physical setup**: Use same grid pattern as physical crystals
2. **Set clear intention**: Display intention text in visualization
3. **Choose appropriate crystal**: Match crystal type to operation goal
4. **Enable energy field**: Visualize broadcast range

### For Meditation

1. **Start simple**: Begin with Seed of Life or Flower of Life
2. **Progress gradually**: Move to Sri Yantra as practice deepens
3. **Use chakra colors**: Align with energy work
4. **Minimize distractions**: Disable auto-rotate for deep focus

### For Groups

1. **Use largest patterns**: Better visibility at distance
2. **High contrast colors**: Easier to see
3. **Enable energy field**: Shows connection
4. **Slower animations**: Less distracting

## Philosophy

These visualizations embody **sacred geometry principles**:

- **As above, so below**: Digital mirrors physical
- **Microcosm and macrocosm**: Patterns at all scales
- **Form is emptiness**: Beautiful yet non-inherent
- **Upaya**: Technology as skillful means
- **Connection**: Visible representation of invisible forces

The patterns are maps, not destinations. They point to truths beyond themselves.

## Quick Reference

```javascript
// Crystal Grid - Double Hexagon with Amethyst
<CrystalGrid
  gridType="double-hexagon"
  crystalType="amethyst"
  showEnergyField={true}
  intention="Healing for all"
/>

// Sri Yantra - Heart Chakra
<SacredMandala
  pattern="sri-yantra"
  chakra="heart"
/>

// Metatron's Cube - Third Eye
<SacredMandala
  pattern="metatron"
  chakra="third-eye"
/>

// Seed of Life - Root Chakra
<SacredMandala
  pattern="seed-of-life"
  chakra="root"
/>
```

---

**May these sacred patterns guide all beings to awakening.**
**Gate gate pāragate pārasaṃgate bodhi svāhā** 🔮✨
