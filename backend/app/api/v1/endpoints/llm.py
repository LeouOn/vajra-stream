"""
LLM Agent API Endpoints
Provides chat-based interface with tool calling and rule-based local fallback.
"""

import json
import logging
import os
import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    import aiohttp
except ImportError:
    aiohttp = None

from backend.core.llm_agent.tools import TOOL_REGISTRY, get_tool_schemas
from backend.core.services.blessing_scheduler import get_scheduler
from backend.core.services.population_manager import get_population_manager
from backend.core.services.rng_attunement_service import get_rng_service
from backend.app.api.v1.endpoints.agent_suggestions import log_failed_tool_call, FailedToolCallSchema

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    api_key: str | None = None
    provider: str | None = "auto"  # 'openai', 'anthropic', 'local', 'auto'
    model: str | None = None
    include_astrology: bool | None = False
    include_anatomy: bool | None = False
    include_hardware: bool | None = False
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


async def execute_tool_locally(name: str, args: dict) -> Any:
    """Helper to execute a tool function from the tool registry"""
    if name not in TOOL_REGISTRY:
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
                "name_chinese": b.name_chinese, "name_pinyin": b.name_pinyin,
                "name_sanskrit": b.name_sanskrit, "category": b.category,
                "meaning": b.meaning, "realm": b.realm, "light": b.light,
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
        return {"buddha": b.name_chinese, "pinyin": b.name_pinyin,
                "message": f"Recitation of {b.name_chinese} ({b.name_pinyin}) would play via Edge TTS."}
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
                running_loop.create_task(loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles))
            else:
                asyncio.run(loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles))
        except RuntimeError:
            asyncio.run(loop.start(intention=intention, interval_seconds=interval, mala_cycles=mala_cycles))
        return loop.get_status()
    elif name == "stop_buddha_recitation":
        from core.buddha_recitation_loop import get_recitation_loop
        loop = get_recitation_loop()
        loop.stop()
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
            "in_saka_dawa_window": in_window, "current_month": now.month,
            "practice": {"id": saka_dawa.id, "name": saka_dawa.name, "genre": saka_dawa.genre,
                         "merit_multiplier": saka_dawa.merit_multiplier,
                         "blessing_prompt": saka_dawa.base_prompt_template},
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
    elif name == "start_character_journey" or name == "advance_journey" or name == "get_journey_status" or name == "run_full_journey":
        from modules.radionics_operator import ToolDispatcher
        from container import container
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


