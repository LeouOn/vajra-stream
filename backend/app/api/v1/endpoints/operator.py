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
    interval_seconds: int = Field(default=300, ge=5, le=3600, description="Seconds between autonomous cycles")


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
# Agentic Character Journey
# ============================================================================


@router.post("/journey/generate-character", summary="Generate an RNG-seeded character")
async def generate_character():
    from container import container

    try:
        return container.operator.generate_character(use_llm=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/journey/start", summary="Start a character journey arc")
async def start_journey():
    from container import container

    try:
        return container.operator.start_character_journey()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/journey/advance", summary="Advance journey by one stage")
async def advance_journey():
    from container import container

    try:
        return container.operator.advance_journey()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journey/status", summary="Get journey status")
async def journey_status():
    from container import container

    try:
        return container.operator.get_journey_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/journey/harvest", summary="Complete and harvest journey")
async def harvest_journey():
    from container import container

    try:
        return container.operator.harvest_journey()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/journey/run-full", summary="Run full 6-stage journey")
async def run_full_journey():
    from container import container

    try:
        return container.operator.run_full_journey()
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


# ============================================================================
# Tool Dispatch (generic — for frontend-driven tool calls)
# ============================================================================


class ToolDispatchRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to call")
    arguments: dict = Field(default_factory=dict, description="Tool arguments")


@router.post("/dispatch", summary="Dispatch a tool call")
async def dispatch_tool(request: ToolDispatchRequest):
    """Generic tool dispatch — allows the frontend to call any registered tool directly."""
    from modules.radionics_operator import ToolDispatcher

    try:
        from container import container

        dispatcher = ToolDispatcher(container)
        result = dispatcher.dispatch(request.tool_name, request.arguments)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 88 Buddhas Endpoints
# ============================================================================


@router.get("/buddhas/random", summary="Get a random Buddha for contemplation")
async def random_buddha(category: str | None = None):
    """Return a random Buddha from the 88-Buddha collection with narrative."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    try:
        svc = get_eighty_eight_buddhas()
        b = svc.random_buddha(category=category if category else None)
        narrative = svc.generate_buddha_narrative(b.name_chinese, depth="contemplation")
        return {
            "buddha": {
                "name_chinese": b.name_chinese,
                "name_pinyin": b.name_pinyin,
                "name_sanskrit": b.name_sanskrit,
                "category": b.category,
                "meaning": b.meaning,
                "realm": b.realm,
                "light": b.light,
            },
            "narrative": narrative.get("narrative", ""),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buddhas/liturgy", summary="Get the full 88-Buddha confession liturgy")
async def buddhas_liturgy():
    """Return the complete 88-Buddha Great Repentance liturgy."""
    from core.eighty_eight_buddhas import get_eighty_eight_buddhas

    try:
        svc = get_eighty_eight_buddhas()
        return svc.get_confession_sequence()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buddhas/recitation/status", summary="Get Buddha recitation loop status")
async def recitation_status():
    """Get current status of the 88-Buddha recitation loop."""
    from core.buddha_recitation_loop import get_recitation_loop

    try:
        loop = get_recitation_loop()
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buddhas/recitation/start", summary="Start Buddha recitation loop")
async def start_recitation(
    intention: str = "愿一切众生离苦得乐",
    interval_seconds: float = 3.0,
    mala_cycles: int | None = None,
    voice: str = "zh-CN-YunxiNeural",
    role: str = "buddhist_chant",
    project_id: str | None = None,
):
    """Start the continuous 88-Buddha recitation loop."""
    import asyncio

    from core.buddha_recitation_loop import get_recitation_loop

    try:
        loop = get_recitation_loop()
        if loop.state.running:
            return {"status": "already_running", "message": "Recitation loop already active."}
        try:
            running_loop = asyncio.get_event_loop()
            if running_loop.is_running():
                running_loop.create_task(
                    loop.start(
                        intention=intention,
                        interval_seconds=interval_seconds,
                        mala_cycles=mala_cycles,
                        voice=voice,
                        role=role,
                        project_id=project_id,
                    )
                )
            else:
                asyncio.run(
                    loop.start(
                        intention=intention,
                        interval_seconds=interval_seconds,
                        mala_cycles=mala_cycles,
                        voice=voice,
                        role=role,
                        project_id=project_id,
                    )
                )
        except RuntimeError:
            asyncio.run(
                loop.start(
                    intention=intention,
                    interval_seconds=interval_seconds,
                    mala_cycles=mala_cycles,
                    voice=voice,
                    role=role,
                    project_id=project_id,
                )
            )
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buddhas/recitation/stop", summary="Stop Buddha recitation loop")
async def stop_recitation():
    """Stop the active 88-Buddha recitation loop."""
    from core.buddha_recitation_loop import get_recitation_loop

    try:
        loop = get_recitation_loop()
        loop.stop()
        return loop.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Saka Dawa Endpoint
# ============================================================================


@router.get("/saka-dawa", summary="Check Saka Dawa holy month status")
async def check_saka_dawa():
    """Check if we are currently in the Saka Dawa holy month window."""
    from datetime import datetime

    from core.models.practice import Practice

    try:
        practices = Practice.get_default_practices()
        saka_dawa = next((p for p in practices if "saka" in p.name.lower() or "saka" in p.id.lower()), None)
        if not saka_dawa:
            return {"error": "Saka Dawa practice not found"}

        now = datetime.now()
        in_window = now.month in (5, 6)

        return {
            "in_saka_dawa_window": in_window,
            "current_month": now.month,
            "saka_dawa_months": [5, 6],
            "practice": {
                "id": saka_dawa.id,
                "name": saka_dawa.name,
                "tradition": saka_dawa.tradition,
                "description": saka_dawa.description,
                "genre": saka_dawa.genre,
                "merit_multiplier": saka_dawa.merit_multiplier,
                "blessing_prompt": saka_dawa.base_prompt_template,
                "preferred_hours": saka_dawa.preferred_planetary_hours,
            },
            "message": (
                "We ARE in the Saka Dawa holy month — the 4th Tibetan month where merit is multiplied 100,000 times! "
                "All compassionate practices are profoundly amplified."
                if in_window
                else "We are NOT currently in the Saka Dawa window (4th Tibetan month, typically May-June). "
                "Consider timing your major practice for that period when merit multiplies 100,000x."
            ),
            "suggested_action": (
                "Perform the Saka Dawa Blessing — generate the epic three-part sutra now while the cosmic multiplier is active!"
                if in_window
                else "Prepare for Saka Dawa by accumulating preliminary practices and setting your intention."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
