"""
FastAPI Application for Vajra.Stream Web Interface - Stable WebSocket Version
"""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables early so os.getenv works for the FastAPI
# middleware/router configuration performed by the imports below.
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402

# Import stable connection manager v2
from backend.websocket.connection_manager import stable_connection_manager_v2  # noqa: E402

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.app.api.v1.api import api_router  # noqa: E402

# Setup templates
template_dir = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Vajra.Stream API starting up...")
    print("Initializing Stable WebSocket connection manager v2...")

    try:
        from core.schema import init_db as _schema_init_db

        _schema_init_db().close()
        print("Database schema initialized (core.schema.init_db)")
    except Exception as e:
        print(f"Failed to initialize database schema: {e}")
        logger.error(f"Failed to initialize database schema: {e}")
        logger.error(traceback.format_exc())

    # Initialize Orchestrator Bridge
    try:
        from backend.core.orchestrator_bridge import orchestrator_bridge

        print("Initializing Orchestrator Bridge...")
        orchestrator_bridge.initialize()
        print("Orchestrator Bridge initialized successfully")
    except Exception as e:
        print(f"Failed to initialize Orchestrator Bridge: {e}")
        logger.error(f"Failed to initialize Orchestrator Bridge: {e}")
        logger.error(traceback.format_exc())

    # Initialize LLM Provider Registry
    health_task = None
    try:
        from core.llm.bootstrap import build_default_registry

        registry = build_default_registry()
        app.state.llm_registry = registry
        print(f"LLM registry initialized: {[p.name for p in registry.providers]}")
    except Exception as e:
        print(f"Failed to initialize LLM registry: {e}")
        logger.error(f"Failed to initialize LLM registry: {e}")
        logger.error(traceback.format_exc())

    # Start LLM health heartbeat
    if hasattr(app.state, "llm_registry") and len(app.state.llm_registry) > 0:
        try:
            from backend.app.config import get_llm_config
            from core.llm.health import start_health_heartbeat

            config = get_llm_config()

            async def publish_health(statuses):
                try:
                    await stable_connection_manager_v2.broadcast(
                        {
                            "type": "PROVIDER_HEALTH",
                            "statuses": [s.model_dump() for s in statuses],
                        }
                    )
                except Exception as e:
                    logger.debug(f"PROVIDER_HEALTH broadcast failed: {e}")

            health_task = asyncio.create_task(
                start_health_heartbeat(
                    app.state.llm_registry,
                    interval_seconds=config.health_check_interval_seconds,
                    on_update=publish_health,
                )
            )
            print(
                f"LLM health heartbeat started "
                f"(interval={config.health_check_interval_seconds}s)"
            )
        except Exception as e:
            print(f"Failed to start health heartbeat: {e}")
            logger.error(f"Failed to start health heartbeat: {e}")
            logger.error(traceback.format_exc())

    # Start real-time streaming with stable manager v2
    streaming_task = None
    try:
        streaming_task = asyncio.create_task(stable_connection_manager_v2.start_realtime_streaming())
        print("Stable real-time streaming started")
    except Exception as e:
        print(f"Failed to start streaming: {e}")
        logger.error(f"Failed to start streaming: {e}")
        logger.error(traceback.format_exc())

    # Start Autonomous Operator Daemon
    try:
        from container import container

        print("Starting Autonomous Radionics Operator daemon...")
        container.operator.start_autonomous_mode(interval_seconds=300)
        print("Autonomous Radionics Operator daemon activated successfully on startup")
    except Exception as e:
        print(f"Failed to start Autonomous Operator daemon: {e}")
        logger.error(f"Failed to start Autonomous Operator daemon: {e}")

    # Wire LLM usage WS broadcast: every Nth record (throttled inside the
    # tracker), push a compact summary over the stable WS channel so the
    # frontend can render a live cost panel without polling.
    try:
        import asyncio as _asyncio

        from core.llm.usage import LLMUsageTracker

        def _broadcast_usage(summary: dict) -> None:
            payload = {
                "type": "LLM_USAGE_UPDATE",
                "data": {
                    "total_calls": summary.get("total_calls"),
                    "total_cost_usd": summary.get("total_cost_usd"),
                    "calls_today": summary.get("calls_today"),
                    "cost_today": summary.get("cost_today"),
                    "daily_cost_usd": summary.get("daily_cost_usd"),
                    "daily_cost_cap": summary.get("daily_cost_cap"),
                    "over_cap": summary.get("over_cap"),
                    "remaining_balance": summary.get("remaining_balance"),
                    "provider_stats": summary.get("provider_stats"),
                },
            }
            try:
                loop = _asyncio.get_running_loop()
                loop.create_task(stable_connection_manager_v2.broadcast(payload))
            except RuntimeError:
                # No running loop — tests/offline use; skip silently.
                pass
            except Exception:  # noqa: BLE001
                logger.debug("LLM_USAGE_UPDATE broadcast failed", exc_info=True)

        LLMUsageTracker.get().add_on_record_callback(_broadcast_usage)
        print("LLM usage WS broadcast hook registered (throttled every 10 records)")
    except Exception as e:
        print(f"Failed to register LLM usage WS broadcast: {e}")
        logger.error(f"Failed to register LLM usage WS broadcast: {e}")

    # Pre-warm the multi-practice recitation engine so the first
    # /practices/list request doesn't pay the JSON-load cost. Lazy load
    # is idempotent; this just forces it to happen now.
    try:
        from core.practice_engine import get_practice_engine

        engine = get_practice_engine()
        # Touch list_practices() to force definition loading eagerly.
        engine_count = len(engine.list_practices())
        print(f"Practice engine pre-warmed ({engine_count} definitions loaded)")
    except Exception as e:
        print(f"Failed to pre-warm practice engine: {e}")
        logger.error(f"Failed to pre-warm practice engine: {e}")
        logger.error(traceback.format_exc())

    yield

    # Shutdown
    print("Vajra.Stream API shutting down...")
    stable_connection_manager_v2.stop_realtime_streaming()

    # Shutdown Orchestrator Bridge (cancel the crystal broadcast daemon thread)
    try:
        from backend.core.orchestrator_bridge import orchestrator_bridge

        orchestrator_bridge.shutdown()
        print("Orchestrator Bridge shut down")
    except Exception as e:
        print(f"Failed to shut down Orchestrator Bridge: {e}")
        logger.error(f"Failed to shut down Orchestrator Bridge: {e}")

    # Stop Autonomous Operator Daemon
    try:
        from container import container

        print("Stopping Autonomous Radionics Operator daemon...")
        container.operator.stop_autonomous_mode()
        print("Autonomous Radionics Operator daemon stopped")
    except Exception as e:
        print(f"Failed to stop Autonomous Operator daemon: {e}")

    # Stop any running multi-practice sessions so their history is
    # recorded with reason="shutdown" rather than left dangling.
    try:
        from core.practice_engine import get_practice_engine

        await get_practice_engine().stop_all(reason="shutdown")
        print("Practice engine stopped all running sessions")
    except Exception as e:
        print(f"Failed to stop practice engine sessions: {e}")
        logger.error(f"Failed to stop practice engine sessions: {e}")

    # Close LLM registry and cancel health heartbeat
    if hasattr(app.state, "llm_registry"):
        try:
            await app.state.llm_registry.close_all()
            print("LLM registry closed")
        except Exception as e:
            print(f"Failed to close LLM registry: {e}")
            logger.error(f"Failed to close LLM registry: {e}")

    if health_task:
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass

    if streaming_task:
        streaming_task.cancel()
        try:
            await streaming_task
        except asyncio.CancelledError:
            pass