async def compile_astrology_context(astro_data: dict = None) -> str:
    try:
        if not astro_data:
            from backend.core.services.vajra_service import vajra_service

            astro_data = await vajra_service._get_astrology_data()

        if not astro_data:
            return ""

        # Extract planetary hours context
        planetary_hours = astro_data.get("planetary_hours", {})
        if not planetary_hours:
            # Fallback to legacy/top-level keys if any
            planetary_hours = {
                "current_planetary_hour": astro_data.get("planetary_hour", "N/A"),
                "day_planet": astro_data.get("day_planet", "N/A"),
                "day_of_week": astro_data.get("day_of_week", "N/A"),
            }

        moon = astro_data.get("moon_phase") or {}

        # Resolve solar term/jieqi
        solar_term = "N/A"
        if isinstance(astro_data.get("solar_terms"), dict):
            solar_term = astro_data.get("solar_terms").get("current_term", "N/A")
        elif astro_data.get("solar_term"):
            solar_term = astro_data.get("solar_term")
        elif isinstance(astro_data.get("chinese"), dict):
            solar_term = astro_data.get("chinese").get("solar_term", "N/A")

        lines = [
            "### 🔮 COSMIC CLOCKWORK SYSTEM",
            f"- **Datetime (Local)**: {astro_data.get('datetime', 'N/A')}",
            f"- **Location (Geocentric)**: Lat: {astro_data.get('location', {}).get('latitude', 'N/A') if isinstance(astro_data.get('location'), dict) else 'N/A'}, Lon: {astro_data.get('location', {}).get('longitude', 'N/A') if isinstance(astro_data.get('location'), dict) else 'N/A'}",
            f"- **Planetary Hour**: {planetary_hours.get('current_planetary_hour', 'N/A')}",
            f"- **Day Ruler**: {planetary_hours.get('day_planet', 'N/A')} ({planetary_hours.get('day_of_week', 'N/A')})",
            f"- **Moon Phase**: {moon.get('phase_name', 'N/A')} (Illumination: {moon.get('illumination', 0.0):.1f}%, Angle: {moon.get('phase_angle', 0.0):.1f}°)",
            f"- **Solar Term (Jie Qi)**: {solar_term}",
            "",
        ]

        # -------------------------------------------------------------
        # I. Western Tropical Astrology
        # -------------------------------------------------------------
        western = astro_data.get("western", {})
        if western:
            lines.append("#### I. Western Tropical Astrology (Transit Wheel & Aspects)")
            positions = western.get("positions", {})
            if positions:
                # Highlight Big Three (Sun, Moon, Ascendant)
                sun_info = positions.get("sun", {})
                moon_info = positions.get("moon", {})
                asc_info = positions.get("ascendant", {})

                lines.append(
                    f"- **☀️ Sun**: {sun_info.get('sign', 'N/A')} {sun_info.get('degree', 0.0):.2f}° ({sun_info.get('house', 'N/A')} House)"
                )
                lines.append(
                    f"- **🌙 Moon**: {moon_info.get('sign', 'N/A')} {moon_info.get('degree', 0.0):.2f}° ({moon_info.get('house', 'N/A')} House)"
                )
                lines.append(
                    f"- **🏹 Ascendant (Rising)**: {asc_info.get('sign', 'N/A')} {asc_info.get('degree', 0.0):.2f}°"
                )

                # Modalities & Elements
                elems = western.get("elements", {})
                mods = western.get("modalities", {})
                lines.append(
                    f"- **Elemental Balance**: Fire: {elems.get('Fire', 0)} pts | Earth: {elems.get('Earth', 0)} pts | Air: {elems.get('Air', 0)} pts | Water: {elems.get('Water', 0)} pts (Dominant: {western.get('dominant_element', 'N/A')})"
                )
                lines.append(
                    f"- **Modalities**: Cardinal: {mods.get('Cardinal', 0)} pts | Fixed: {mods.get('Fixed', 0)} pts | Mutable: {mods.get('Mutable', 0)} pts (Dominant: {western.get('dominant_modality', 'N/A')})"
                )

                # Coordinate grid
                lines.append("- **Planetary Coordinates**:")
                for planet, pos in positions.items():
                    house_str = f" ({pos.get('house')} House)" if pos.get("house") else ""
                    lines.append(
                        f"  - *{planet.replace('_', ' ').title()}*: {pos.get('sign')} {pos.get('degree', 0.0):.2f}°{house_str}"
                    )

            # Aspects
            aspects = western.get("aspects", [])
            if aspects:
                lines.append("- **Active Transit Aspects**:")
                for asp in aspects:
                    lines.append(f"  - {asp.get('description', '')} [{asp.get('aspect', '')}]")
            lines.append("")

        # -------------------------------------------------------------
        # II. Indian Vedic Astrology
        # -------------------------------------------------------------
        indian = astro_data.get("indian", {})
        if indian:
            lines.append("#### II. Indian Vedic Astrology (Panchang & Grahas)")
            panchanga = indian.get("panchanga", {})
            if panchanga:
                tithi = panchanga.get("tithi", {})
                nakshatra = panchanga.get("nakshatra", {})
                yoga = panchanga.get("yoga", {})
                karana = panchanga.get("karana", {})
                vara = panchanga.get("vara", {})

                lines.append(
                    f"- **Tithi (Lunar Day)**: {tithi.get('name', 'N/A')} ({tithi.get('paksha', 'N/A')} Paksha, Progress: {tithi.get('progress', 0.0) * 100:.1f}%)"
                )
                lines.append(
                    f"- **Nakshatra (Lunar Mansion)**: {nakshatra.get('name', 'N/A')} (Progress: {nakshatra.get('progress', 0.0) * 100:.1f}%)"
                )
                lines.append(
                    f"- **Yoga (Synergy)**: {yoga.get('name', 'N/A')} (Progress: {yoga.get('progress', 0.0) * 100:.1f}%)"
                )
                lines.append(f"- **Karana (Half Tithi)**: {karana.get('name', 'N/A')}")
                lines.append(f"- **Vara (Solar Day)**: {vara.get('name', 'N/A')}")

            sidereal = indian.get("sidereal_positions", {})
            if sidereal:
                lines.append("- **Sidereal Graha Coordinates (Lahiri Ayanamsa)**:")
                for graha, pos in sidereal.items():
                    lines.append(f"  - *{graha.title()}*: {pos.get('rashi', 'N/A')} {pos.get('degree', 0.0):.2f}°")

            lines.append(f"- **Ayanamsa Offset**: {indian.get('ayanamsa', 0.0):.4f}°")
            lines.append("")

        # -------------------------------------------------------------
        # III. Chinese Lunisolar Astrology
        # -------------------------------------------------------------
        chinese = astro_data.get("chinese", {})
        if chinese:
            lines.append("#### III. Chinese Lunisolar Astrology & BaZi")
            lunar_date = chinese.get("lunar_date", {})
            lines.append(
                f"- **Lunar Date**: {lunar_date.get('formatted', 'N/A')} (Leap: {lunar_date.get('is_leap', False)})"
            )
            lines.append(f"- **Zodiac Animal**: {chinese.get('zodiac_animal', 'N/A')}")

            bazi = chinese.get("bazi", {})
            if bazi:
                lines.append("- **BaZi Four Pillars of Destiny**:")
                lines.append(f"  - *Year*: {bazi.get('year', 'N/A')}")
                lines.append(f"  - *Month*: {bazi.get('month', 'N/A')}")
                lines.append(f"  - *Day*: {bazi.get('day', 'N/A')}")
                lines.append(f"  - *Hour*: {bazi.get('hour', 'N/A')}")

                # Calculate Wu Xing counts in Python
                counts = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}
                char_map = {"木": "Wood", "火": "Fire", "土": "Earth", "金": "Metal", "水": "Water"}
                for val in bazi.values():
                    if not isinstance(val, str):
                        continue
                    # Match content inside parentheses, or fallback to matching directly
                    match = re.search(r"\(([^)]+)\)", val)
                    elements_str = match.group(1) if match else val
                    for char in elements_str:
                        eng_name = char_map.get(char)
                        if eng_name:
                            counts[eng_name] += 1

                total_elements = sum(counts.values()) or 8
                lines.append("- **Wu Xing Element Balance**:")
                for elem, count in counts.items():
                    percentage = (count / total_elements) * 100
                    lines.append(f"  - *{elem}*: {count} / {total_elements} ({percentage:.1f}%)")

            shichen = chinese.get("shichen", {})
            if shichen:
                lines.append(
                    f"- **Shichen**: {shichen.get('name', 'N/A')} (Earthly Branch: {shichen.get('branch', 'N/A')})"
                )
            lines.append("")

        return "\n".join(lines) + "\n\n"
    except Exception as e:
        logger.error(f"Error compiling astrology context: {e}")
        return "### Astrological Context\nUnavailable.\n\n"


