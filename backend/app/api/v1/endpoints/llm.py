"""
LLM Agent API Endpoints
Provides chat-based interface with tool calling and rule-based local fallback.
"""

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

try:
    import aiohttp
except ImportError:
    aiohttp = None

from backend.app.api.v1.endpoints.agent_suggestions import (
    FailedToolCallSchema,
    log_failed_tool_call,
)
from backend.core.llm_agent.tools import TOOL_REGISTRY, get_tool_schemas
from backend.core.services.blessing_scheduler import get_scheduler
from backend.core.services.population_manager import get_population_manager
from backend.core.services.rng_attunement_service import get_rng_service

# New async LLM / context layer (Phase 1 — ProviderRegistry + ContextModule).
from core.context import (
    AnatomyContextModule,
    AstrologyContextModule,
    ContextRequest,
    HardwareContextModule,
    SystemPromptBuilder,
)
from core.llm.base import strip_thinking
from core.llm.defaults import (
    DEFAULT_MODELS_BY_USE_CASE,
    KNOWN_FEATURED_MODEL_IDS,
    NEMOTRON_FREE_MODEL_ID,
)
from core.llm.retry import retry_with_backoff
from core.llm.usage import LLMUsageTracker, UsageRecord

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessage(BaseModel):
    role: str
    content: str
    name: str | None = None  # Match core/llm/models.py ChatMessage
    tool_call_id: str | None = None  # Required by tool loop message injection


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    api_key: str | None = None
    provider: str | None = "auto"  # 'openai', 'anthropic', 'local', 'auto'
    model: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt: str | None = None
    stream: bool = False
    tools: list | None = None
    include_astrology: bool | None = False
    include_anatomy: bool | None = False
    include_hardware: bool | None = False
    use_rag: bool | None = False
    astrology_data: dict | None = None
    debug_mode: bool | None = False


class ToolCallLog(BaseModel):
    tool_name: str
    arguments: dict
    status: str
    result: Any | None = None
    error: str | None = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallLog]
    debug_info: dict | None = None


def format_messages_for_llm(request_messages: list[ChatMessage], default_system_prompt: str):
    # Find any system messages in request_messages
    custom_system_parts = []
    for msg in request_messages:
        if msg.role == "system":
            custom_system_parts.append(msg.content)

    if custom_system_parts:
        full_system_prompt = f"{default_system_prompt}\n\nContext and details:\n" + "\n".join(custom_system_parts)
    else:
        full_system_prompt = default_system_prompt

    # Get all non-system messages
    non_system_messages = [msg for msg in request_messages if msg.role != "system"]

    # Skip any leading assistant messages (e.g. welcome message) to ensure it starts with a user message
    first_user_idx = 0
    while first_user_idx < len(non_system_messages) and non_system_messages[first_user_idx].role == "assistant":
        first_user_idx += 1

    chat_messages = []
    for msg in non_system_messages[first_user_idx:]:
        if msg.role in ("user", "assistant"):
            chat_messages.append({"role": msg.role, "content": msg.content})

    return full_system_prompt, chat_messages


TOOL_NAME_ALIASES: dict[str, str] = {
    "list_targets": "list_populations",
    "show_targets": "list_populations",
    "show_populations": "list_populations",
    "get_targets": "list_populations",
    "list_population": "list_populations",
    "start_blessing": "start_automation",
    "stop_blessing": "stop_automation",
    "begin_session": "start_automation",
    "get_session": "get_automation_status",
    "session_status": "get_automation_status",
    "list_session": "get_automation_stats",
}


def _resolve_tool_name(name: str) -> str:
    return TOOL_NAME_ALIASES.get(name, name)


def _parse_text_tool_calls(content: str) -> list[dict[str, Any]]:
    """Extract tool calls from LLM text output when native tool_calls is empty.

    Scans all top-level {...} blocks via brace-depth counting and tries to
    parse each as a tool call. Handles nested braces in arguments values.
    """
    results: list[dict[str, Any]] = []
    i = 0
    while i < len(content):
        if content[i] != "{":
            i += 1
            continue
        depth = 0
        start = i
        while i < len(content):
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            break
        candidate = content[start : i + 1]
        i += 1
        if len(candidate) < 15:
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        name = parsed.get("tool") or parsed.get("name") or parsed.get("function") or ""
        args = parsed.get("arguments") or parsed.get("parameters") or parsed.get("args") or {}
        if name and isinstance(name, str):
            results.append({"name": name.strip(), "arguments": args if isinstance(args, dict) else {}})
    return results


async def execute_tool_locally(name: str, args: dict) -> Any:
    """Helper to execute a tool function from the tool registry"""
    if name not in TOOL_REGISTRY:
        resolved = _resolve_tool_name(name)
        if resolved in TOOL_REGISTRY:
            name = resolved
        else:
            raise ValueError(f"Tool {name} not found in registry")

    tool_func = TOOL_REGISTRY[name]
    logger.info(f"🔧 Executing tool {name} with args: {args}")

    # Special case: avoid self-HTTP calls by accessing services directly
    # This prevents deadlocks when tools call back to the same server
    if name == "list_populations":
        pm = get_population_manager()
        active_only = args.get("active_only", False)
        category = args.get("category")
        urgent_only = args.get("urgent_only", False)
        pops = [p.to_dict() for p in pm.get_all_populations()]
        if active_only:
            pops = [p for p in pops if p.get("is_active")]
        if category:
            pops = [p for p in pops if p.get("category") == category]
        if urgent_only:
            pops = [p for p in pops if p.get("is_urgent")]
        return pops
    elif name == "get_population_statistics":
        pm = get_population_manager()
        stats = pm.get_statistics()
        return {
            "total_populations": stats.get("total_populations", 0),
            "active_populations": stats.get("active_populations", 0),
            "total_blessings_sent": stats.get("total_blessings_sent", 0),
            "total_mantras_repeated": stats.get("total_mantras_repeated", 0),
        }
    elif name == "create_population":
        pm = get_population_manager()
        pop = pm.create_population(**args)
        return pop.to_dict() if pop else None
    elif name == "update_population":
        pm = get_population_manager()
        pop = pm.update_population(args.get("population_id"), **args)
        return pop.to_dict() if pop else None
    elif name == "start_automation":
        from backend.core.services.blessing_scheduler import SchedulerConfig, SchedulerMode, get_scheduler

        scheduler = get_scheduler()
        config = SchedulerConfig(
            mode=SchedulerMode(args.get("mode", "round_robin")),
            duration_per_population=args.get("duration_per_population", 1800),
            transition_pause=args.get("transition_pause", 30),
            link_rng=args.get("link_rng", True),
            auto_dedicate=args.get("auto_dedicate", True),
            continuous_mode=args.get("continuous_mode", True),
            only_active=args.get("only_active", True),
            min_priority=args.get("min_priority", 1),
        )
        session_id = scheduler.start_automation(config=config)
        session = scheduler.sessions.get(session_id)
        queue_len = len(session.populations_queue) if session else 0
        return {"session_id": session_id, "populations_in_queue": queue_len}
    elif name == "stop_automation":
        from backend.core.services.blessing_scheduler import get_scheduler

        scheduler = get_scheduler()
        result = scheduler.stop_automation(args.get("session_id"))
        return result
    elif name == "get_automation_status":
        from backend.core.services.blessing_scheduler import get_scheduler

        scheduler = get_scheduler()
        status_info = scheduler.get_current_status(args.get("session_id"))
        return status_info if status_info is not None else {}
    elif name == "get_automation_stats":
        from backend.core.services.blessing_scheduler import get_scheduler

        scheduler = get_scheduler()
        return scheduler.get_session_stats(args.get("session_id"))
    elif name == "pause_automation":
        from backend.core.services.blessing_scheduler import get_scheduler

        scheduler = get_scheduler()
        success = scheduler.pause_automation(args.get("session_id"))
        return {
            "success": success,
            "message": "Automation paused successfully" if success else "Failed to pause automation",
        }
    elif name == "resume_automation":
        from backend.core.services.blessing_scheduler import get_scheduler

        scheduler = get_scheduler()
        success = scheduler.resume_automation(args.get("session_id"))
        return {
            "success": success,
            "message": "Automation resumed successfully" if success else "Failed to resume automation",
        }
    elif name == "create_rng_session":
        from backend.core.services.rng_attunement_service import get_rng_service

        service = get_rng_service()
        session_id = service.create_session(
            session_id=args.get("session_id"),
            baseline_tone_arm=args.get("baseline_tone_arm", 5.0),
            sensitivity=args.get("sensitivity", 1.0),
        )
        return {"session_id": session_id}
    elif name == "get_rng_reading":
        from backend.core.services.rng_attunement_service import get_rng_service

        service = get_rng_service()
        reading = service.get_reading(args.get("session_id"))
        if reading:
            return {
                "timestamp": reading.timestamp,
                "raw_value": reading.raw_value,
                "tone_arm": reading.tone_arm,
                "needle_position": reading.needle_position,
                "needle_state": reading.needle_state.value
                if hasattr(reading.needle_state, "value")
                else reading.needle_state,
                "quality": reading.quality.value if hasattr(reading.quality, "value") else reading.quality,
                "entropy": reading.entropy,
                "coherence": reading.coherence,
                "trend": reading.trend,
                "floating_needle_score": reading.floating_needle_score,
            }
        return {}
    elif name == "stop_rng_session":
        from backend.core.services.rng_attunement_service import get_rng_service

        service = get_rng_service()
        session_id = args.get("session_id")
        summary = service.get_session_summary(session_id) or {}
        service.stop_session(session_id)
        return summary
    elif name == "create_blessing_slideshow":
        from backend.core.services.blessing_slideshow_service import (
            IntentionSet,
            IntentionType,
            MantraType,
            get_blessing_slideshow_service,
        )

        service = get_blessing_slideshow_service()
        intentions = [IntentionType(i) for i in args.get("intentions", ["love", "healing", "peace"])]
        intention_set = IntentionSet(
            primary_mantra=MantraType(args.get("mantra", "chenrezig")),
            intentions=intentions,
            repetitions_per_photo=args.get("repetitions_per_photo", 108),
            dedication=args.get("dedication", "May all beings benefit"),
        )
        session_id = service.create_session(
            directory_path=args.get("directory_path"),
            intention_set=intention_set,
            loop_mode=args.get("loop_mode", True),
            display_duration_ms=args.get("display_duration_ms", 2000),
            rng_session_id=args.get("rng_session_id"),
        )
        session = service.sessions.get(session_id)
        total_photos = len(session.photos) if session else 0
        return {"session_id": session_id, "total_photos": total_photos}
    elif name == "get_current_slide":
        from backend.core.services.blessing_slideshow_service import get_blessing_slideshow_service

        service = get_blessing_slideshow_service()
        slide_info = service.get_current_slide(args.get("session_id"))
        return slide_info if slide_info is not None else {}
    elif name == "stop_slideshow":
        from backend.core.services.blessing_slideshow_service import get_blessing_slideshow_service

        service = get_blessing_slideshow_service()
        stats = service.stop_session(args.get("session_id"))
        return stats
    elif name == "forge_sigil":
        from backend.core.services.sigil_service import sigil_service

        return await sigil_service.forge_sigil(args.get("intention"), args.get("kamea", "saturn"))
    elif name == "cast_tarot_spread":
        from backend.core.services.divination_service import divination_service

        res = divination_service.draw_tarot(args.get("count", 3))
        return {"cards": res}
    elif name == "cast_i_ching":
        from backend.core.services.divination_service import divination_service

        return divination_service.cast_i_ching()
    elif name == "cast_geomancy":
        from backend.core.services.divination_service import divination_service

        return divination_service.cast_geomancy()

    elif name == "search_grimoire_correspondences":
        from backend.core.services.grimoire_service import grimoire_service

        return grimoire_service.search(args.get("query", ""))
    elif name == "get_planetary_hours_and_transits":
        import datetime

        from backend.core.services.grimoire_service import grimoire_service
        from backend.core.services.vajra_service import vajra_service

        now = datetime.datetime.now()
        astro_data = await vajra_service._get_astrology_data()
        hour_data = grimoire_service.get_planetary_hours(now.hour, now.weekday())
        return {"astrology": astro_data, "planetary_hour": hour_data, "timestamp": time.time()}
    elif name == "get_random_buddha":
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        category = args.get("category")
        b = svc.random_buddha(category=category)
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
    elif name == "generate_buddha_narrative":
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        return svc.generate_buddha_narrative(
            buddha_name=args.get("buddha_name", ""),
            depth=args.get("depth", "contemplation"),
        )
    elif name == "get_88_buddhas_liturgy":
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        return svc.get_confession_sequence()
    elif name == "recite_buddha_name":
        from core.eighty_eight_buddhas import get_eighty_eight_buddhas

        svc = get_eighty_eight_buddhas()
        b = svc.get_buddha_by_name(args.get("buddha_name", ""))
        if not b:
            return {"error": f"Buddha not found: {args.get('buddha_name')}"}
        return {
            "buddha": b.name_chinese,
            "pinyin": b.name_pinyin,
            "message": f"Recitation of {b.name_chinese} ({b.name_pinyin}) would play via Edge TTS.",
        }
    elif name == "start_buddha_recitation":
        import asyncio

        from core.buddha_recitation_loop import get_recitation_loop

        loop = get_recitation_loop()
        if loop.state.running:
            return {"status": "already_running"}
        intention = args.get("intention", "愿一切众生离苦得乐")
        interval = args.get("interval_seconds", 3.0)
        mala_cycles = args.get("mala_cycles")
        try:
            running_loop = asyncio.get_event_loop()
            if running_loop.is_running():
                running_loop.create_task(
                    loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles)
                )
            else:
                asyncio.run(loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles))
        except RuntimeError:
            asyncio.run(loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles))
        return loop.get_status()
    elif name == "stop_buddha_recitation":
        from core.buddha_recitation_loop import get_recitation_loop

        loop = get_recitation_loop()
        await loop.stop()
        return loop.get_status()
    elif name == "get_buddha_recitation_status":
        from core.buddha_recitation_loop import get_recitation_loop

        return get_recitation_loop().get_status()
    elif name == "check_saka_dawa":
        from datetime import datetime as dt

        from core.models.practice import Practice

        practices = Practice.get_default_practices()
        saka_dawa = next((p for p in practices if "saka" in p.name.lower() or "saka" in p.id.lower()), None)
        if not saka_dawa:
            return {"error": "Saka Dawa practice not found"}
        now = dt.now()
        in_window = now.month in (5, 6)
        return {
            "in_saka_dawa_window": in_window,
            "current_month": now.month,
            "practice": {
                "id": saka_dawa.id,
                "name": saka_dawa.name,
                "genre": saka_dawa.genre,
                "merit_multiplier": saka_dawa.merit_multiplier,
                "blessing_prompt": saka_dawa.base_prompt_template,
            },
            "message": "Saka Dawa is ACTIVE — 100,000x merit!" if in_window else "Not in Saka Dawa window.",
        }
    elif name == "check_auspicious_timing":
        from core.auspicious_timing import check_auspicious_window

        return check_auspicious_window(args.get("genre", "healing")).to_dict()
    elif name == "generate_character":
        from core.character_generator import CharacterGenerator

        gen = CharacterGenerator()
        sheet = gen.generate(use_llm=False)
        return sheet.to_dict()
    elif (
        name == "start_character_journey"
        or name == "advance_journey"
        or name == "get_journey_status"
        or name == "run_full_journey"
    ):
        from container import container
        from modules.radionics_operator import ToolDispatcher

        disp = ToolDispatcher(container)
        return disp.dispatch(name, args)
    else:
        # Fallback: call the tool function directly (detect if async or sync)
        import inspect

        if inspect.iscoroutinefunction(tool_func):
            return await tool_func(**args)
        return tool_func(**args)