# Initialize FastAPI app
app = FastAPI(
    title="Vajra.Stream API",
    description="Sacred Technology Web Interface - Stable WebSocket Version v2",
    version="1.0.0-stable-v2",
    lifespan=lifespan,
)

# CORS middleware - FIXED to include localhost:5173 and port 3010
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3009",
        "http://127.0.0.1:3009",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes
@app.get("/")
async def root():
    return {
        "message": "Vajra.Stream API",
        "status": "active",
        "version": "1.0.0-stable-v2",
        "description": "Sacred Technology Web Interface - Stable WebSocket Version v2",
        "websocket_stats": stable_connection_manager_v2.get_connection_stats(),
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "vajra-stream",
        "version": "1.0.0-stable-v2",
        "timestamp": asyncio.get_event_loop().time(),
        "websocket_connections": stable_connection_manager_v2.get_connection_count(),
        "streaming_active": stable_connection_manager_v2.is_streaming(),
    }


@app.get("/ws-stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return stable_connection_manager_v2.get_connection_stats()


# Include central API router
app.include_router(api_router, prefix="/api/v1")


# Story search endpoint (used by commandStore)
@app.get("/api/v1/stories/search")
async def search_stories(q: str = ""):
    tales = [
        {
            "id": "burning_house",
            "title": "The Burning House",
            "source": "Lotus Sutra",
            "tradition": "Mahayana",
            "theme": "impermanence",
            "summary": "A father lures his children from a burning house with promises of toys.",
        },
        {
            "id": "the_arrow",
            "title": "The Arrow",
            "source": "Acintita Sutra",
            "tradition": "Theravada",
            "theme": "wisdom",
            "summary": "A man wounded by a poison arrow refuses treatment, demanding to know who shot it.",
        },
        {
            "id": "the_raft",
            "title": "The Raft",
            "source": "Majjhima Nikaya",
            "tradition": "Theravada",
            "theme": "letting_go",
            "summary": "A man crosses a river using a raft, then must decide whether to carry it further.",
        },
        {
            "id": "cup_of_tea",
            "title": "A Cup of Tea",
            "source": "Zen",
            "tradition": "Zen",
            "theme": "emptiness",
            "summary": "Nan-in serves tea, overfilling the cup to teach about emptying the mind.",
        },
    ]
    results = [t for t in tales if q.lower() in t["title"].lower() or q.lower() in t["theme"].lower()] if q else tales
    return {"results": results, "query": q}


# WebSocket endpoint - Stable implementation
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = None
    try:
        print("WebSocket connection attempt received")
        connection_id = await stable_connection_manager_v2.connect(websocket)
        print(f"WebSocket {connection_id} accepted successfully")

        # Message handling loop
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                print(f"Received WebSocket message from {connection_id}: {data[:100]}...")  # Truncate long messages

                # Handle message using stable manager v2
                await stable_connection_manager_v2.handle_message(connection_id, data)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await stable_connection_manager_v2.send_personal_message(
                    {"type": "ping", "timestamp": asyncio.get_event_loop().time()}, connection_id
                )
                print(f"Sent ping to {connection_id} to keep alive")

    except WebSocketDisconnect as e:
        print(f"WebSocket {connection_id} disconnected with code: {e.code}")
        logger.info(f"WebSocket {connection_id} disconnected cleanly: {e.code} {e.reason}")
    except Exception as e:
        print(f"WebSocket error for {connection_id}: {e}")
        logger.error(f"WebSocket error for {connection_id}: {e}")
        logger.error(traceback.format_exc())
    finally:
        if connection_id:
            stable_connection_manager_v2.disconnect(connection_id)


# Visualization Gallery
@app.get("/visualizations", response_class=HTMLResponse)
@app.get("/gallery", response_class=HTMLResponse)
async def visualization_gallery():
    """
    Sacred Visualization Gallery - Beautiful web interface for all visualizations
    """
    template_path = template_dir / "visualization.html"
    if template_path.exists():
        with open(template_path, encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Visualization template not found</h1>", status_code=404)


# Static file serving for frontend (optional)
@app.get("/frontend", response_class=HTMLResponse)
async def get_frontend():
    """
    Serve frontend application (optional - for development)
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
            .stable { color: #4CAF50; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔱 Vajra.Stream API</h1>
            <p>Sacred Technology Web Interface - <span class="stable">Stable WebSocket Version v2</span></p>

            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/</span> - API Root
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/health</span> - Health Check
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/ws-stats</span> - WebSocket Statistics
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path">/docs</span> - API Documentation
            </div>
            <div class="endpoint">
                <span class="method">GET</span> <span class="path"><a href="/visualizations">/visualizations</a></span> - 🎨 Sacred Visualization Gallery
            </div>
            <div class="endpoint">
                <span class="method">WS</span> <span class="path">/ws</span> - WebSocket Connection (Stable)
            </div>

            <h2>📚 Resources</h2>
            <p>Visit <a href="/docs" style="color: #2196F3;">/docs</a> for interactive API documentation.</p>
            <p>Visit <a href="/redoc" style="color: #2196F3;">/redoc</a> for ReDoc documentation.</p>
            <p>Visit <a href="/visualizations" style="color: #FFD700;">🎨 Visualization Gallery</a> for sacred art and healing visualizations.</p>
            <p>Visit <a href="/ws-stats" style="color: #4CAF50;">WebSocket Stats</a> for real-time connection information.</p>
        </div>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    print("Starting Vajra.Stream API Server (Stable WebSocket Version v2)...")
    print("WebSocket endpoint: ws://localhost:8008/ws")
    print("API Documentation: http://localhost:8008/docs")
    print("WebSocket Statistics: http://localhost:8008/ws-stats")
    print("Visualization Gallery: http://localhost:8008/visualizations")
    print("React/Vite frontend (if used): http://localhost:3009")

    uvicorn.run(app, host="0.0.0.0", port=8008, reload=True, log_level="info")