def compile_anatomy_context() -> str:
    try:
        from modules.personal_healing import PersonalHealingModule

        phm = PersonalHealingModule()

        lines = [
            "### Subtle Body & Energetic Anatomy Context",
            "**Active Chakra Radiance Levels & Solfeggio Correspondence**:",
        ]

        for name, info in phm.chakra_data.items():
            freqs = ", ".join(f"{k}: {v}Hz" for k, v in info.get("frequencies", {}).items())
            lines.append(f"- **{info.get('name')}**:")
            lines.append(f"  - Sanskrit: {info.get('sanskrit')}")
            lines.append(f"  - Governs: {info.get('governs')}")
            lines.append(f"  - Frequencies: {freqs}")
            lines.append(f"  - Crystals: {', '.join(info.get('crystals', []))}")
            lines.append(f"  - Affirmations: {'; '.join(info.get('affirmations', []))}")

        lines.append("\n**12 Classical Meridians & Organ Networks**:")
        for name, info in phm.meridian_data.items():
            lines.append(
                f"- **{name.replace('_', ' ').title()} Meridian**: Element: {info.get('element')}, Emotion: {info.get('emotion')}, Frequency: {info.get('frequency')}Hz, Color: {info.get('color')}"
            )

        return "\n".join(lines) + "\n\n"
    except Exception as e:
        logger.error(f"Error compiling anatomy context: {e}")
        return "### Subtle Body Context\nUnavailable.\n\n"


def compile_hardware_context() -> str:
    try:
        from backend.core.services.vajra_service import vajra_service

        sys_status = vajra_service.get_system_status()
        sessions = vajra_service.get_all_sessions()

        lines = [
            "### Active Hardware & Session Metrics",
            f"- **WebSocket Clients Connected**: {sys_status.get('websocket_connections', 0)}",
            f"- **Active Audio Stream**: {'ON' if sys_status.get('streaming_active') else 'OFF'}",
        ]

        if sessions:
            lines.append("- **Active Operations Sessions**:")
            for s_id, s in sessions.items():
                lines.append(
                    f"  - Session ID `{s_id}`: Name: {s.get('name')}, Type: {s.get('type')}, Status: {s.get('status')}"
                )
        else:
            lines.append("- **Active Operations Sessions**: None")

        try:
            from backend.core.orchestrator_bridge import orchestrator_bridge

            if hasattr(orchestrator_bridge, "mops_tracker") and orchestrator_bridge.mops_tracker:
                stats = orchestrator_bridge.mops_tracker.get_statistics()
                lines.append("- **Computational Merit Rates (MOPS)**:")
                lines.append(
                    f"  - Scalar Generation Rate: {stats.get('scalar_pulses', {}).get('10s', 0):,.2f} pulses/sec"
                )
                lines.append(f"  - Mantra Chanting Rate: {stats.get('mantras', {}).get('10s', 0):,.2f} repetitions/sec")
                lines.append(f"  - Crystal Charging Rate: {stats.get('crystals', {}).get('10s', 0):,.2f} pulses/sec")
        except Exception:
            pass

        return "\n".join(lines) + "\n\n"
    except Exception as e:
        logger.error(f"Error compiling hardware/session context: {e}")
        return "### Hardware & Session Context\nUnavailable.\n\n"