async def run_rule_based_fallback(query: str) -> ChatResponse:
    """
    Intelligent fallback system that matches natural language commands
    and executes tools directly on the backend.
    """
    query_lower = query.lower().strip()
    tool_calls = []
    response_text = ""

    # 1. Start Automation
    if re.search(
        r"\b(start|begin|activate|turn\s*on|enable)\s*(the\s*)?(automation|scheduler|rotation|cycle)\b", query_lower
    ):
        try:
            res = await execute_tool_locally("start_automation", {})
            tool_calls.append(ToolCallLog(tool_name="start_automation", arguments={}, status="success", result=res))
            response_text = (
                f"🔮 **Vajra.Stream Automation Initiated**\n\n"
                f"I have successfully activated the automated blessing rotation.\n"
                f"- **Session ID**: `{res.get('session_id', '')[:28]}…`\n"
                f"- **Populations in queue**: {res.get('populations_in_queue')}\n"
                f"- **Status**: Continuous rotation started."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="start_automation", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to start automation: {str(e)}"

    # 2. Stop Automation
    elif re.search(
        r"\b(stop|pause|suspend|disable|turn\s*off|end)\s*(the\s*)?(automation|scheduler|rotation|cycle)\b", query_lower
    ):
        try:
            scheduler = get_scheduler()
            active_sessions = list(scheduler.sessions.keys())
            if active_sessions:
                session_id = active_sessions[0]
                res = await execute_tool_locally("stop_automation", {"session_id": session_id})
                tool_calls.append(
                    ToolCallLog(
                        tool_name="stop_automation", arguments={"session_id": session_id}, status="success", result=res
                    )
                )
                response_text = (
                    f"🛑 **Vajra.Stream Automation Stopped**\n\n"
                    f"I have stopped the active scheduler rotation session (`{session_id}`).\n"
                    f"- **Total duration**: {res.get('total_duration', 0):.1f} seconds\n"
                    f"- **Completed cycles**: {res.get('cycle_count', 0)}\n"
                    f"- **Total photos blessed**: {res.get('total_photos_blessed', 0)}\n"
                    f"- **Total mantras repeated**: {res.get('total_mantras', 0)}"
                )
            else:
                response_text = "ℹ️ No active automation scheduler session was found running."
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="stop_automation", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to stop automation: {str(e)}"

    # 3. List Populations
    elif re.search(r"\b(list|show|view|get)\s*(the\s*)?(populations|targets)\b", query_lower):
        try:
            res = await execute_tool_locally("list_populations", {})
            tool_calls.append(ToolCallLog(tool_name="list_populations", arguments={}, status="success", result=res))
            if res:
                response_text = (
                    "👥 **Vajra.Stream Target Populations**\n\nHere are the registered blessing target populations:\n\n"
                )
                for pop in res:
                    response_text += (
                        f"- **{pop.get('name')}** (Category: `{pop.get('category')}`)\n"
                        f"  - Intentions: {', '.join(pop.get('intentions', []))}\n"
                        f"  - Priority: {pop.get('priority')}/10 | Photo Count: {pop.get('photo_count')}\n"
                    )
            else:
                response_text = "ℹ️ No populations are registered. Go to Targets to add one!"
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="list_populations", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to list populations: {str(e)}"

    # 4. Get Population Statistics
    elif re.search(
        r"\b(stats|statistics|overall\s*stats|summary)\s*(of\s*populations|across\s*populations|of\s*blessings)?\b",
        query_lower,
    ):
        try:
            res = await execute_tool_locally("get_population_statistics", {})
            tool_calls.append(
                ToolCallLog(tool_name="get_population_statistics", arguments={}, status="success", result=res)
            )
            response_text = (
                f"📈 **Vajra.Stream System-Wide Blessing Stats**\n\n"
                f"- **Total Blessings Sent**: {res.get('total_blessings_sent', 0)}\n"
                f"- **Total Mantras Repeated**: {res.get('total_mantras_repeated', 0)}\n"
                f"- **Total Blessing Duration**: {res.get('total_blessing_duration', 0):.1f} seconds\n"
                f"- **Active Populations Count**: {res.get('total_populations', 0)}"
            )
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="get_population_statistics", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to retrieve statistics: {str(e)}"

    # 5. Start RNG Session
    elif re.search(
        r"\b(start|create|begin|activate)\s*(a\s*)?(rng|random\s*number\s*generator|attunement|needle)\s*(session)?\b",
        query_lower,
    ):
        try:
            res = await execute_tool_locally("create_rng_session", {"baseline_tone_arm": 5.0, "sensitivity": 1.0})
            tool_calls.append(
                ToolCallLog(
                    tool_name="create_rng_session",
                    arguments={"baseline_tone_arm": 5.0, "sensitivity": 1.0},
                    status="success",
                    result=res,
                )
            )
            response_text = (
                f"🔮 **RNG Attunement Session Created**\n\n"
                f"The random number generator is now capturing local quantum fluctuations.\n"
                f"- **Session ID**: `{res.get('session_id')}`\n"
                f"- Tone Arm Baseline calibrated to 5.0."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="create_rng_session", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to start RNG session: {str(e)}"

    # 6. Stop RNG Session
    elif re.search(
        r"\b(stop|end|terminate|deactivate)\s*(the\s*)?(rng|random\s*number\s*generator|attunement|needle)\s*(session)?\b",
        query_lower,
    ):
        try:
            service = get_rng_service()
            active_rng = service.get_all_sessions()
            if active_rng:
                session_id = active_rng[-1]  # Take the last active session
                res = await execute_tool_locally("stop_rng_session", {"session_id": session_id})
                tool_calls.append(
                    ToolCallLog(
                        tool_name="stop_rng_session", arguments={"session_id": session_id}, status="success", result=res
                    )
                )
                response_text = (
                    f"🛑 **RNG Attunement Stopped**\n\n"
                    f"Stopped the attunement tracker session `{session_id}`.\n"
                    f"- **Total readings captured**: {res.get('total_readings', 0)}\n"
                    f"- **Floating Needle count**: {res.get('floating_needle_count', 0)}\n"
                    f"- **Average Coherence**: {res.get('avg_coherence', 0.0):.2f}\n"
                    f"- **Duration**: {res.get('duration_seconds', 0.0):.1f}s"
                )
            else:
                response_text = "ℹ️ No active RNG attunement sessions are currently running."
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="stop_rng_session", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to stop RNG session: {str(e)}"

    # 7. Forge Sigil Fallback
    elif re.search(r"\b(forge|create|make|generate)\s*(a\s*)?sigil\b", query_lower):
        try:
            intention = "Divine Alignment"
            intent_match = re.search(r"\b(for|of|to)\s+(.+)$", query_lower)
            if intent_match:
                intention = intent_match.group(2).strip()

            res = await execute_tool_locally("forge_sigil", {"intention": intention, "kamea": "saturn"})
            tool_calls.append(
                ToolCallLog(
                    tool_name="forge_sigil",
                    arguments={"intention": intention, "kamea": "saturn"},
                    status="success",
                    result=res,
                )
            )
            response_text = (
                f"🔮 **Sigil Forged for Intention: '{intention}'**\n\n"
                f"The intention has been reduced to its core letter components: `{res.get('reduced_letters')}`.\n"
                f"A neon glowing sigil has been generated on the Saturn magic square (Kamea) and saved.\n\n"
                f"*(Use the Broadcast tab to transmit this frequency signature!)*"
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="forge_sigil", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to forge sigil: {str(e)}"

    # 8. Cast Tarot Spread Fallback
    elif re.search(r"\b(draw|cast|get|show)\s*(a\s*)?(tarot|card|spread)\b", query_lower):
        try:
            count = 3
            if "single" in query_lower or "one" in query_lower or "1" in query_lower:
                count = 1
            elif "ten" in query_lower or "10" in query_lower or "celtic" in query_lower:
                count = 10

            res = await execute_tool_locally("cast_tarot_spread", {"count": count})
            tool_calls.append(
                ToolCallLog(tool_name="cast_tarot_spread", arguments={"count": count}, status="success", result=res)
            )

            response_text = "🔮 **Tarot Spread Drawn**\n\nHere are the cards representing your inquiry:\n\n"
            for idx, card in enumerate(res.get("cards", [])):
                orient = " (Reversed)" if card.get("reversed") else ""
                response_text += (
                    f"{idx + 1}. **{card.get('name')}**{orient}\n"
                    f"   - *Element*: {card.get('element')} | *Ruler/Correspondence*: {card.get('ruler') or 'N/A'}\n"
                    f"   - *Guidance*: {card.get('meaning')}\n"
                )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="cast_tarot_spread", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to draw Tarot cards: {str(e)}"

    # 9. Cast I Ching Fallback
    elif re.search(r"\b(cast|throw|get|consult)\s*(the\s*)?(i\s*ching|hexagram)\b", query_lower):
        try:
            res = await execute_tool_locally("cast_i_ching", {})
            tool_calls.append(ToolCallLog(tool_name="cast_i_ching", arguments={}, status="success", result=res))
            primary = res.get("primary", {})
            relating = res.get("relating", {})
            lines_str = ", ".join(str(l) for l in res.get("cast_lines", []))

            response_text = (
                f"☯️ **I Ching Oracle Consulted**\n\n"
                f"Lines generated (bottom-to-top): `[{lines_str}]`\n\n"
                f"**Primary Hexagram**: {primary.get('name')}\n"
                f"- *Vibe*: {primary.get('meaning')}\n\n"
            )
            if res.get("has_changes"):
                response_text += (
                    f"**Relating Hexagram** (due to changing lines at {res.get('changing_lines')}): {relating.get('name')}\n"
                    f"- *Vibe*: {relating.get('meaning')}\n"
                )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="cast_i_ching", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to cast I Ching: {str(e)}"

    # 10. Cast Geomancy Fallback
    elif re.search(r"\b(cast|generate|geomancy|geomantic|shield)\b", query_lower):
        try:
            res = await execute_tool_locally("cast_geomancy", {})
            tool_calls.append(ToolCallLog(tool_name="cast_geomancy", arguments={}, status="success", result=res))
            figs = res.get("figures", {})

            response_text = (
                f"👁 **Geomantic Shield Chart Cast**\n\n"
                f"- **First Mother**: {figs.get('Mother 1', {}).get('name')} ({figs.get('Mother 1', {}).get('translation')})\n"
                f"- **Second Mother**: {figs.get('Mother 2', {}).get('name')} ({figs.get('Mother 2', {}).get('translation')})\n"
                f"- **Right Witness**: {figs.get('Right Witness', {}).get('name')} ({figs.get('Right Witness', {}).get('translation')})\n"
                f"- **Left Witness**: {figs.get('Left Witness', {}).get('name')} ({figs.get('Left Witness', {}).get('translation')})\n"
                f"- **The Judge**: {figs.get('Judge', {}).get('name')} - *Key*: {figs.get('Judge', {}).get('meaning')}\n"
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="cast_geomancy", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to cast Geomancy chart: {str(e)}"

    # 11. Search Grimoire Fallback
    elif re.search(r"\b(search|lookup|query|find)\s*(the\s*)?grimoire\s*(for\s+)?(.+)$", query_lower):
        try:
            term = (
                re.search(r"\b(search|lookup|query|find)\s*(the\s*)?grimoire\s*(for\s+)?(.+)$", query_lower)
                .group(4)
                .strip()
            )
            res = await execute_tool_locally("search_grimoire_correspondences", {"query": term})
            tool_calls.append(
                ToolCallLog(
                    tool_name="search_grimoire_correspondences", arguments={"query": term}, status="success", result=res
                )
            )

            if res:
                response_text = f"📚 **Grimoire Search Results for '{term}'**\n\n"
                for item in res[:5]:
                    response_text += (
                        f"🪐 **Planet**: {item.get('planet')} | **Metal**: {item.get('metal')}\n"
                        f"  - **Minerals**: {', '.join(item.get('minerals', []))}\n"
                        f"  - **Herbs**: {', '.join(item.get('herbs', []))}\n"
                        f"  - **Rates**: {item.get('rates')} | **Chakra**: {item.get('chakra')}\n"
                        f"  - **Focus**: {item.get('influence')}\n\n"
                    )
                f"ℹ️ No direct correspondences found in the Grimoire library for '{term}'."
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="search_grimoire_correspondences", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to search Grimoire: {str(e)}"

    # 11b. Start Narrative Loop
    elif re.search(
        r"\b(start|activate|begin|turn\s*on)\s*(the\s*)?(narrative\s*loop|broadcast\s*loop|story\s*loop|transmission\s*loop)\b",
        query_lower,
    ):
        try:
            res = await execute_tool_locally("start_narrative_loop", {"interval_minutes": 15})
            tool_calls.append(
                ToolCallLog(
                    tool_name="start_narrative_loop", arguments={"interval_minutes": 15}, status="success", result=res
                )
            )
            response_text = (
                "🔮 **Continuous Broadcast Narrative Loop Activated**\n\n"
                "I have started the background narrative generation loop.\n"
                "- **Interval**: every 15 minutes\n"
                "- **Status**: Active and broadcasting."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="start_narrative_loop", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to start narrative loop: {str(e)}"

    # 11c. Stop Narrative Loop
    elif re.search(
        r"\b(stop|deactivate|turn\s*off|end)\s*(the\s*)?(narrative\s*loop|broadcast\s*loop|story\s*loop|transmission\s*loop)\b",
        query_lower,
    ):
        try:
            res = await execute_tool_locally("stop_narrative_loop", {})
            tool_calls.append(ToolCallLog(tool_name="stop_narrative_loop", arguments={}, status="success", result=res))
            response_text = (
                "🛑 **Continuous Broadcast Narrative Loop Stopped**\n\n"
                "I have successfully stopped the active background narrative loop."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(tool_name="stop_narrative_loop", arguments={}, status="error", error=str(e)))
            response_text = f"❌ Failed to stop narrative loop: {str(e)}"

    # 11d. Get Narrative Loop Status
    elif re.search(
        r"\b(status|check|info)\s*(of\s*the\s*)?(narrative\s*loop|broadcast\s*loop|story\s*loop|transmission\s*loop)\b",
        query_lower,
    ):
        try:
            res = await execute_tool_locally("get_narrative_loop_status", {})
            tool_calls.append(
                ToolCallLog(tool_name="get_narrative_loop_status", arguments={}, status="success", result=res)
            )
            active_str = "ACTIVE (Broadcasting)" if res.get("active") else "INACTIVE"
            response_text = (
                f"ℹ️ **Continuous Narrative Loop Status**\n\n"
                f"- **Active Status**: {active_str}\n"
                f"- **Cycle Interval**: {res.get('interval_minutes')} minutes\n"
            )
            if res.get("last_generated"):
                response_text += f"- **Last Blessing Genre**: `{res['last_generated'].get('genre')}`"
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="get_narrative_loop_status", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to get loop status: {str(e)}"

    # 11e. List Settings / Realms
    elif re.search(r"\b(list|show|view)\s*(the\s*)?(realms|locations|settings)\b", query_lower):
        try:
            res = await execute_tool_locally("list_narrative_locations", {})
            tool_calls.append(
                ToolCallLog(tool_name="list_narrative_locations", arguments={}, status="success", result=res)
            )
            if res:
                response_text = "🗺️ **Active Realms and Settings**\n\n"
                for loc in res:
                    m_str = "Metaphysical" if loc.get("is_metaphysical") else "Earthly"
                    response_text += f"- **{loc.get('name')}** ({m_str})\n  - *Description*: {loc.get('description')}\n"
            else:
                response_text = "ℹ️ No narrative settings found."
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="list_narrative_locations", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to list settings: {str(e)}"

    # 11f. List Characters / Archetypes
    elif re.search(r"\b(list|show|view)\s*(the\s*)?(characters|archetypes)\b", query_lower):
        try:
            res = await execute_tool_locally("list_narrative_characters", {})
            tool_calls.append(
                ToolCallLog(tool_name="list_narrative_characters", arguments={}, status="success", result=res)
            )
            if res:
                response_text = "👥 **Narrative Characters and Archetypes**\n\n"
                for char in res:
                    response_text += (
                        f"- **{char.get('name')}** ({char.get('role')})\n  - *Description*: {char.get('description')}\n"
                    )
            else:
                response_text = "ℹ️ No characters found."
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="list_narrative_characters", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to list characters: {str(e)}"

    # 11g. Generate Single Outlook
    elif re.search(r"\b(generate|create|write)\s*(a\s*)?(single\s*)?(outlook|blessing|story|narrative)\b", query_lower):
        try:
            res = await execute_tool_locally("generate_single_outlook", {})
            tool_calls.append(
                ToolCallLog(tool_name="generate_single_outlook", arguments={}, status="success", result=res)
            )
            response_text = (
                f"📜 **Generated Blessing Narrative**\n\n"
                f"{res.get('narrative')}\n\n"
                f"--- \n"
                f"- **Genre**: {res.get('genre')} | **Astrology**: {res.get('astrology_used')[:60]}..."
            )
        except Exception as e:
            tool_calls.append(
                ToolCallLog(tool_name="generate_single_outlook", arguments={}, status="error", error=str(e))
            )
            response_text = f"❌ Failed to generate narrative: {str(e)}"

    # 12. Predefined Dharma Tales Fallback
    elif re.search(
        r"\b(tell|generate|show|give|read)\s*(me\s*)?(a\s*)?(dharma\s*tale|teaching|story|wisdom|parable|tale)\b",
        query_lower,
    ):
        parable = (
            "🏯 **Zen Wisdom: A Cup of Tea**\n\n"
            "Nan-in, a Japanese master during the Meiji era, received a university professor who came to inquire about Zen.\n\n"
            "Nan-in served tea. He poured his visitor's cup full, and then kept on pouring.\n\n"
            "The professor watched the overflow until he no longer could restrain himself. "
            '"It is overfull. No more will go in!"\n\n'
            '"Like this cup," Nan-in said, "you are full of your own opinions and speculations. '
            'How can I show you Zen unless you first empty your cup?"'
        )
        response_text = parable

    # 13. Help / Introduction
    else:
        response_text = (
            "👋 **Welcome to the Vajra.Stream AI Command Center!**\n\n"
            "I can assist you in controlling your radionics operations and sacred generators using natural language commands. "
            "If an OpenAI or Anthropic API Key is not set, I run in **Local Command Mode**. Here are some commands you can type:\n\n"
            "- 🔮 `Start automation` - Begins the 24/7 round-robin population blessing cycle.\n"
            "- 🛑 `Stop automation` - Terminates the active scheduler and blessings.\n"
            "- 👥 `List populations` - Shows all registered blessing targets and categories.\n"
            "- 📈 `Get statistics` - Displays cumulative counts of photos blessed and mantras chanted.\n"
            "- 🎲 `Start RNG session` - Calibrates and begins tracking quantum entropy & floating needles.\n"
            "- 🛑 `Stop RNG session` - Concludes the active attunement tracker.\n"
            "- 🔮 `Forge sigil for [intention]` - Generates a vector Kamea sigil pattern.\n"
            "- 🃏 `Draw tarot cards` - Casts a Tarot spread for your query.\n"
            "- ☯️ `Cast I Ching` - Casts a hexagram representing the current situation.\n"
            "- 👁 `Cast geomancy` - Draws a shield chart mapping 16 figures to houses.\n"
            "- 📚 `Search grimoire for [herbs/crystals/planets]` - Searches correspondences library.\n"
            "- 📖 `Generate outlook` - Trigger a localized blessing parable narrative.\n"
            "- 🔄 `Start narrative loop` - Starts the background narrative generation loop.\n"
            "- 🛑 `Stop narrative loop` - Pauses continuous narrative cycles.\n"
            "- 🗺️ `List realms` - Lists all defined setting places and lands.\n"
            "- 👥 `List characters` - Lists all spiritual actors and dialogue archetypes.\n"
            "- 📚 `Tell me a dharma tale` - Generates a story or parable for your contemplation."
        )

    return ChatResponse(response=response_text, tool_calls=tool_calls)


# ============================ Context + Provider Helpers ============================
# These helpers replace the old inline compile_*_context() functions and the
# 6 copy-pasted tool-calling loops inside chat_interaction.  They are used by
# the registry-backed chat endpoint below.


async def _build_system_prompt_with_context(request: ChatRequest) -> str:
    """Build the base operator system prompt and append composable context modules.

    Uses :class:`SystemPromptBuilder` + the ContextModule registry (``core.context``)
    to assemble astrology / anatomy / hardware sections concurrently.  Every module
    is defensive — a single broken module never prevents the others from
    contributing, and a total builder failure falls back to the bare base prompt.
    """
    base_prompt = (
        "You are the Vajra.Stream AI Operator, a wise assistant designed to control a "
        "radionics board, crystal broadcasters, scalar wave generators, and blessing slideshows. "
        "Your goal is to run operations based on the user's intent. "
        "You can execute actions using tools. If the user asks to start a session, list populations, "
        "calibrate the RNG, stop automation, or tune settings, look up the appropriate tool and call it. "
        "Available tools include: list_populations, start_automation, stop_automation, get_automation_status, "
        "create_rng_session, get_rng_reading, forge_sigil, cast_tarot_spread, cast_i_ching, "
        "play_chakra_healing_audio, generate_single_outlook, and many more. "
        "Do not explain the tools, just call them. Once you receive the tool results, explain the outcome "
        "with deep compassion and wisdom, invoking the digital dharma theme."
    )
    context_request = ContextRequest(
        include_astrology=bool(request.include_astrology),
        include_anatomy=bool(request.include_anatomy),
        include_hardware=bool(request.include_hardware),
        astrology_data=request.astrology_data,
    )
    builder = SystemPromptBuilder()
    builder.register(AstrologyContextModule())
    builder.register(AnatomyContextModule())
    builder.register(HardwareContextModule())
    try:
        # SystemPromptBuilder.compose() now accepts base_prompt directly,
        # so we don't need to concatenate here. The builder returns
        # `base_prompt + "\n\n" + <rendered sections>` when sections exist.
        composed = await builder.compose(context_request, base_prompt=base_prompt)
    except Exception as exc:  # noqa: BLE001 — context failure must not break chat
        logger.warning("SystemPromptBuilder compose failed: %s", exc)
        composed = base_prompt

    if request.use_rag:
        rag_block = _build_rag_context_block(request)
        if rag_block:
            composed = f"{composed}\n\n{rag_block}"
    return composed


def _build_rag_context_block(request: ChatRequest) -> str:
    """Search the knowledge index for the latest user query and return a
    formatted "Relevant knowledge:" block, or '' if nothing matched.
    """
    try:
        from core.knowledge_index import get_knowledge_index
    except ImportError:
        return ""
    user_query = next(
        (m.content for m in reversed(request.messages) if m.role == "user"),
        None,
    )
    if not user_query:
        return ""
    try:
        idx = get_knowledge_index()
        results = idx.search(user_query, top_k=3)
    except Exception:  # noqa: BLE001 — RAG must never block chat
        logger.debug("RAG retrieval failed", exc_info=True)
        return ""
    if not results:
        return ""
    lines = ["Relevant knowledge (from the Vajra.Stream knowledge base):"]
    for r in results:
        source = r.get("source", "?")
        text = r.get("text", "").strip().replace("\n", " ")
        if len(text) > 400:
            text = text[:397] + "..."
        lines.append(f"- [{source}] {text}")
    return "\n".join(lines)


async def _select_provider_via_registry(http_request: Request, requested_provider: str) -> str | None:
    """Consult :meth:`ProviderRegistry.pick_best` to resolve ``"auto"``.

    Returns the chosen provider name (e.g. ``"openrouter"``, ``"lm_studio"``), or
    ``None`` when the registry is unavailable / empty / unhealthy.  Explicit
    (non-``"auto"``) requests are honoured only when the named provider is
    actually registered and currently healthy; otherwise ``None`` is returned so
    the caller falls through to env-var based detection.
    """
    registry = getattr(http_request.app.state, "llm_registry", None)
    if registry is None or len(registry) == 0:
        return None

    if requested_provider and requested_provider != "auto":
        if requested_provider not in registry:
            return None
        try:
            statuses = await registry.health_check_all()
        except Exception as exc:  # noqa: BLE001
            logger.warning("registry health check failed: %s", exc)
            return None
        if any(s.provider == requested_provider and s.healthy for s in statuses):
            return requested_provider
        return None

    try:
        best = await retry_with_backoff(
            lambda: registry.pick_best(),
            max_retries=1,
            initial_backoff=0.5,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ProviderRegistry.pick_best failed: %s", exc)
        return None
    return best.name if best is not None else None


def _build_openai_tools(tool_schemas: list[dict]) -> list[dict]:
    """Convert internal tool schemas into OpenAI function-tool descriptors."""
    return [
        {
            "type": "function",
            "function": {
                "name": s["name"],
                "description": s["description"],
                "parameters": s["parameters"],
            },
        }
        for s in tool_schemas
    ]


def _record_llm_usage(
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    endpoint: str = "chat",
    success: bool = True,
) -> None:
    """Best-effort LLM usage recording for raw-client call paths.

    Used by the tool-calling loops (which call ``client.chat.completions.create``
    directly with a sync ``openai.OpenAI`` / ``anthropic.Anthropic`` client
    rather than going through the provider class). The provider-class path
    (``OpenAICompatibleProvider.generate`` / ``AnthropicProvider.generate``)
    records itself, so registry-routed calls do not call this helper — that
    keeps the JSONL audit log free of duplicates.
    """
    try:
        tracker = LLMUsageTracker.get()
        tracker.record(
            UsageRecord(
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens or 0,
                completion_tokens=completion_tokens or 0,
                total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
                latency_ms=latency_ms,
                endpoint=endpoint,
                success=success,
            )
        )
    except Exception:  # noqa: BLE001 — tracker must never block an LLM call
        logger.debug("LLMUsageTracker.record failed", exc_info=True)


async def _run_openai_compatible_tool_loop(
    *,
    client: Any,
    model_name: str,
    messages: list[dict],
    tools: list[dict],
    tool_logs: list[ToolCallLog],
    max_turns: int = 5,
    provider_label: str = "provider",
    create_kwargs: dict | None = None,
) -> str:
    """Run the chat-completions tool-calling loop for any OpenAI-compatible client.

    Unifies the 5 previously copy-pasted loops (OpenAI, OpenRouter, DeepSeek,
    MiniMax, LM Studio).  Returns the final assistant text — either the model's
    terminal message or a ``"*(... reached maximum reasoning turns ...)*"``
    notice when the loop exhausts ``max_turns``.
    """
    extra_kwargs = create_kwargs or {}
    for turn in range(max_turns):
        logger.info(f"{provider_label} turn {turn} with model {model_name}...")
        turn_start = time.time()
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto" if tools else None,
            temperature=0.7,
            **extra_kwargs,
        )
        try:
            _turn_latency = (time.time() - turn_start) * 1000.0
            _usage = getattr(response, "usage", None)
            _record_llm_usage(
                provider=provider_label.lower().replace(" ", "_"),
                model=model_name,
                prompt_tokens=getattr(_usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(_usage, "completion_tokens", 0) or 0,
                latency_ms=_turn_latency,
            )
        except Exception:  # noqa: BLE001
            logger.debug("usage record failed in openai tool loop", exc_info=True)

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            text_tool_calls = _parse_text_tool_calls(msg.content or "")
            if text_tool_calls:
                logger.info(f"{provider_label}: parsed {len(text_tool_calls)} tool call(s) from text output")
                for tc_text in text_tool_calls:
                    name = _resolve_tool_name(tc_text["name"])
                    args = tc_text["arguments"]
                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        messages.append(
                            {
                                "role": "user",
                                "content": f"[Tool result for {name}]: {json.dumps(result)[:2000]}",
                            }
                        )
                    except Exception as ex:
                        logger.error(f"Error executing text-parsed tool {name}: {ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        messages.append(
                            {
                                "role": "user",
                                "content": f"[Tool error for {name}]: {ex}",
                            }
                        )

                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.7,
                    **extra_kwargs,
                )
                final_msg = response.choices[0].message
                return final_msg.content or ""

            return msg.content or ""

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except Exception as json_err:  # noqa: BLE001
                logger.error(f"{provider_label} returned malformed tool args: {json_err}")
                args = {}
            try:
                result = await execute_tool_locally(name, args)
                tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": json.dumps(result),
                    }
                )
            except Exception as ex:
                logger.error(f"Error executing {provider_label} tool {name}: {ex}")
                try:
                    log_failed_tool_call(
                        FailedToolCallSchema(
                            tool_name=name,
                            arguments=json.dumps(args),
                            error_message=str(ex),
                        )
                    )
                except Exception as log_ex:  # noqa: BLE001
                    logger.error(f"Failed to log tool failure to DB: {log_ex}")
                tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": json.dumps({"error": str(ex)}),
                    }
                )

    return f"*({provider_label} reached maximum reasoning turns without finishing.)*"


async def _run_anthropic_tool_loop(
    *,
    client: Any,
    model_name: str,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    tool_logs: list[ToolCallLog],
    max_turns: int = 5,
) -> str:
    """Run the Anthropic messages tool-calling loop (block-based content format)."""
    for turn in range(max_turns):
        logger.info(f"Anthropic turn {turn}...")
        turn_start = time.time()
        response = client.messages.create(
            model=model_name,
            system=system_prompt,
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=2000,
        )
        try:
            _turn_latency = (time.time() - turn_start) * 1000.0
            _usage = getattr(response, "usage", None)
            _record_llm_usage(
                provider="anthropic",
                model=model_name,
                prompt_tokens=getattr(_usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(_usage, "output_tokens", 0) or 0,
                latency_ms=_turn_latency,
            )
        except Exception:  # noqa: BLE001
            logger.debug("usage record failed in anthropic tool loop", exc_info=True)

        assistant_content: list[dict] = []
        tool_requests = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_requests.append(block)
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        messages.append({"role": "assistant", "content": assistant_content})

        if not tool_requests:
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results_content = []
        for tool_use in tool_requests:
            name = tool_use.name
            args = tool_use.input
            try:
                result = await execute_tool_locally(name, args)
                tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result),
                    }
                )
            except Exception as ex:
                logger.error(f"Error executing Anthropic tool {name}: {ex}")
                try:
                    log_failed_tool_call(
                        FailedToolCallSchema(
                            tool_name=name,
                            arguments=json.dumps(args),
                            error_message=str(ex),
                        )
                    )
                except Exception as log_ex:  # noqa: BLE001
                    logger.error(f"Failed to log tool failure to DB: {log_ex}")
                tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                tool_results_content.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps({"error": str(ex)}),
                    }
                )

        messages.append({"role": "user", "content": tool_results_content})

    return "*(Anthropic reached maximum reasoning turns without finishing.)*"


async def _chat_via_registry(
    http_request: Request,
    request: ChatRequest,
    provider_name: str,
    system_prompt_holder: list[str] | None = None,
) -> ChatResponse:
    """Registry-first chat path. Uses the registered provider for the request.

    The legacy code path (env-var lookups + copy-pasted tool loops) is preserved
    below as a fallback for deployments without an initialized registry or
    providers that aren't registered.

    ``system_prompt_holder`` is unused here (kept for signature symmetry with the
    fallback path); system prompt is built inside this function.
    """
    from core.llm.retry import retry_with_backoff

    registry = http_request.app.state.llm_registry
    # Build system prompt with context modules
    system_prompt = await _build_system_prompt_with_context(request)

    # Pick the requested provider from the registry (already verified `provider in registry`)
    chosen = None
    for p in registry.providers:
        if p.name == provider_name:
            chosen = p
            break
    if chosen is None:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider_name}' is registered but not selectable",
        )

    chat_request = request.model_copy(update={"system_prompt": system_prompt})

    async def _do_generate():
        return await chosen.generate(chat_request)

    try:
        response = await retry_with_backoff(_do_generate, max_retries=1, initial_backoff=0.5)
    except Exception as e:
        # Failover to next healthy provider
        chain = await registry.failover_chain()
        logger.info(
            "Provider %s failed (%s), trying failover chain of %d",
            provider_name,
            e,
            len(chain),
        )
        for next_provider in chain:
            if next_provider.name == provider_name:
                continue  # already tried
            try:
                response = await next_provider.generate(chat_request)
                logger.info("Failover succeeded via %s", next_provider.name)
                break
            except Exception as e2:
                logger.warning("Failover to %s failed: %s", next_provider.name, e2)
                continue
        else:
            raise HTTPException(
                status_code=503,
                detail=f"All providers failed. Primary: {e}",
            )

    # Convert the new core.llm.models.ChatResponse to the local ChatResponse
    # (which the endpoint advertises as response_model).
    clean_content, _ = strip_thinking(response.content)
    debug_info: dict | None = None
    if request.debug_mode:
        debug_info = {
            "provider": response.provider,
            "model": response.model,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "finish_reason": response.finish_reason,
        }
        if getattr(response, "reasoning_content", None):
            debug_info["reasoning_content"] = response.reasoning_content
        if getattr(response, "reasoning_tokens", 0):
            debug_info["reasoning_tokens"] = response.reasoning_tokens
    return ChatResponse(
        response=clean_content,
        tool_calls=[
            ToolCallLog(name=tc.get("name", ""), args=tc.get("arguments", {}), result="")
            for tc in (response.tool_calls or [])
        ],
        debug_info=debug_info,
    )


