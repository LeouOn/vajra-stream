"""
Simple Vajra.Stream Backend Server
Minimal working version for testing
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from datetime import datetime

app = FastAPI(
    title="Vajra.Stream API",
    description="Sacred Technology Platform Backend",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for demo
active_sessions = {}
audio_status = {
    "is_playing": False,
    "active_frequencies": [],
    "spectrum": []
}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Vajra.Stream API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    print("WebSocket connected")
    
    try:
        while True:
            # Simulate real-time audio data
            await asyncio.sleep(0.1)  # 10 Hz update rate
            
            # Send audio spectrum data
            await websocket.send_text(json.dumps({
                "type": "audio_spectrum",
                "data": {
                    "frequencies": [7.83, 136.1, 528, 639, 741],
                    "amplitudes": [0.8, 0.6, 0.4, 0.7, 0.5],
                    "timestamp": datetime.now().isoformat()
                }
            }))
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket disconnected")

@app.post("/api/v1/audio/generate")
async def generate_audio(request: dict):
    """Generate audio based on configuration"""
    try:
        audio_type = request.get("type", "prayer_bowl")
        frequency = request.get("frequency", 432)
        duration = request.get("duration", 300)
        
        # Update audio status
        audio_status["is_playing"] = True
        audio_status["active_frequencies"] = [frequency]
        
        return {
            "status": "success",
            "audio_data": [0.1, 0.2, 0.3] * duration * 44100,  # Simulated audio data
            "sample_rate": 44100,
            "duration": duration,
            "frequency": frequency
        }
    except Exception as e:
        return {"error": f"Audio generation failed: {str(e)}"}

@app.post("/api/v1/audio/play")
async def play_audio(request: dict):
    """Play audio"""
    try:
        audio_status["is_playing"] = True
        return {"status": "playing", "message": "Audio playback started"}
    except Exception as e:
        return {"error": f"Audio playback failed: {str(e)}"}

@app.post("/api/v1/audio/stop")
async def stop_audio():
    """Stop audio playback"""
    try:
        audio_status["is_playing"] = False
        audio_status["active_frequencies"] = []
        return {"status": "stopped", "message": "Audio playback stopped"}
    except Exception as e:
        return {"error": f"Audio stop failed: {str(e)}"}

@app.get("/api/v1/audio/status")
async def get_audio_status():
    """Get current audio status"""
    return {
        "is_playing": audio_status["is_playing"],
        "active_frequencies": audio_status["active_frequencies"],
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/audio/spectrum")
async def get_frequency_spectrum():
    """Get current frequency spectrum"""
    return {
        "frequencies": audio_status["active_frequencies"],
        "amplitudes": audio_status["spectrum"]
    }

@app.get("/api/v1/audio/frequencies")
async def get_active_frequencies():
    """Get currently active frequencies"""
    return {"frequencies": audio_status["active_frequencies"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "simple_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )