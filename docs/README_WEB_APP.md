# Vajra.Stream Web Application

## 🌸 Overview

Vajra.Stream Web Application is a modern, browser-based interface for sacred technology practices, featuring advanced prayer bowl audio synthesis, real-time 3D visualizations, and comprehensive session management.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Existing Vajra.Stream modules

### Installation

1. **Backend Setup**
```bash
cd backend
pip install -r requirements.txt
```

2. **Frontend Setup**
```bash
cd frontend
npm install
```

3. **Start Services**
```bash
# Terminal 1 - Start Backend
cd backend
python app/main.py

# Terminal 2 - Start Frontend
cd frontend
npm run dev
```

4. **Access Application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

## 🏗️ Architecture

### Backend (FastAPI)
- **Service Layer**: Wraps existing Vajra.Stream modules
- **API Layer**: RESTful endpoints for all functionality
- **WebSocket**: Real-time data streaming at 10Hz
- **Integration**: Seamless connection to existing audio generators, crystal broadcasters, and astrology modules

### Frontend (React + Vite)
- **3D Visualizations**: React Three Fiber with sacred geometry
- **Real-time UI**: WebSocket-connected components
- **State Management**: Zustand for predictable state
- **Styling**: Tailwind CSS with custom Vajra theme

### Key Features
- 🎵 **Prayer Bowl Synthesis**: Enhanced harmonic generation
- 🌐 **Sacred Geometry**: 3D Flower of Life visualization
- 📊 **Audio Spectrum**: Real-time frequency analysis
- 🌙 **Astrology Integration**: Planetary positions and timing
- 🧘 **Session Management**: Create and track blessing sessions
- 🔮 **Hardware Control**: Crystal broadcaster integration

## 📱 User Interface

### Main Components

#### Control Panel
- Frequency control (1-1000 Hz)
- Volume and duration settings
- Prayer bowl mode toggle
- Advanced parameters (harmonics, modulation)
- Preset configurations (OM, Heart Chakra, Earth Resonance)

#### Visualizations
- **Sacred Geometry**: Interactive 3D Flower of Life
- **Audio Spectrum**: Real-time frequency bars
- **Planetary System**: Astrological visualization (in development)
- **Coming Soon**: Chakra system, prayer wheel, Rothko generator

#### Session Manager
- Create custom blessing sessions
- Set intentions and durations
- Monitor active sessions
- Session history and statistics

### Real-time Features
- **WebSocket Connection**: Live data streaming
- **Audio Reactivity**: Visuals respond to frequency
- **Status Indicators**: Connection and playback status
- **Live Updates**: Session progress and spectrum

## 🔧 API Documentation

### Audio Endpoints
- `POST /api/v1/audio/generate` - Generate prayer bowl audio
- `POST /api/v1/audio/play` - Play audio through hardware
- `GET /api/v1/audio/spectrum` - Get current spectrum
- `GET /api/v1/audio/presets` - Get audio presets

### Session Endpoints
- `POST /api/v1/sessions/create` - Create new session
- `POST /api/v1/sessions/{id}/start` - Start session
- `POST /api/v1/sessions/{id}/stop` - Stop session
- `GET /api/v1/sessions/` - List active sessions

### Astrology Endpoints
- `GET /api/v1/astrology/current` - Current astrological data
- `GET /api/v1/astrology/moon-phase` - Moon phase
- `GET /api/v1/astrology/planetary-positions` - Planetary positions

### WebSocket Events
- `realtime_data` - Audio spectrum and session updates
- `connection_status` - Connection status changes
- `session_update` - Individual session updates
- `heartbeat` - Keep-alive messages

## 🎨 Visualizations

### Sacred Geometry
- **Flower of Life**: 19 interactive circles
- **Audio Reactivity**: Scale and color based on frequency
- **Smooth Animation**: 60fps rotation and pulsing
- **Interactive Controls**: Zoom, rotate, auto-rotate

### Audio Spectrum
- **Real-time FFT**: 100 frequency bins
- **Color Gradient**: Cyan to purple spectrum
- **Frequency Indicator**: Line showing current frequency
- **Smooth Updates**: 10Hz refresh rate