# ============================ Chat Endpoint ============================


def _provider_default_model(provider_class) -> str | None:
    """Read a provider class's declared ``default_model`` without instantiating it.

    Instantiating the provider class just to read the default would trigger
    HTTP-client construction and env-var validation. Introspecting the
    ``__init__`` signature is side-effect-free and tracks future changes to
    the provider's configured default automatically.
    """
    import inspect

    try:
        sig = inspect.signature(provider_class.__init__)
        param = sig.parameters.get("default_model")
        if param and param.default is not inspect.Parameter.empty:
            return param.default
    except Exception as e:
        logger.debug("Could not introspect default_model on %s: %s", provider_class, e)
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest, http_request: Request):
    """
    Chat with the AI Command Center to run magical computer operations.

    Routes through the new :class:`ProviderRegistry` +
    :class:`SystemPromptBuilder` pipeline with health-aware failover, then falls
    back to a rule-based local interpreter when no provider is reachable.  The
    six previously copy-pasted tool-calling loops are unified into
    :func:`_run_openai_compatible_tool_loop` (5 OpenAI-compatible providers) and
    :func:`_run_anthropic_tool_loop` (Anthropic block format).
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Message list cannot be empty")

    query = request.messages[-1].content
    provider = request.provider or "auto"

    # 1) Model-prefix hint wins over everything else (preserves legacy behaviour).
    if provider == "auto" and request.model:
        if request.model.startswith("lm_studio:"):
            provider = "lm_studio"
        elif request.model.startswith("local:"):
            provider = "local"

    # 2) Resolve 'auto' through the ProviderRegistry when one is available.
    if provider == "auto":
        registry_choice = await _select_provider_via_registry(http_request, "auto")
        if registry_choice:
            provider = registry_choice

    # 2b) NEW: If the registry has a healthy registered provider matching the
    # requested name, route through it. This is the new "registry-first" path
    # that bypasses the env-var lookups in the legacy branches below. The
    # legacy branches remain as a fallback for cases where the registry is
    # not initialized (e.g. older deployments) or no provider matched.
    registry = getattr(http_request.app.state, "llm_registry", None)
    if registry is not None and len(registry) > 0 and provider in registry:
        return await _chat_via_registry(http_request, request, provider, system_prompt_holder=None)

    # Retrieve key from request or env (used by the API-backed branches below).
    api_key = (
        request.api_key
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("MINIMAX_API_KEY")
    )
    tool_schemas = get_tool_schemas()
    openai_tools = _build_openai_tools(tool_schemas)
    claude_tools = [
        {"name": s["name"], "description": s["description"], "input_schema": s["parameters"]} for s in tool_schemas
    ]

    # 3) Build system prompt + composable context modules.
    system_prompt = await _build_system_prompt_with_context(request)

    tool_logs: list[ToolCallLog] = []

    # Prepare debug payload (only populated when explicitly requested).
    debug_payload = None
    if request.debug_mode:
        debug_payload = {
            "system_prompt": system_prompt,
            "messages_sent": [{"role": m.role, "content": m.content} for m in request.messages],
            "tools_available": [s["name"] for s in tool_schemas],
            "provider_selected": provider,
            "model_selected": request.model or "default",
            "timestamp": time.time(),
        }

    def wrap_res(res):
        if isinstance(res, str):
            res = ChatResponse(response=res, tool_logs=tool_logs)
        # Final safety net: strip any <think> blocks that slipped through
        # providers that bypass the registry path (raw openai/anthropic
        # clients in the legacy branches below).
        if res.response:
            cleaned, _reasoning = strip_thinking(res.response)
            res.response = cleaned
            if _reasoning and request.debug_mode:
                if res.debug_info is None:
                    res.debug_info = {}
                res.debug_info.setdefault("reasoning_content", _reasoning)
        if request.debug_mode:
            res.debug_info = debug_payload
        return res

    # 4) No credentials and no local provider → rule-based fallback.
    if not api_key and provider not in ("local", "lm_studio"):
        logger.info("No API keys found. Falling back to rule-based parser.")
        return wrap_res(await run_rule_based_fallback(query))

    full_system_prompt, chat_messages = format_messages_for_llm(request.messages, system_prompt)

    # 5) Route to the matching provider branch. Each branch constructs its client
    #    and delegates the tool-calling loop to one of the two unified helpers.
    try:
        # ---- OpenAI ----
        if api_key and (provider == "openai" or (provider == "auto" and os.getenv("OPENAI_API_KEY"))):
            import openai

            client = openai.OpenAI(api_key=api_key)
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
            from core.llm.providers.openai import OpenAIProvider

            response_text = await _run_openai_compatible_tool_loop(
                client=client,
                model_name=request.model or _provider_default_model(OpenAIProvider) or "gpt-4o-mini",
                messages=openai_messages,
                tools=openai_tools,
                tool_logs=tool_logs,
                provider_label="OpenAI",
            )
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

        # ---- OpenRouter ----
        if os.getenv("OPENROUTER_API_KEY") and (
            provider == "openrouter"
            or (provider == "auto" and not os.getenv("OPENAI_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"))
        ):
            import openai as openai_lib

            client = openai_lib.OpenAI(
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                timeout=float(os.getenv("OPENROUTER_TIMEOUT", "120")),
            )
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
            from core.llm.providers.openrouter import OpenRouterProvider

            model_name = (
                request.model
                or _provider_default_model(OpenRouterProvider)
                or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
            )
            response_text = await _run_openai_compatible_tool_loop(
                client=client,
                model_name=model_name,
                messages=openai_messages,
                tools=openai_tools,
                tool_logs=tool_logs,
                provider_label="OpenRouter",
            )
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

        # ---- LM Studio / Local GGUF ----
        if provider == "local" or provider == "lm_studio" or (provider == "auto" and not api_key):
            import openai as openai_lib

            base_url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234")
            timeout = float(os.getenv("LM_STUDIO_TIMEOUT", "300"))
            client = openai_lib.OpenAI(
                api_key="not-required",
                base_url=f"{base_url}/v1",
                timeout=timeout,
            )

            model_name = request.model
            if model_name and model_name.startswith("lm_studio:"):
                model_name = model_name.replace("lm_studio:", "", 1)

            if not model_name:
                try:
                    models_res = client.models.list()
                except Exception as models_err:
                    logger.error(f"Failed to fetch models from LM Studio: {models_err}")
                    raise HTTPException(
                        status_code=503,
                        detail="Cannot reach LM Studio. Ensure LM Studio is running with a model loaded.",
                    ) from models_err
                if not (models_res and models_res.data):
                    raise HTTPException(
                        status_code=503,
                        detail="No model is currently loaded in LM Studio. Please load a model in LM Studio first, then retry.",
                    )
                model_name = models_res.data[0].id
                logger.info(f"Dynamically detected loaded model: {model_name}")

            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
            try:
                response_text = await _run_openai_compatible_tool_loop(
                    client=client,
                    model_name=model_name,
                    messages=openai_messages,
                    tools=openai_tools,
                    tool_logs=tool_logs,
                    provider_label="LM Studio",
                    create_kwargs={"timeout": timeout},
                )
            except Exception as loop_err:
                err_str = str(loop_err).lower()
                if "timeout" in err_str or "timed out" in err_str or "timed-out" in err_str:
                    logger.error(f"LM Studio request timed out: {loop_err}")
                    fallback_res = await run_rule_based_fallback(query)
                    fallback_res.response = (
                        "*(LM Studio Request Timed Out - Switched to Local Interpreter)*\n\n" + fallback_res.response
                    )
                    return wrap_res(fallback_res)
                raise
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

        # ---- DeepSeek ----
        if api_key and (
            provider == "deepseek"
            or (provider == "auto" and os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"))
        ):
            import openai as openai_lib

            client = openai_lib.OpenAI(
                api_key=api_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            )
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
            from core.llm.providers.deepseek import DeepSeekProvider

            response_text = await _run_openai_compatible_tool_loop(
                client=client,
                model_name=request.model or _provider_default_model(DeepSeekProvider) or "deepseek-chat",
                messages=openai_messages,
                tools=openai_tools,
                tool_logs=tool_logs,
                provider_label="DeepSeek",
            )
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

        # ---- MiniMax ----
        if api_key and (
            provider == "minimax"
            or (
                provider == "auto"
                and os.getenv("MINIMAX_API_KEY")
                and not os.getenv("OPENAI_API_KEY")
                and not os.getenv("ANTHROPIC_API_KEY")
            )
        ):
            import openai as openai_lib

            client = openai_lib.OpenAI(
                api_key=api_key,
                base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
                timeout=float(os.getenv("MINIMAX_TIMEOUT", "120")),
            )
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
            from core.llm.providers.minimax import MinimaxProvider

            response_text = await _run_openai_compatible_tool_loop(
                client=client,
                model_name=request.model or _provider_default_model(MinimaxProvider) or "MiniMax-Text-01",
                messages=openai_messages,
                tools=openai_tools,
                tool_logs=tool_logs,
                provider_label="minimax",
            )
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

        # ---- Anthropic ----
        if api_key and (provider == "anthropic" or (provider == "auto" and os.getenv("ANTHROPIC_API_KEY"))):
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            from core.llm.providers.anthropic import AnthropicProvider

            response_text = await _run_anthropic_tool_loop(
                client=client,
                model_name=request.model or _provider_default_model(AnthropicProvider) or "claude-3-5-haiku-20241022",
                system_prompt=full_system_prompt,
                messages=chat_messages,
                tools=claude_tools,
                tool_logs=tool_logs,
            )
            return wrap_res(ChatResponse(response=response_text, tool_calls=tool_logs))

    except Exception as e:
        logger.error(f"{provider} execution failed: {e}. Trying fallback providers...")
        err_str = str(e).lower()

        if os.getenv("OPENROUTER_API_KEY") and provider != "openrouter":
            try:
                import openai as openai_lib

                or_client = openai_lib.OpenAI(
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    timeout=float(os.getenv("OPENROUTER_TIMEOUT", "120")),
                )
                or_model = request.model or os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
                or_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages
                logger.info(f"Falling back to OpenRouter with model {or_model}...")
                or_response = await _run_openai_compatible_tool_loop(
                    client=or_client,
                    model_name=or_model,
                    messages=or_messages,
                    tools=openai_tools,
                    tool_logs=tool_logs,
                    provider_label="OpenRouter",
                )
                return wrap_res(ChatResponse(response=or_response, tool_calls=tool_logs))
            except Exception as or_ex:
                logger.error(f"OpenRouter fallback also failed: {or_ex}")

        logger.info("All providers failed. Falling back to rule-based parser.")
        fallback_res = await run_rule_based_fallback(query)
        err_str = str(e).lower()
        if "timeout" in err_str or "timed out" in err_str:
            prefix = f"*({provider} Request Timed Out - Switched to Local Interpreter)*"
        elif "connection" in err_str or "refused" in err_str or "name resolution" in err_str:
            prefix = f"*({provider} Not Reachable - Switched to Local Interpreter)*"
        elif "jinja" in err_str or "no user query" in err_str or "prompt template" in err_str:
            prefix = f"*({provider} Prompt Template Error - Check model prompt template settings)*"
        else:
            prefix = f"*({provider} Call Failed: {str(e)[:100]} - Switched to Local Interpreter)*"
        fallback_res.response = f"{prefix}\n\n" + fallback_res.response
        return wrap_res(fallback_res)

    # 6) Default fallback when no branch matched.
    return wrap_res(await run_rule_based_fallback(query))


@router.post("/teach", response_model=ChatResponse)
async def teach_interaction(request: ChatRequest, http_request: Request):
    """Clean LLM endpoint for educational use — no operator prompt, no tools.

    Unlike ``/chat``, this endpoint passes the caller's system message
    directly to the LLM without prepending the operator base prompt or
    exposing operator tool schemas. Used by the Esoteric Tutor.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Message list cannot be empty")

    system_parts = [m.content for m in request.messages if m.role == "system"]
    system_prompt = "\n\n".join(system_parts) if system_parts else "You are a helpful teacher."
    chat_msgs = [m for m in request.messages if m.role != "system"]
    if not chat_msgs:
        raise HTTPException(status_code=400, detail="No user/assistant messages found")

    registry = getattr(http_request.app.state, "llm_registry", None)
    if not registry:
        raise HTTPException(status_code=503, detail="LLM registry not initialized")

    provider_name = await _select_provider_via_registry(http_request, request.provider or "auto")
    if not provider_name:
        provider_name = registry.providers[0].name if registry.providers else None
    if not provider_name:
        raise HTTPException(status_code=503, detail="No LLM providers available")

    chosen = None
    for p in registry.providers:
        if p.name == provider_name:
            chosen = p
            break
    if chosen is None:
        raise HTTPException(status_code=503, detail=f"Provider '{provider_name}' not selectable")

    from core.llm.models import ChatRequest as CoreChatRequest

    core_request = CoreChatRequest(
        messages=[{"role": m.role, "content": m.content} for m in chat_msgs],
        system_prompt=system_prompt,
        max_tokens=request.max_tokens or 1200,
        temperature=request.temperature or 0.7,
        model=request.model,
        stream=False,
        tools=[],
    )

    try:
        response = await retry_with_backoff(lambda: chosen.generate(core_request), max_retries=1, initial_backoff=0.5)
    except Exception as e:
        chain = await registry.failover_chain()
        for next_provider in chain:
            if next_provider.name == provider_name:
                continue
            try:
                response = await next_provider.generate(core_request)
                logger.info("Teach failover succeeded via %s", next_provider.name)
                break
            except Exception as e2:
                logger.warning("Teach failover to %s failed: %s", next_provider.name, e2)
                continue
        else:
            raise HTTPException(status_code=503, detail=f"All providers failed. Primary: {e}")

    clean_content, _ = strip_thinking(response.content)
    return ChatResponse(response=clean_content, tool_calls=[])


