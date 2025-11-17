"""
FastAPI Application for Vajra.Stream Web Interface
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path to import existing Vajra.Stream modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))

from backend.app.api.v1.endpoints import (
    audio as audio_endpoint,
    sessions as sessions_endpoint,
    astrology as astrology_endpoint,
    scalar_waves as scalar_endpoint,
    radionics as radionics_endpoint,
    anatomy as anatomy_endpoint,
    blessings as blessings_endpoint,
    visualization as visualization_endpoint,
    rng_attunement as rng_endpoint,
    blessing_slideshow as slideshow_endpoint
)
from backend.websocket.connection_manager import ConnectionManager
from backend.core.services.vajra_service import vajra_service

# Setup templates
template_dir = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

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
    allow_origins=["http://localhost:3009", "http://127.0.0.1:3009", "http://localhost:3001", "http://127.0.0.1:3001"],
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

# Terra MOPS and Healing System routers
app.include_router(scalar_endpoint.router, prefix="/api/v1/scalar", tags=["scalar-waves"])
app.include_router(radionics_endpoint.router, prefix="/api/v1/radionics", tags=["radionics"])
app.include_router(anatomy_endpoint.router, prefix="/api/v1/anatomy", tags=["anatomy"])
app.include_router(blessings_endpoint.router, prefix="/api/v1/blessings", tags=["blessings"])
app.include_router(visualization_endpoint.router, prefix="/api/v1/visualization", tags=["visualization"])
app.include_router(rng_endpoint.router, prefix="/api/v1", tags=["rng-attunement"])
app.include_router(slideshow_endpoint.router, prefix="/api/v1", tags=["blessing-slideshow"])

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


# Visualization Gallery
@app.get("/visualizations", response_class=HTMLResponse)
@app.get("/gallery", response_class=HTMLResponse)
async def visualization_gallery():
    """
    Sacred Visualization Gallery - Beautiful web interface for all visualizations
    """
    template_path = template_dir / "visualization.html"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(
            content="<h1>Visualization template not found</h1>",
            status_code=404
        )


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
            a { color: #FFD700; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔱 Vajra.Stream API</h1>
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
                <span class="method">GET</span> <span class="path"><a href="/visualizations">/visualizations</a></span> - 🎨 Sacred Visualization Gallery
            </div>
            <div class="endpoint">
                <span class="method">WS</span> <span class="path">/ws</span> - WebSocket Connection
            </div>

            <h2>📚 Resources</h2>
            <p>Visit <a href="/docs" style="color: #2196F3;">/docs</a> for interactive API documentation.</p>
            <p>Visit <a href="/redoc" style="color: #2196F3;">/redoc</a> for ReDoc documentation.</p>
            <p>Visit <a href="/visualizations" style="color: #FFD700;">🎨 Visualization Gallery</a> for sacred art and healing visualizations.</p>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    print("Starting Vajra.Stream API Server...")
    print("WebSocket endpoint: ws://localhost:8001/ws")
    print("API Documentation: http://localhost:8001/docs")
    print("Visualization Gallery: http://localhost:8001/visualizations")
    print("React/Vite frontend (if used): http://localhost:3009")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )