"""
Radionics Operator API Endpoints
Exposes the LLM-powered radionics operator to the frontend.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# Request / Response Models
# ============================================================================


class AnalyzeIntentionRequest(BaseModel):
    intention: str = Field(..., description="User intention text to analyze", min_length=1, max_length=1000)


class SuggestRatesRequest(BaseModel):
    intention_or_condition: str = Field(..., description="Intention or condition to suggest rates for", min_length=1)
    count: int = Field(default=5, ge=1, le=20, description="Number of rate suggestions")


class GenerateInsightRequest(BaseModel):
    session_context: dict = Field(default_factory=dict, description="Current session state for insight generation")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Chat message to send to the operator", min_length=1, max_length=2000)


class OperatorStatusResponse(BaseModel):
    llm_available: bool
    llm_provider: str
    container_available: bool
    active_session: bool
    session: dict
    tools_count: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/analyze", summary="Analyze an intention")
async def analyze_intention(request: AnalyzeIntentionRequest):
    """
    Analyze a user intention and return structured results.

    The operator parses the intention into structured components,
    searches the rate database, and recommends:
    - Target/condition/chakra identification
    - Suggested radionics rates
    - Optimal carrier frequency
    - Recommended mantra
    - Suggested healing modalities
    """
    from container import container

    try:
        operator = container.operator
        result = operator.analyze_intention(request.intention)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-rates", summary="Suggest radionics rates")
async def suggest_rates(request: SuggestRatesRequest):
    """
    Suggest radionics rates for an intention or condition.

    Searches the rate database first, then falls back to
    algorithmic rate generation if nothing is found.
    """
    from container import container

    try:
        operator = container.operator
        result = operator.suggest_rates(request.intention_or_condition, request.count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights", summary="Generate session insights")
async def generate_insights(request: GenerateInsightRequest):
    """
    Generate a natural-language insight about the current session state.

    The operator interprets RNG readings, GV trends, and scalar metrics
    to provide meaningful commentary and adjustment suggestions.
    """
    from container import container

    try:
        operator = container.operator
        result = operator.generate_insight(request.session_context or None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", summary="Chat with the operator")
async def chat_with_operator(request: ChatRequest):
    """
    Open-ended chat with the radionics operator.

    The operator can use tools (rates, broadcasting, RNG, astrology, etc.)
    and respond with natural language + tool results.
    """
    from container import container

    try:
        operator = container.operator
        result = operator.chat(request.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", summary="Get operator status")
async def get_operator_status():
    """Get the current status of the radionics operator."""
    from container import container

    try:
        operator = container.operator
        return operator.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream", summary="SSE stream of operator insights")
async def stream_insights():
    """
    Server-Sent Events stream of real-time operator commentary.

    Connects to the operator and streams insights as they are generated.
    The frontend can connect to this endpoint with EventSource to receive
    live commentary without polling.
    """
    import asyncio
    import json as json_mod

    from starlette.responses import StreamingResponse

    from container import container

    async def event_stream():
        operator = container.operator
        while True:
            try:
                # Generate insight from current session state
                state = operator._session.to_dict()
                if state.get("intention"):
                    insight = operator.generate_insight(state)
                    yield f"data: {json_mod.dumps(insight)}\n\n"
                else:
                    yield f"data: {json_mod.dumps({'insight': 'Waiting for intention...', 'type': 'idle'})}\n\n"
            except Exception as e:
                yield f"data: {json_mod.dumps({'insight': f'Error: {e}', 'type': 'error'})}\n\n"

            await asyncio.sleep(5)  # Update every 5 seconds

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Autonomous Mode
# ============================================================================


class AutonomousStartRequest(BaseModel):
    interval_seconds: int = Field(default=300, ge=60, le=3600, description="Seconds between autonomous cycles")


class SuggestionActionRequest(BaseModel):
    index: int = Field(..., ge=0, description="Index of the suggestion to act on")


@router.post("/autonomous/start", summary="Start autonomous operator mode")
async def start_autonomous(request: AutonomousStartRequest):
    """Start autonomous radionics operation — the operator monitors world events and proposes actions."""
    from container import container

    try:
        operator = container.operator
        return operator.start_autonomous_mode(request.interval_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autonomous/stop", summary="Stop autonomous operator mode")
async def stop_autonomous():
    """Stop autonomous operation."""
    from container import container

    try:
        operator = container.operator
        return operator.stop_autonomous_mode()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autonomous/status", summary="Get autonomous mode status")
async def get_autonomous_status():
    """Get current autonomous mode status and pending suggestions."""
    from container import container

    try:
        operator = container.operator
        return operator.get_autonomous_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autonomous/suggestions", summary="Get pending autonomous suggestions")
async def get_suggestions():
    """Get pending autonomous suggestions awaiting user approval."""
    from container import container

    try:
        operator = container.operator
        return {"suggestions": operator.get_autonomous_suggestions()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autonomous/approve", summary="Approve and execute a suggestion")
async def approve_suggestion(request: SuggestionActionRequest):
    """Approve and execute an autonomous suggestion."""
    from container import container

    try:
        operator = container.operator
        return operator.approve_suggestion(request.index)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/autonomous/dismiss", summary="Dismiss a suggestion")
async def dismiss_suggestion(request: SuggestionActionRequest):
    """Dismiss an autonomous suggestion without executing."""
    from container import container

    try:
        operator = container.operator
        return operator.dismiss_suggestion(request.index)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Trend Analysis
# ============================================================================


@router.get("/trends", summary="Get LLM-powered trend analysis")
async def get_trends():
    """Generate trend analysis from session history using the LLM."""
    from container import container

    try:
        operator = container.operator
        return operator.analyze_trends()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# World Context
# ============================================================================


@router.get("/world-context", summary="Get current world context")
async def get_world_context():
    """Get real-time world context — active disasters, crises, astrological transits."""
    from core.internet_context import compile_world_context

    try:
        ctx = compile_world_context()
        return {
            "events_count": len(ctx.events),
            "disasters": ctx.disasters[:10],
            "events": [
                {"title": e.title, "type": e.event_type, "severity": e.severity, "location": e.location}
                for e in ctx.events[:15]
            ],
            "planetary_hour": ctx.planetary_hour,
            "day_ruler": ctx.day_ruler,
            "summary": ctx.summary,
            "fetched_at": ctx.fetched_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LLM Blessing Loop
# ============================================================================


class BlessingLoopStartRequest(BaseModel):
    intention: str = Field(default="all beings", description="Intention for the blessings")
    interval_seconds: float = Field(default=15.0, ge=5.0, le=300.0, description="Seconds between blessings")


@router.post("/blessing-loop/start", summary="Start LLM blessing loop")
async def start_blessing_loop(request: BlessingLoopStartRequest):
    """Start a continuous loop of LLM-generated unique blessings."""
    from container import container

    try:
        operator = container.operator
        return operator.start_blessing_loop(request.intention, request.interval_seconds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blessing-loop/stop", summary="Stop LLM blessing loop")
async def stop_blessing_loop():
    """Stop the blessing loop and return collected blessings."""
    from container import container

    try:
        operator = container.operator
        return operator.stop_blessing_loop()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blessing-loop/status", summary="Get blessing loop status")
async def get_blessing_loop_status():
    """Get current blessing loop status."""
    from container import container

    try:
        operator = container.operator
        return operator.get_blessing_loop_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blessing-loop/stream", summary="Get blessing stream")
async def get_blessing_stream(since: int = 0):
    """Get blessings generated since the given index."""
    from container import container

    try:
        operator = container.operator
        return {"blessings": operator.get_blessing_stream(since), "since": since}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/blessing-loop/next", summary="Generate next blessing")
async def generate_next():
    """Manually trigger the next blessing generation."""
    from container import container

    try:
        operator = container.operator
        blessing = operator.generate_next_blessing()
        return {"blessing": blessing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LLM Configuration
# ============================================================================


@router.get("/llm-config", summary="Get LLM configuration")
async def get_llm_config():
    """Get current LLM role assignments and model names."""
    from container import container

    try:
        operator = container.operator
        creative = operator.creative_llm
        return {
            "orchestrator": {
                "model": getattr(operator.llm, "model_name", "auto") if operator.llm else "none",
                "provider": operator.llm.model_type if operator.llm else "none",
                "available": bool(operator.llm and (operator.llm.client or operator.llm.local_model)),
            },
            "creative": {
                "model": getattr(creative, "model_name", "auto") if creative else "none",
                "provider": creative.model_type if creative else "none",
                "available": bool(creative and (creative.client or creative.local_model)),
            },
            "dual_llm_active": operator._creative_llm is not None and operator._creative_llm is not operator._llm,
            "env_vars": {
                "LM_STUDIO_ORCHESTRATOR_MODEL": "Set to override orchestrator model",
                "LM_STUDIO_CREATIVE_MODEL": "Set to use a different model for blessings/stories",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session", summary="Get current session state")
async def get_session():
    """Get the current operator session context."""
    from container import container

    try:
        operator = container.operator
        return operator._session.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