@router.get("/usage/summary")
async def get_usage_summary() -> dict:
    """Return the cumulative LLM usage summary.

    Totals (calls, tokens, cost), per-provider breakdown, daily cost vs cap,
    and the last 50 in-memory records. The JSONL log file on disk is the
    authoritative audit trail; this endpoint is the live view.
    """
    tracker = LLMUsageTracker.get()
    return tracker.get_summary()


@router.get("/usage/recent")
async def get_recent_usage(limit: int = 50) -> dict:
    """Return the most recent LLM calls (default 50, max 1000 in memory)."""
    tracker = LLMUsageTracker.get()
    records = tracker.recent_calls[-limit:]
    return {
        "calls": [
            {
                "timestamp": r.timestamp,
                "provider": r.provider,
                "model": r.model,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "endpoint": r.endpoint,
                "success": r.success,
            }
            for r in records
        ],
        "count": len(records),
    }


@router.get("/usage/reset")
async def reset_usage() -> dict:
    """Clear in-memory usage counters and records.

    The JSONL log file on disk is preserved for audit. Useful for testing
    and for starting a fresh accounting window without restarting the server.
    """
    tracker = LLMUsageTracker.get()
    tracker.reset()
    return {"status": "reset"}


@router.get("/models", summary="List available LLM models")
async def list_models():
    """List available local GGUF models and API configurations."""
    try:
        from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration

        llm = LLMIntegration(model_type="auto")
        available = llm.list_available_models()

        # Check active/loaded models in LM Studio via direct HTTP request
        import json as json_mod
        import urllib.error
        import urllib.request

        lm_studio_models = []
        lm_studio_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234")
        try:
            req = urllib.request.Request(f"{lm_studio_url}/v1/models")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                models_data = json_mod.loads(response.read().decode())
                lm_studio_models = [m["id"] for m in models_data.get("data", [])]
        except Exception:
            pass

        # Determine the default selected model — prefer loaded LM Studio model
        default_model = ""
        if lm_studio_models:
            default_model = f"lm_studio:{lm_studio_models[0]}"
        elif available.get("local"):
            default_model = f"local:{available['local'][0]}"

        return {
            "status": "success",
            "available": {
                "local": [f"local:{m}" for m in available.get("local", [])],
                "api": available.get("api", []),
                "lm_studio": lm_studio_models,
            },
            "default_model": default_model,
            "lm_studio_connected": len(lm_studio_models) > 0 or default_model != "",
        }
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return {
            "status": "success",
            "available": {"local": [], "api": [], "lm_studio": []},
            "default_model": "",
            "lm_studio_connected": False,
        }


