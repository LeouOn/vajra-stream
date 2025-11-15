"""
FastAPI Application for Vajra.Stream Web Interface
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import asyncio
import sys
import os

# Add parent directory to path to import existing Vajra.Stream modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from app.api.v1.endpoints import audio as audio_endpoint, sessions as sessions_endpoint, astrology as astrology_endpoint
from websocket.connection_manager import ConnectionManager
from core.services.vajra_service import vajra_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Vajra.Stream API starting up...")
    print("Initializing WebSocket connection manager...")
    
    # Start background task for real-time streaming
    asyncio.create_task(connection_manager.start_realtime_streaming())
    
    yield
    
    # Shutdown
    print("Vajra.Stream API shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="Vajra.Stream API",
    description="Sacred Technology Web Interface",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
connection_manager = ConnectionManager()

# API Routes
@app.get("/")
async def root():
    return {
        "message": "Vajra.Stream API", 
        "status": "active",
        "version": "1.0.0",
        "description": "Sacred Technology Web Interface"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "vajra-stream",
        "timestamp": asyncio.get_event_loop().time()
    }

# Include routers
app.include_router(audio_endpoint.router, prefix="/api/v1/audio", tags=["audio"])
app.include_router(sessions_endpoint.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(astrology_endpoint.router, prefix="/api/v1/astrology", tags=["astrology"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connection_manager.disconnect(websocket)

# Static file serving for frontend (optional)
@app.get("/frontend", response_class=HTMLResponse)
async def get_frontend():
    """
    Serve the frontend application (optional - for development)
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Vajra.Stream API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: white; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 5px; }
            .method { color: #4CAF50; font-weight: bold; }
            .path { color: #2196F3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Vajra.Stream API</h1>
            <p>Sacred Technology Web Interface</p>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/</span> - API Root
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/health</span> - Health Check
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/docs</span> - API Documentation
            </div>
            <div class="endpoint">
                <span class="method">WS</span> <span class="path">/ws</span> - WebSocket Connection
            </div>
            
            <h2>📚 API Documentation</h2>
            <p>Visit <a href="/docs" style="color: #2196F3;">/docs</a> for interactive API documentation.</p>
            <p>Visit <a href="/redoc" style="color: #2196F3;">/redoc</a> for ReDoc documentation.</p>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    print("Starting Vajra.Stream API Server...")
    print("WebSocket endpoint: ws://localhost:8000/ws")
    print("API Documentation: http://localhost:8000/docs")
    print("Frontend should be available at: http://localhost:3000")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info"
    )