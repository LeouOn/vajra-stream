# Vajra Stream - Quick Start Guide

## Installation

### Minimal Install (Core Features Only)
```bash
pip install -r requirements-minimal.txt
```

This installs only the essential dependencies:
- FastAPI (web server)
- Pillow (image processing)
- NumPy (numerical computing)
- Pydantic (data validation)
- Rich (terminal output)

### Full Install (All Features)
```bash
pip install -r requirements.txt
```

**Note:** If you're on Python 3.14+, some optional packages (like librosa) may not install. The system will work fine without them - they're optional enhancements.

## Starting the Web Server

### Method 1: Simple Launcher (Recommended for Windows)

**Windows:**
```cmd
start_web_server.bat
```

**Linux/Mac:**
```bash
python start_web_server.py
```

### Method 2: Using vajra_stream_v2.py
```bash
python vajra_stream_v2.py --serve
```

### Method 3: Direct uvicorn
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## Accessing the Web Interface

Once the server is running, open your browser to:

### 🎨 Visualization Gallery (Main Interface)
```
http://localhost:8000/visualizations
```

This beautiful web interface lets you generate and view:
- Chakra System diagrams
- Meridian maps
- Rothko abstract art
- Sacred geometry (Flower of Life, Metatron's Cube, etc.)
- Healing mandalas
- Energy field visualizations

### 📚 API Documentation
```
http://localhost:8000/docs
```

Interactive Swagger UI for all API endpoints.

### 🔍 Alternative Documentation
```
http://localhost:8000/redoc
```

ReDoc-style documentation.

## Using the System

### Web Interface
1. Start the server (see above)
2. Open http://localhost:8000/visualizations
3. Click any visualization card to generate the image
4. Click the generated image to view full-screen

### Terminal Interface
```bash
python vajra_stream_v2.py --interactive
```

Then choose from the menu options.

### Python API
```python
from vajra_stream_v2 import VajraStream

vs = VajraStream()

# Generate scalar waves
result = vs.generate_scalar_waves('hybrid', duration_seconds=10)

# Broadcast healing
session = vs.broadcast_healing("John Doe", duration_minutes=10)

# Visualize chakras
chakra_path = vs.visualize_chakras()
print(f"Chakra diagram saved to: {chakra_path}")
```

## Troubleshooting

### "Module not found" errors
Make sure you're running from the project root directory:
```bash
cd /path/to/vajra-stream
python start_web_server.py
```

### "PIL/Pillow not installed" errors
```bash
pip install pillow
```

### Visualization not loading in browser
1. Check that the server is running (you should see "Application startup complete" in the console)
2. Make sure PIL/Pillow is installed: `pip install pillow`
3. Try clearing your browser cache
4. Check the server console for error messages

### Port already in use
If port 8000 is already in use, edit `start_web_server.py` and change:
```python
port=8000,  # Change to 8001 or any other available port
```

## What's Working

✅ **Web Visualization Gallery** - Beautiful browser interface
✅ **REST API** - All endpoints documented and working
✅ **Terminal Interface** - Interactive menu system
✅ **Python API** - Full programmatic access
✅ **Graceful Error Handling** - Helpful messages when dependencies are missing

## What Requires Optional Dependencies

❌ **Audio Generation** - Requires: `numpy scipy sounddevice`
❌ **TTS (Text-to-Speech)** - Requires: `pyttsx3`
❌ **Astrology** - Requires: `astropy astroquery`
❌ **Advanced Composition** - Requires: `numpy scipy`

All of these will show helpful error messages with installation instructions if you try to use them without the dependencies.

## Next Steps

1. **Explore the visualization gallery** at http://localhost:8000/visualizations
2. **Try the interactive menu**: `python vajra_stream_v2.py --interactive`
3. **Read the full documentation**:
   - [WEB_VISUALIZATION_GUIDE.md](WEB_VISUALIZATION_GUIDE.md) - Web interface details
   - [FEATURE_PARITY_GUIDE.md](FEATURE_PARITY_GUIDE.md) - All features documented
   - [README.md](README.md) - Main project documentation

## Support

If you encounter any issues:
1. Check that you're using Python 3.10 - 3.13 (some packages don't support 3.14 yet)
2. Make sure you've installed at least the minimal requirements
3. Check the error message - it will usually tell you what's missing
4. Look for error messages in the server console

---

**May all beings benefit from this sacred technology!** 🕉️