@router.get("/providers/health")
async def get_providers_health(request: Request) -> dict:
    """Return current health status for all registered providers."""
    registry = getattr(request.app.state, "llm_registry", None)
    if registry is None or len(registry) == 0:
        return {
            "providers": [],
            "healthy_count": 0,
            "total_count": 0,
            "message": "LLM registry not initialized",
        }
    statuses = await registry.health_check_all()
    return {
        "providers": [s.model_dump() for s in statuses],
        "healthy_count": sum(1 for s in statuses if s.healthy),
        "total_count": len(statuses),
    }


# ============================ Model Discovery & Management ============================
# Endpoints added under /api/v1/llm/models/* — dynamic OpenRouter discovery
# (cached 5 min), user-saved custom model registry, and a fast test probe.

# In-memory cache for the OpenRouter /models response. Held at module scope so
# all worker tasks share it. The lock is created lazily inside the handler so
# constructing it does not require a running event loop on import (Windows).
_AVAILABLE_MODELS_CACHE: dict[str, Any] = {"fetched_at": 0.0, "models": [], "source": ""}
_AVAILABLE_MODELS_TTL_SECONDS: float = 300.0  # 5 minutes
_AVAILABLE_MODELS_LOCK: asyncio.Lock | None = None


def _get_available_models_lock() -> asyncio.Lock:
    """Lazy-init the module-level asyncio.Lock for the discovery cache.

    ``asyncio.Lock()`` must be created inside a running loop on Windows;
    constructing it at import time raises ``RuntimeError`` under some
    ProactorEventLoop configurations.
    """
    global _AVAILABLE_MODELS_LOCK
    if _AVAILABLE_MODELS_LOCK is None:
        _AVAILABLE_MODELS_LOCK = asyncio.Lock()
    return _AVAILABLE_MODELS_LOCK