## 🧪 Testing

### Integration Tests
Run comprehensive integration tests:
```bash
python test_integration.py
```

### Test Coverage
- ✅ Backend health checks
- ✅ API endpoint validation
- ✅ WebSocket connectivity
- ✅ Audio generation and playback
- ✅ Session management
- ✅ Real-time data streaming

## 🔌 Configuration

### Audio Presets
- **OM Frequency**: 136.1 Hz - Spiritual foundation
- **Heart Chakra**: 528 Hz - Love and healing
- **Earth Resonance**: 7.83 Hz - Grounding
- **Pure Sine**: 440 Hz - Standard tuning

### Advanced Parameters
- **Harmonic Strength**: 0-100% - Overtone intensity
- **Modulation Depth**: 0-20% - Frequency variation
- **Envelope Type**: prayer_bowl, sine, custom
- **Hardware Level**: 2 or 3 - Crystal broadcaster selection

## 🌐 Deployment

### Development
```bash
# Backend
cd backend
python app/main.py

# Frontend
cd frontend
npm run dev
```

### Production
```bash
# Build frontend
cd frontend
npm run build

# Start backend (production mode)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker (Optional)
```dockerfile
# Backend Dockerfile example
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔗 Integration with Existing Vajra.Stream

### Module Compatibility
- ✅ `core.audio_generator` - Enhanced synthesis
- ✅ `hardware.crystal_broadcaster` - Hardware control
- ✅ `core.astrology` - Astrological calculations
- ✅ `core.prayer_wheel` - Prayer wheel system
- ✅ `core.llm_integration` - Content generation
- ✅ `core.tts_engine` - Text-to-speech
- ✅ `core.visual_renderer` - Visual generation

### Fallback Mode
If enhanced modules are unavailable, the system automatically falls back to:
- Basic sine wave generation
- Simulated hardware control
- Mock astrological data
- Simplified visualizations

## 🎯 Performance

### Optimizations
- **WebSocket Throttling**: 10Hz update rate
- **3D Rendering**: Efficient geometry reuse
- **State Management**: Minimal re-renders
- **API Caching**: Response caching where appropriate

### Benchmarks
- **API Response**: < 100ms
- **WebSocket Latency**: < 50ms
- **3D Frame Rate**: 60fps target
- **Audio Latency**: < 10ms processing

## 🐛 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Check module imports
python -c "from core.audio_generator import EnhancedAudioGenerator"
```

#### Frontend Won't Build
```bash
# Clear node_modules
rm -rf frontend/node_modules
npm install

# Check Node.js version
node --version

# Clear cache
npm cache clean --force
```

#### WebSocket Connection Fails
- Check backend is running on port 8000
- Verify CORS settings
- Check firewall settings
- Ensure WebSocket endpoint is accessible

#### Audio Not Playing
- Verify audio generation completed
- Check hardware level (2 or 3)
- Check crystal broadcaster connection
- Review backend logs for errors

### Debug Mode
Enable debug logging:
```bash
# Backend
cd backend
python app/main.py --log-level debug

# Frontend
cd frontend
npm run dev --debug
```

## 📚 Documentation

### API Documentation
- Interactive: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI: http://localhost:8000/openapi.json

### Component Documentation
- Frontend components: `frontend/src/components/`
- API endpoints: `backend/app/api/v1/endpoints/`
- Service layer: `backend/core/services/`

## 🤝 Contributing

### Development Workflow
1. Fork repository
2. Create feature branch
3. Make changes
4. Run integration tests
5. Submit pull request

### Code Style
- **Python**: PEP 8 compliance
- **JavaScript**: ESLint configuration
- **React**: Hooks and functional components
- **CSS**: Tailwind utility classes

## 📄 License

This web application extends the existing Vajra.Stream sacred technology platform while maintaining compatibility with all core modules and preserving the spiritual and technical integrity of the original system.

## 🌟 Acknowledgments

Built with gratitude for the ancient wisdom of sacred sound technology and the modern power of web-based interfaces for spiritual practice.