@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    """
    Chat with the AI Command Center to run magical computer operations.
    Integrates with OpenAI/Anthropic tool calling with local rule-based fallback.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Message list cannot be empty")

    query = request.messages[-1].content
    provider = request.provider

    if provider == "auto" and request.model:
        if request.model.startswith("lm_studio:"):
            provider = "lm_studio"
        elif request.model.startswith("local:"):
            provider = "local"

    # Retrieve key from request or env
    api_key = request.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("MINIMAX_API_KEY")
    provider = provider or "auto"
    tool_schemas = get_tool_schemas()

    # Build System Prompt
    system_prompt = (
        "You are the Vajra.Stream AI Operator, a wise assistant designed to control a "
        "radionics board, crystal broadcasters, scalar wave generators, and blessing slideshows. "
        "Your goal is to run operations based on the user's intent. "
        "You can execute actions using tools. If the user asks to start a session, list targets, "
        "calibrate the RNG, stop automation, or tune settings, look up the appropriate tool and call it. "
        "Do not explain the tools, just call them. Once you receive the tool results, explain the outcome "
        "with deep compassion and wisdom, invoking the digital dharma theme."
    )

    # Dynamic context injection based on request flags
    context_str = ""
    if request.include_astrology:
        context_str += await compile_astrology_context(request.astrology_data)
    if request.include_anatomy:
        context_str += compile_anatomy_context()
    if request.include_hardware:
        context_str += compile_hardware_context()

    if context_str:
        system_prompt += "\n\nCURRENT ENVIRONMENTAL & SYSTEM METRICS:\n" + context_str

    tool_logs: list[ToolCallLog] = []

    # Prepare debug payload
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
            res = ChatResponse(response=res, tool_calls=tool_logs)
        if request.debug_mode:
            res.debug_info = debug_payload
        return res

    # If no provider API key and provider isn't local or lm_studio, use rule-based fallback
    if not api_key and provider not in ("local", "lm_studio"):
        logger.info("No API keys found. Falling back to rule-based parser.")
        return wrap_res(await run_rule_based_fallback(query))

    # Handle OpenAI Client Tool Calling
    if api_key and (provider == "openai" or (provider == "auto" and os.getenv("OPENAI_API_KEY"))):
        try:
            import openai

            client = openai.OpenAI(api_key=api_key)

            # Format messages
            full_system_prompt, chat_messages = format_messages_for_llm(request.messages, system_prompt)
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages

            # Format tools for OpenAI
            openai_tools = []
            for schema in tool_schemas:
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": schema["name"],
                            "description": schema["description"],
                            "parameters": schema["parameters"],
                        },
                    }
                )

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"OpenAI turn {turn}...")
                response = client.chat.completions.create(
                    model=request.model or "gpt-4o-mini",
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                    temperature=0.7,
                )

                msg = response.choices[0].message
                openai_messages.append(msg)

                # Check if tool calls exist
                if not msg.tool_calls:
                    return wrap_res(ChatResponse(response=msg.content or "", tool_calls=tool_logs))

                # Process tool calls
                for tool_call in msg.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        # Append tool output message
                        openai_messages.append(
                            {"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": json.dumps(result)}
                        )
                    except Exception as ex:
                        logger.error(f"Error executing tool {name}: {ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        openai_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": name,
                                "content": json.dumps({"error": str(ex)}),
                            }
                        )

        except Exception as e:
            logger.error(f"OpenAI execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = await run_rule_based_fallback(query)
            fallback_res.response = (
                f"*(OpenAI Call Failed: {str(e)} - Switched to Local Interpreter)*\n\n" + fallback_res.response
            )
            return wrap_res(fallback_res)

    # Handle LM Studio Local Model Tool Calling
    elif provider == "local" or provider == "lm_studio" or (provider == "auto" and not api_key):
        try:
            import openai as openai_lib

            lm_studio_config = {
                "base_url": os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234"),
                "api_key": "not-required",
                "timeout": float(os.getenv("LM_STUDIO_TIMEOUT", "300")),  # 5 min default — large models need time
            }
            client = openai_lib.OpenAI(
                api_key=lm_studio_config["api_key"],
                base_url=f"{lm_studio_config['base_url']}/v1",
                timeout=lm_studio_config["timeout"],
            )

            # Format messages
            full_system_prompt, chat_messages = format_messages_for_llm(request.messages, system_prompt)
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages

            # Format tools for OpenAI-compatible LM Studio API
            openai_tools = []
            for schema in tool_schemas:
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": schema["name"],
                            "description": schema["description"],
                            "parameters": schema["parameters"],
                        },
                    }
                )

            # Dynamically check for currently loaded model in LM Studio
            model_name = request.model
            if model_name and model_name.startswith("lm_studio:"):
                model_name = model_name.replace("lm_studio:", "", 1)

            if not model_name:
                try:
                    models_res = client.models.list()
                    if models_res and models_res.data:
                        model_name = models_res.data[0].id
                        logger.info(f"Dynamically detected loaded model: {model_name}")
                    else:
                        raise HTTPException(
                            status_code=503,
                            detail="No model is currently loaded in LM Studio. Please load a model in LM Studio first, then retry.",
                        )
                except HTTPException:
                    raise
                except Exception as models_err:
                    logger.error(f"Failed to fetch models from LM Studio: {models_err}")
                    raise HTTPException(
                        status_code=503,
                        detail="Cannot reach LM Studio. Ensure LM Studio is running with a model loaded.",
                    ) from models_err

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"LM Studio turn {turn} with model {model_name}...")
                logger.info(
                    f"Sending messages to LM Studio: {len(openai_messages)} messages, {len(openai_tools)} tools"
                )
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=openai_messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                        temperature=0.7,
                        timeout=float(os.getenv("LM_STUDIO_TIMEOUT", "300")),
                    )
                    logger.info(f"LM Studio response received, finish_reason: {response.choices[0].finish_reason}")
                except Exception as timeout_err:
                    err_str = str(timeout_err).lower()
                    if "timeout" in err_str or "timed out" in err_str or "timed-out" in err_str:
                        logger.error(f"LM Studio request timed out: {timeout_err}")
                        fallback_res = await run_rule_based_fallback(query)
                        fallback_res.response = (
                            "*(LM Studio Request Timed Out - Switched to Local Interpreter)*\n\n"
                            + fallback_res.response
                        )
                        return wrap_res(fallback_res)
                    raise

                msg = response.choices[0].message
                openai_messages.append(msg)

                # Check if tool calls exist
                if not msg.tool_calls:
                    return wrap_res(ChatResponse(response=msg.content or "", tool_calls=tool_logs))

                # Process tool calls
                for tool_call in msg.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)

                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        openai_messages.append(
                            {"role": "tool", "tool_call_id": tool_call.id, "name": name, "content": json.dumps(result)}
                        )
                    except Exception as ex:
                        logger.error(f"Error executing tool {name}: {ex}")
                        try:
                            log_failed_tool_call(FailedToolCallSchema(tool_name=name, arguments=json.dumps(args), error_message=str(ex)))
                        except Exception as log_ex:
                            logger.error(f"Failed to log tool failure to DB: {log_ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        openai_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": name,
                                "content": json.dumps({"error": str(ex)}),
                            }
                        )

        except Exception as e:
            err_str = str(e).lower()
            logger.error(f"LM Studio execution failed: {e}")
            fallback_res = await run_rule_based_fallback(query)
            if "jinja" in err_str or "no user query" in err_str or "prompt template" in err_str:
                fallback_res.response = (
                    "*(LM Studio Prompt Template Error - Check model prompt template settings in LM Studio)*\n\n"
                    + fallback_res.response
                )
            elif "timeout" in err_str or "timed out" in err_str:
                fallback_res.response = (
                    "*(LM Studio Request Timed Out - Switched to Local Interpreter)*\n\n" + fallback_res.response
                )
            elif "connection" in err_str or "refused" in err_str:
                fallback_res.response = (
                    "*(LM Studio Not Available (Connection Refused) - Switched to Local Interpreter)*\n\n"
                    + fallback_res.response
                )
            else:
                fallback_res.response = (
                    f"*(LM Studio Call Failed: {str(e)[:100]} - Switched to Local Interpreter)*\n\n"
                    + fallback_res.response
                )
            return wrap_res(fallback_res)

    # Handle DeepSeek Client Tool Calling
    elif api_key and (provider == "deepseek" or (provider == "auto" and os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"))):
        try:
            import openai as openai_lib
            # For DeepSeek, we use the OpenAI client with custom base URL
            client = openai_lib.OpenAI(
                api_key=api_key,
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            )

            # Format tools if provided
            openai_tools = []
            for t in tool_schemas:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"]
                    }
                })

            # Format messages
            full_system_prompt, chat_messages = format_messages_for_llm(request.messages, system_prompt)
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages

            model_name = request.model or "deepseek-chat"
            max_turns = 5

            for turn in range(max_turns):
                logger.info(f"DeepSeek turn {turn}...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                    temperature=0.7,
                )

                msg = response.choices[0].message
                openai_messages.append(msg)

                if not msg.tool_calls:
                    response_text = msg.content
                    break

                # Process tool calls
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)

                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps(result)
                        })
                    except Exception as ex:
                        logger.error(f"Error executing tool {name}: {ex}")
                        try:
                            log_failed_tool_call(FailedToolCallSchema(tool_name=name, arguments=json.dumps(args), error_message=str(ex)))
                        except Exception as log_ex:
                            logger.error(f"Failed to log tool failure to DB: {log_ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps({"error": str(ex)})
                        })
            else:
                # If we exit the loop without breaking, we hit max_turns
                response_text = "*(DeepSeek reached maximum reasoning turns without finishing.)*"

            return wrap_res(ChatResponse(response=response_text or "", tool_calls=tool_logs))
        except Exception as e:
            err_str = str(e).lower()
            logger.error(f"DeepSeek execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = await run_rule_based_fallback(query)
            fallback_res.response = (
                f"*(DeepSeek Call Failed: {str(e)[:100]} - Switched to Local Interpreter)*\n\n"
                + fallback_res.response
            )
            return wrap_res(fallback_res)

    # Handle minimax.io (OpenAI-compatible) Tool Calling
    elif api_key and (provider == "minimax" or (provider == "auto" and os.getenv("MINIMAX_API_KEY") and not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"))):
        try:
            import openai as openai_lib
            # minimax.io exposes an OpenAI-compatible API; use the OpenAI client.
            client = openai_lib.OpenAI(
                api_key=api_key,
                base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
                timeout=float(os.getenv("MINIMAX_TIMEOUT", "120")),
            )

            openai_tools = []
            for t in tool_schemas:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"]
                    }
                })

            full_system_prompt, chat_messages = format_messages_for_llm(request.messages, system_prompt)
            openai_messages = [{"role": "system", "content": full_system_prompt}] + chat_messages

            model_name = request.model or "MiniMax-M3"
            max_turns = 5
            response_text = ""

            for turn in range(max_turns):
                logger.info(f"minimax turn {turn} with model {model_name}...")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                    temperature=0.7,
                )

                msg = response.choices[0].message
                openai_messages.append(msg)

                if not msg.tool_calls:
                    response_text = msg.content
                    break

                for tc in msg.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)

                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps(result)
                        })
                    except Exception as ex:
                        logger.error(f"Error executing minimax tool {name}: {ex}")
                        try:
                            log_failed_tool_call(FailedToolCallSchema(tool_name=name, arguments=json.dumps(args), error_message=str(ex)))
                        except Exception as log_ex:
                            logger.error(f"Failed to log tool failure to DB: {log_ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps({"error": str(ex)})
                        })
            else:
                response_text = "*(minimax reached maximum reasoning turns without finishing.)*"

            return wrap_res(ChatResponse(response=response_text or "", tool_calls=tool_logs))
        except Exception as e:
            err_str = str(e).lower()
            logger.error(f"minimax execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = await run_rule_based_fallback(query)
            if "timeout" in err_str or "timed out" in err_str:
                prefix = "*(minimax Request Timed Out - Switched to Local Interpreter)*"
            elif "connection" in err_str or "refused" in err_str or "name resolution" in err_str:
                prefix = "*(minimax Not Reachable - Switched to Local Interpreter)*"
            else:
                prefix = f"*(minimax Call Failed: {str(e)[:100]} - Switched to Local Interpreter)*"
            fallback_res.response = f"{prefix}\n\n" + fallback_res.response
            return wrap_res(fallback_res)

    # Handle Anthropic Client Tool Calling
    elif api_key and (provider == "anthropic" or (provider == "auto" and os.getenv("ANTHROPIC_API_KEY"))):
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)

            # Format messages for Claude (system is a top-level parameter)
            full_system_prompt, claude_messages = format_messages_for_llm(request.messages, system_prompt)

            # Format tools for Claude
            claude_tools = []
            for schema in tool_schemas:
                claude_tools.append(
                    {"name": schema["name"], "description": schema["description"], "input_schema": schema["parameters"]}
                )

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"Anthropic turn {turn}...")
                response = client.messages.create(
                    model=request.model or "claude-3-5-haiku-20241022",
                    system=full_system_prompt,
                    messages=claude_messages,
                    tools=claude_tools,
                    temperature=0.7,
                    max_tokens=2000,
                )

                # Append assistant message
                # Note: Claude returns response.content which is a list of blocks
                assistant_content = []
                tool_requests = []

                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        tool_requests.append(block)
                        assistant_content.append(
                            {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
                        )

                claude_messages.append({"role": "assistant", "content": assistant_content})

                if not tool_requests:
                    # Extract final text response
                    text_resp = "".join([b.text for b in response.content if b.type == "text"])
                    return wrap_res(ChatResponse(response=text_resp, tool_calls=tool_logs))

                # Process tool calls
                tool_results_content = []
                for tool_use in tool_requests:
                    name = tool_use.name
                    args = tool_use.input

                    try:
                        result = await execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="success", result=result))
                        tool_results_content.append(
                            {"type": "tool_result", "tool_use_id": tool_use.id, "content": json.dumps(result)}
                        )
                    except Exception as ex:
                        logger.error(f"Error executing Anthropic tool {name}: {ex}")
                        try:
                            log_failed_tool_call(FailedToolCallSchema(tool_name=name, arguments=json.dumps(args), error_message=str(ex)))
                        except Exception as log_ex:
                            logger.error(f"Failed to log tool failure to DB: {log_ex}")
                        tool_logs.append(ToolCallLog(tool_name=name, arguments=args, status="error", error=str(ex)))
                        tool_results_content.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": json.dumps({"error": str(ex)}),
                            }
                        )

                claude_messages.append({"role": "user", "content": tool_results_content})

        except Exception as e:
            logger.error(f"Anthropic execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = await run_rule_based_fallback(query)
            fallback_res.response = (
                f"*(Anthropic Call Failed: {str(e)} - Switched to Local Interpreter)*\n\n" + fallback_res.response
            )
            return wrap_res(fallback_res)

    # Default fallback
    return wrap_res(await run_rule_based_fallback(query))


@router.get("/models", summary="List available LLM models")
async def list_models():
    """List available local GGUF models and API configurations."""
    try:
        from core.llm_integration import LLMIntegration

        llm = LLMIntegration(model_type="auto")
        available = llm.list_available_models()

        # Check active/loaded models in LM Studio via direct HTTP request
        import json as json_mod
        import urllib.error
        import urllib.request

        lm_studio_models = []
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234")
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