# Path to the user's saved custom model list (JSON file in the home dir).
CUSTOM_MODELS_PATH: Path = Path.home() / ".vajra-stream" / "custom_models.json"

# OpenRouter public catalogue URL. No API key required for read.
OPENROUTER_MODELS_URL: str = "https://openrouter.ai/api/v1/models"

# OpenRouter chat-completions URL used by the test probe.
OPENROUTER_CHAT_URL: str = "https://openrouter.ai/api/v1/chat/completions"

# Probe prompt sent by POST /models/{id}/test. Kept tiny so the test
# is fast and ~free even on paid models.
_TEST_PROBE_PROMPT: str = "Say 'Hello' in one word."


class AvailableModel(BaseModel):
    """A single model entry returned by ``GET /models/available``.

    Fields are a normalized subset of the OpenRouter /models payload,
    enriched with a ``featured`` flag for the curated built-in set and
    a ``source`` indicating where the entry came from.
    """

    id: str
    name: str
    provider: str
    context_length: int | None = None
    input_per_m: float = 0.0
    output_per_m: float = 0.0
    is_free: bool = False
    featured: bool = False
    description: str = ""
    source: str = "openrouter"  # 'openrouter' | 'lm_studio' | 'local_gguf'


class AddCustomModelRequest(BaseModel):
    """Request body for ``POST /models/add``."""

    model_id: str
    display_name: str
    provider: str = "openrouter"


class SavedCustomModel(BaseModel):
    """An entry persisted in ``~/.vajra-stream/custom_models.json``."""

    model_id: str
    display_name: str
    provider: str
    added_at: str  # ISO-8601 timestamp


