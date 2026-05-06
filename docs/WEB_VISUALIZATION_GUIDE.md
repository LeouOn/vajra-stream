# Vajra Stream Web Visualization Guide

## Overview

The Vajra Stream now includes a beautiful web-based visualization interface accessible through your browser. This provides an elegant way to view all sacred visualizations without needing to open image files manually.

## Quick Start

### 1. Start the API Server

```bash
# Option 1: Using the main application
python vajra_stream_v2.py --serve

# Option 2: Direct server start
python backend/app/main.py

# Option 3: Using uvicorn directly
cd backend/app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access the Visualization Gallery

Open your browser and navigate to:

```
http://localhost:8000/visualizations
```

Or use the alternative route:

```
http://localhost:8000/gallery
```

## Available Visualizations

### 1. Chakra System
- **Endpoint**: `/api/v1/visualization/chakras`
- **Description**: Visualize all seven primary chakras with their colors, Sanskrit names, and energetic properties
- **Parameters**:
  - `width` (default: 1200)
  - `height` (default: 1600)

### 2. Meridian System
- **Endpoint**: `/api/v1/visualization/meridians`
- **Description**: Traditional Chinese Medicine meridian pathways showing Qi energy flow
- **Parameters**:
  - `width` (default: 1200)
  - `height` (default: 1600)

### 3. Rothko Abstract Art
- **Endpoint**: `/api/v1/visualization/rothko`
- **Description**: Generate healing abstract art using sacred color harmonies
- **Parameters**:
  - `width` (default: 1920)
  - `height` (default: 1080)
  - `colors` (optional list of hex colors)

### 4. Sacred Geometry

#### Flower of Life
- **Endpoint**: `/api/v1/visualization/sacred-geometry/flower_of_life`
- **Description**: Ancient symbol containing patterns of creation

#### Metatron's Cube
- **Endpoint**: `/api/v1/visualization/sacred-geometry/metatrons_cube`
- **Description**: Contains all five Platonic Solids

#### Sri Yantra
- **Endpoint**: `/api/v1/visualization/sacred-geometry/sri_yantra`
- **Description**: Supreme yantra for meditation and manifestation

#### Other Available Geometries
- `seed_of_life`
- `vesica_piscis`
- `torus`
- `golden_spiral`

### 5. Healing Mandala
- **Endpoint**: `/api/v1/visualization/mandala`
- **Description**: Create sacred mandala with healing intention
- **Parameters**:
  - `size` (default: 1000)
  - `intention` (default: "healing")

### 6. Energy Field (Aura)
- **Endpoint**: `/api/v1/visualization/energy-field`
- **Description**: Visualize human energy field and auric layers
- **Parameters**:
  - `width` (default: 800)
  - `height` (default: 800)
  - `field_type` (default: "aura")

## Usage Examples

### Python API

```python
from vajra_stream_v2 import VajraStream

vs = VajraStream()

# Generate chakra visualization
chakra_path = vs.visualize_chakras(width=1200, height=1600)
print(f"Chakra diagram saved to: {chakra_path}")

# Generate Rothko art
rothko_path = vs.generate_rothko_art(width=1920, height=1080)
print(f"Rothko art saved to: {rothko_path}")
```

### Direct API Calls

```bash
# Get chakra visualization
curl http://localhost:8000/api/v1/visualization/chakras -o chakras.png

# Get Rothko art
curl http://localhost:8000/api/v1/visualization/rothko -o rothko.png

# Get sacred geometry
curl http://localhost:8000/api/v1/visualization/sacred-geometry/flower_of_life -o flower.png

# Get healing mandala
curl "http://localhost:8000/api/v1/visualization/mandala?intention=peace" -o mandala.png
```

### JavaScript/Fetch

```javascript
// Load chakra visualization in browser
fetch('http://localhost:8000/api/v1/visualization/chakras')
  .then(response => response.blob())
  .then(blob => {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(blob);
    document.body.appendChild(img);
  });
```

## Features

### Interactive Gallery
- **Click to generate**: Each visualization card generates the image on demand
- **Click to expand**: Click any generated image to view it in full-screen modal
- **Beautiful UI**: Modern, responsive design with sacred aesthetics
- **Loading indicators**: Visual feedback while images are being generated

### Browser Compatibility
- Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design adapts to different screen sizes
- No additional plugins required

### Error Handling
- Graceful degradation if dependencies are missing
- Helpful error messages with installation instructions
- Clear feedback when visualizations fail to generate

## API Documentation

For complete API documentation, visit:

```
http://localhost:8000/docs
```

This provides interactive Swagger UI documentation for all endpoints.

## Dependencies

### Required for Visualization
```bash
pip install pillow numpy
```

### Full Install
```bash
pip install -r requirements.txt
```

### Minimal Install
```bash
pip install -r requirements-minimal.txt
```

## Troubleshooting

### "Rothko generator not available" error
```bash
# Install PIL/Pillow
pip install pillow
```

### "PIL/Pillow required for visualization" error
```bash
# Install image processing library
pip install pillow>=10.0.0
```

### Template not found
Make sure the `templates/` directory exists in the project root with `visualization.html`

### Port already in use
```bash
# Use a different port
uvicorn backend.app.main:app --port 8001
```

## Integration with Frontend

The API is CORS-enabled and can be integrated with any frontend framework:

```javascript
// React/Vue/Svelte example
const API_BASE = 'http://localhost:8000/api/v1';

async function loadChakras() {
  const response = await fetch(`${API_BASE}/visualization/chakras`);
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
```

## Terminal Visualization

For terminal-based visualization (ASCII art, color output), use the CLI:

```bash
# Interactive menu
python vajra_stream_v2.py --interactive

# Then select visualization options from the menu
```

## Architecture

```
vajra-stream/
├── backend/
│   └── app/
│       ├── main.py (FastAPI server + routes)
│       └── api/v1/endpoints/
│           └── visualization.py (Visualization endpoints)
├── templates/
│   └── visualization.html (Web gallery UI)
├── modules/
│   ├── visualization.py (Visualization service)
│   └── anatomy.py (Anatomy service)
└── vajra_stream_v2.py (Main application)
```

## Next Steps

1. **Customize visualizations**: Modify parameters in the gallery UI
2. **Create animations**: Use the API to generate sequences of images
3. **Build custom frontends**: Use the REST API with your preferred framework
4. **Export for print**: Generate high-resolution images for physical printing

## Sacred Frequencies

The visualization system integrates with the healing frequency system:

- **528 Hz** - DNA Repair, Love (Love Frequency)
- **432 Hz** - Natural Tuning (Universal Frequency)
- **963 Hz** - Divine Consciousness (Pineal Gland Activation)

These frequencies inform the color harmonies and energetic properties of the visualizations.

---

**May all beings benefit from these sacred visualizations!** 🕉️

For more information, see:
- [FEATURE_PARITY_GUIDE.md](FEATURE_PARITY_GUIDE.md) - Complete feature documentation
- [README.md](README.md) - Main project documentation