def _load_custom_models() -> list[dict]:
    """Load the user's saved custom models from disk.

    Returns an empty list if the file does not exist or is corrupt
    (a warning is logged on parse failure; the file is left untouched).
    """
    try:
        if CUSTOM_MODELS_PATH.exists():
            raw = CUSTOM_MODELS_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return [m for m in data if isinstance(m, dict)]
            if isinstance(data, dict) and isinstance(data.get("models"), list):
                return [m for m in data["models"] if isinstance(m, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read custom models file %s: %s", CUSTOM_MODELS_PATH, exc)
    return []


def _save_custom_models(models: list[dict]) -> None:
    """Persist the custom-model list to disk, creating the parent dir."""
    try:
        CUSTOM_MODELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CUSTOM_MODELS_PATH.write_text(
            json.dumps(models, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to write custom models file %s: %s", CUSTOM_MODELS_PATH, exc)
        raise


def _detect_provider(model_id: str) -> str:
    """Best-effort provider extraction from a model id prefix.

    OpenRouter model ids look like ``vendor/model-name``. We take the
    first slash-separated segment. Falls back to ``"openrouter"`` for
    unscoped ids.
    """
    if "/" in model_id:
        return model_id.split("/", 1)[0].lower()
    return "openrouter"


async def _fetch_openrouter_models_uncached() -> list[dict]:
    """Hit ``GET https://openrouter.ai/api/v1/models`` and normalize rows.

    Returns an empty list on any failure (timeout, HTTP error, parse
    error) — the caller surfaces a graceful "no models" state rather
    than a 5xx. Requires ``aiohttp``; if it is not installed, returns
    ``[]`` immediately.
    """
    if aiohttp is None:
        logger.warning("aiohttp not installed — OpenRouter model discovery unavailable")
        return []
    try:
        timeout = aiohttp.ClientTimeout(total=10.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(OPENROUTER_MODELS_URL) as resp:
                if resp.status != 200:
                    logger.warning("OpenRouter /models returned HTTP %s", resp.status)
                    return []
                payload = await resp.json()
    except Exception as exc:  # noqa: BLE001 — discovery must never 5xx
        logger.warning("OpenRouter /models fetch failed: %s", exc)
        return []

    rows = payload.get("data", []) if isinstance(payload, dict) else []
    featured_set = set(KNOWN_FEATURED_MODEL_IDS)
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = row.get("id") or ""
        if not model_id:
            continue
        pricing = row.get("pricing") or {}
        try:
            prompt_per_token = float(pricing.get("prompt") or "0")
            completion_per_token = float(pricing.get("completion") or "0")
        except (TypeError, ValueError):
            prompt_per_token = 0.0
            completion_per_token = 0.0
        input_per_m = prompt_per_token * 1_000_000.0
        output_per_m = completion_per_token * 1_000_000.0
        is_free = input_per_m == 0.0 and output_per_m == 0.0
        try:
            ctx_len = int(row.get("context_length") or 0) or None
        except (TypeError, ValueError):
            ctx_len = None
        out.append(
            {
                "id": model_id,
                "name": row.get("name") or model_id,
                "provider": _detect_provider(model_id),
                "context_length": ctx_len,
                "input_per_m": input_per_m,
                "output_per_m": output_per_m,
                "is_free": is_free,
                "featured": model_id in featured_set,
                "description": (row.get("description") or "")[:500],
                "source": "openrouter",
            }
        )
    return out


async def _fetch_lm_studio_models_uncached() -> list[dict]:
    """Best-effort list of locally-loaded LM Studio models.

    Returns ``[]`` if LM Studio is not running or unreachable; never
    raises. Uses urllib (sync) wrapped in a thread so it does not
    block the event loop and does not add an aiohttp dependency for
    this optional local probe.
    """
    import urllib.error
    import urllib.request

    base_url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234").rstrip("/")

    def _do_fetch() -> list[dict]:
        try:
            req = urllib.request.Request(f"{base_url}/v1/models")
            with urllib.request.urlopen(req, timeout=1.5) as response:  # noqa: S310 — local
                data = json.loads(response.read().decode())
            out: list[dict] = []
            for m in data.get("data", []):
                mid = m.get("id") or ""
                if not mid:
                    continue
                out.append(
                    {
                        "id": f"lm_studio:{mid}",
                        "name": mid,
                        "provider": "lm_studio",
                        "context_length": m.get("context_length"),
                        "input_per_m": 0.0,
                        "output_per_m": 0.0,
                        "is_free": True,
                        "featured": False,
                        "description": "Locally hosted via LM Studio",
                        "source": "lm_studio",
                    }
                )
            return out
        except Exception:  # noqa: BLE001 — LM Studio probe must be silent
            return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _do_fetch)


@router.get("/models/available", summary="List all available OpenRouter models")
async def list_available_models() -> dict:
    """Return the full OpenRouter model catalogue (cached 5 minutes).

    Merges:
      1. OpenRouter public /models response (300+ entries) — cached for
         ``_AVAILABLE_MODELS_TTL_SECONDS`` so we never hit OpenRouter on
         every page load.
      2. Locally-loaded LM Studio models (no cache; probed every call).

    Each entry is normalized to the :class:`AvailableModel` shape and
    tagged with ``featured=True`` if it appears in
    :data:`core.llm.defaults.KNOWN_FEATURED_MODEL_IDS`. The Nemotron
    free model is always included even if OpenRouter omits it.
    """
    global _AVAILABLE_MODELS_CACHE
    lock = _get_available_models_lock()
    async with lock:
        now = time.time()
        cached = _AVAILABLE_MODELS_CACHE
        needs_refresh = (now - cached.get("fetched_at", 0.0)) > _AVAILABLE_MODELS_TTL_SECONDS
        or_models: list[dict] = []
        if needs_refresh:
            or_models = await _fetch_openrouter_models_uncached()
            if or_models:
                cached["fetched_at"] = now
                cached["models"] = or_models
                cached["source"] = "openrouter"
            else:
                # Keep stale cache if we have one; otherwise seed with the
                # built-in featured set so the UI is never empty.
                if not cached.get("models"):
                    set(KNOWN_FEATURED_MODEL_IDS)
                    cached["models"] = [
                        {
                            "id": mid,
                            "name": mid.split("/")[-1],
                            "provider": _detect_provider(mid),
                            "context_length": None,
                            "input_per_m": 0.0,
                            "output_per_m": 0.0,
                            "is_free": mid.endswith(":free"),
                            "featured": True,
                            "description": "Built-in featured model",
                            "source": "builtin",
                        }
                        for mid in KNOWN_FEATURED_MODEL_IDS
                    ]
                    cached["source"] = "builtin"
        or_models = list(cached.get("models", []))

    # Merge LM Studio models (always probed; cheap and local).
    lm_models = await _fetch_lm_studio_models_uncached()

    # Defensive: ensure Nemotron is always present even if OpenRouter
    # transiently drops it from the catalogue.
    if not any(m.get("id") == NEMOTRON_FREE_MODEL_ID for m in or_models):
        or_models.insert(
            0,
            {
                "id": NEMOTRON_FREE_MODEL_ID,
                "name": "Nemotron 3 Ultra 550B (Free)",
                "provider": "nvidia",
                "context_length": 1_000_000,
                "input_per_m": 0.0,
                "output_per_m": 0.0,
                "is_free": True,
                "featured": True,
                "description": "550B MoE, 1M context, $0 input / $0 output. Built-in default.",
                "source": "builtin",
            },
        )

    # Validate rows against the Pydantic model for a stable contract.
    validated: list[dict] = []
    for m in or_models + lm_models:
        try:
            validated.append(AvailableModel(**m).model_dump())
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipping malformed available-model row %r: %s", m, exc)

    return {
        "status": "success",
        "count": len(validated),
        "fetched_at": cached.get("fetched_at"),
        "source": cached.get("source", ""),
        "models": validated,
    }


@router.get("/models/saved", summary="List user-saved custom models")
async def list_saved_models() -> dict:
    """Return the user's saved-model list from ``~/.vajra-stream/custom_models.json``."""
    models = _load_custom_models()
    # Normalize each row before returning.
    out: list[dict] = []
    for m in models:
        try:
            out.append(
                SavedCustomModel(
                    model_id=str(m.get("model_id", "")),
                    display_name=str(m.get("display_name", "")),
                    provider=str(m.get("provider", "openrouter")),
                    added_at=str(m.get("added_at", "")),
                ).model_dump()
            )
        except Exception:  # noqa: BLE001
            continue
    return {"status": "success", "count": len(out), "models": out}


@router.post("/models/add", summary="Add a custom model to the saved list")
async def add_custom_model(req: AddCustomModelRequest) -> dict:
    """Add ``model_id`` to the user's saved custom model list.

    Persisted to ``~/.vajra-stream/custom_models.json`` (file is created
    if missing). Adding the same ``model_id`` twice updates the display
    name and provider in place rather than creating a duplicate.
    """
    model_id = req.model_id.strip()
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")
    provider = (req.provider or _detect_provider(model_id)).strip() or "openrouter"
    display_name = (req.display_name or model_id).strip()

    models = _load_custom_models()
    added_at = _now_iso()
    for m in models:
        if m.get("model_id") == model_id:
            m["display_name"] = display_name
            m["provider"] = provider
            m["added_at"] = added_at
            _save_custom_models(models)
            return {"status": "updated", "model": m}
    entry = {
        "model_id": model_id,
        "display_name": display_name,
        "provider": provider,
        "added_at": added_at,
    }
    models.append(entry)
    _save_custom_models(models)
    return {"status": "added", "model": entry}


@router.delete("/models/{model_id:path}", summary="Remove a saved custom model")
async def delete_custom_model(model_id: str) -> dict:
    """Remove ``model_id`` from the saved custom model list.

    Silently succeeds (``status: "not_found"``) if the model was not in
    the saved list — DELETE should be idempotent.
    """
    models = _load_custom_models()
    before = len(models)
    models = [m for m in models if m.get("model_id") != model_id]
    if len(models) == before:
        return {"status": "not_found", "model_id": model_id}
    _save_custom_models(models)
    return {"status": "deleted", "model_id": model_id}


class ModelTestResponse(BaseModel):
    """Result of a single model probe."""

    success: bool
    response: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_estimate: float = 0.0
    error: str = ""


@router.post(
    "/models/{model_id:path}/test",
    summary="Send a tiny probe prompt to a model and report latency + cost",
    response_model=ModelTestResponse,
)
async def test_model(model_id: str) -> ModelTestResponse:
    """Send ``"Say 'Hello' in one word."`` to ``model_id`` and report.

    Uses the OpenRouter chat-completions endpoint with a hard 15-second
    timeout. Cost is estimated via :class:`LLMUsageTracker` using the
    per-model pricing table. Returns a 200 with ``success: false`` on
    any failure (timeout, missing key, HTTP error) so the frontend can
    render the error inline without a 5xx.
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return ModelTestResponse(
            success=False,
            error="OPENROUTER_API_KEY not set — cannot probe remote models.",
        )
    if aiohttp is None:
        return ModelTestResponse(
            success=False,
            error="aiohttp not installed — model probe unavailable.",
        )

    started = time.time()
    try:
        async with asyncio.timeout(15.0):
            timeout = aiohttp.ClientTimeout(total=15.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    OPENROUTER_CHAT_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": _TEST_PROBE_PROMPT}],
                        "max_tokens": 16,
                    },
                ) as resp:
                    latency_ms = (time.time() - started) * 1000.0
                    body = await resp.json()
                    if resp.status >= 400:
                        err_msg = (
                            body.get("error", {}).get("message") if isinstance(body, dict) else f"HTTP {resp.status}"
                        ) or f"HTTP {resp.status}"
                        return ModelTestResponse(
                            success=False,
                            latency_ms=latency_ms,
                            error=str(err_msg)[:300],
                        )
                    choices = body.get("choices") or []
                    text = ""
                    if choices and isinstance(choices[0], dict):
                        msg = choices[0].get("message") or {}
                        text = str(msg.get("content") or "").strip()
                    usage = body.get("usage") or {}
                    prompt_toks = int(usage.get("prompt_tokens") or 0)
                    completion_toks = int(usage.get("completion_tokens") or 0)
                    total_toks = prompt_toks + completion_toks
                    cost = LLMUsageTracker.get().estimate_cost("openrouter", model_id, prompt_toks, completion_toks)
                    # Record the probe so the usage dashboard reflects it.
                    _record_llm_usage(
                        provider="openrouter",
                        model=model_id,
                        prompt_tokens=prompt_toks,
                        completion_tokens=completion_toks,
                        latency_ms=latency_ms,
                        endpoint="model_test",
                    )
                    return ModelTestResponse(
                        success=True,
                        response=text,
                        latency_ms=latency_ms,
                        tokens_used=total_toks,
                        cost_estimate=cost,
                    )
    except asyncio.TimeoutError:
        return ModelTestResponse(
            success=False,
            latency_ms=(time.time() - started) * 1000.0,
            error="Probe timed out after 15s.",
        )
    except Exception as exc:  # noqa: BLE001
        return ModelTestResponse(
            success=False,
            latency_ms=(time.time() - started) * 1000.0,
            error=f"Probe failed: {exc}"[:300],
        )


@router.get("/models/defaults", summary="Return the recommended default model per use case")
async def get_default_models() -> dict:
    """Expose :data:`core.llm.defaults.DEFAULT_MODELS_BY_USE_CASE` to the UI.

    Used by the Model Manager's "Active Model Display" section so the
    recommended default for each feature (outlook, chat, blessing loop,
    operator, divination, TTS) is rendered from a single source of truth.
    """
    return {
        "status": "success",
        "defaults": DEFAULT_MODELS_BY_USE_CASE,
    }


def _now_iso() -> str:
    """ISO-8601 UTC timestamp for persisted ``added_at`` fields."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
