"""
Radionics Operator
LLM-powered radionics orchestrator — the AI backbone of Vajra.Stream.

The RadionicsOperator turns the LLM from a passive content generator into an active
radionics practitioner by:
- Loading knowledge base context (frequencies, mantras, rates, chakras)
- Exposing all container services as typed tools
- Analyzing user intentions and recommending rates/frequencies/configurations
- Interpreting RNG readings and GV measurements in real-time
- Generating personalized protocols combining multiple modalities
- Streaming insights through the event bus to the frontend

Architecture:
    User Intention
         │
         ▼
    RadionicsOperator.analyze(intention)
         │
         ├─→ context_builder.build_system_prompt(session_state)
         ├─→ llm.generate(prompt + tool_schemas)
         ├─→ dispatch tool calls → container services
         └─→ return structured analysis + rate suggestions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from core.context_builder import (
    SessionContext,
    build_intention_analysis_prompt,
    build_system_prompt,
    search_rates,
)
from core.llm.usage import LLMUsageTracker, UsageRecord
from core.radionics_tools import RADIONICS_TOOLS, get_tools_for_provider
from core.rate_to_audio import map_rate_to_carriers, CarrierFrequencySet
from modules.interfaces import EventBus

logger = logging.getLogger(__name__)


def _record_operator_usage(
    *,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    endpoint: str = "operator_chat",
    success: bool = True,
) -> None:
    """Best-effort usage recording for direct operator chat calls.

    The operator bypasses the provider class (it uses ``self.llm.client``
    directly), so it must record explicitly.
    """
    try:
        tracker = LLMUsageTracker.get()
        tracker.record(UsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
            latency_ms=latency_ms,
            endpoint=endpoint,
            success=success,
        ))
    except Exception:  # noqa: BLE001
        logger.debug("LLMUsageTracker.record failed in operator", exc_info=True)


# ============================================================================
# Domain Events
# ============================================================================


class OperatorInsightGenerated:
    """Event: the operator has generated an insight or suggestion."""

    def __init__(self, insight_type: str, content: dict[str, Any], session_id: str | None = None):
        self.timestamp = datetime.now()
        self.event_id = str(uuid.uuid4())
        self.insight_type = insight_type
        self.content = content
        self.session_id = session_id


class RateSuggestionGenerated:
    """Event: the operator has suggested radionics rates."""

    def __init__(self, rates: list[dict], intention: str, session_id: str | None = None):
        self.timestamp = datetime.now()
        self.event_id = str(uuid.uuid4())
        self.rates = rates
        self.intention = intention
        self.session_id = session_id


# ============================================================================
# Tool Dispatcher
# ============================================================================


class ToolDispatcher:
    """
    Dispatches LLM tool calls to actual container services.

    Maps tool names to service methods, handling the impedance mismatch
    between the LLM's function-calling format and the actual Python API.
    """

    def __init__(self, container=None):
        self._container = container

    def set_container(self, container):
        """Set the DI container for service access."""
        self._container = container

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call to the appropriate service and return the result."""

        try:
            # ---- 88 Buddhas & Saka Dawa (no container needed) ----
            if tool_name == "get_random_buddha":
                from core.eighty_eight_buddhas import get_eighty_eight_buddhas

                svc = get_eighty_eight_buddhas()
                category = arguments.get("category")
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

            elif tool_name == "generate_buddha_narrative":
                from core.eighty_eight_buddhas import get_eighty_eight_buddhas

                svc = get_eighty_eight_buddhas()
                result = svc.generate_buddha_narrative(
                    buddha_name=arguments.get("buddha_name", ""),
                    depth=arguments.get("depth", "contemplation"),
                )
                return result

            elif tool_name == "get_88_buddhas_liturgy":
                from core.eighty_eight_buddhas import get_eighty_eight_buddhas

                svc = get_eighty_eight_buddhas()
                return svc.get_confession_sequence()

            elif tool_name == "recite_buddha_name":
                buddha_name = arguments.get("buddha_name", "")
                from core.eighty_eight_buddhas import get_eighty_eight_buddhas

                svc = get_eighty_eight_buddhas()
                b = svc.get_buddha_by_name(buddha_name)
                if not b:
                    return {"error": f"Buddha not found: {buddha_name}"}
                # Actually invoke the unified TTS provider so the recitation is
                # played back in the active backend (Qwen3-TTS or Edge).
                text = f"南無{b.name_chinese}" if not b.name_chinese.startswith("南無") else b.name_chinese
                try:
                    from core.tts_provider import get_tts_provider

                    provider = get_tts_provider()
                    project_id = arguments.get("project_id")
                    if project_id is not None:
                        provider.config.project_id = project_id
                    role = arguments.get("role", "buddhist_chant")
                    edge_v, qwen_s = provider._resolve_voice(
                        arguments.get("voice"),
                        role,
                    )
                    backend_id = provider.active_backend.value

                    async def _do_speak():
                        return await provider.speak(
                            text=text,
                            voice=arguments.get("voice"),
                            rate="-30%",
                            role=role,
                        )

                    try:
                        running = asyncio.get_event_loop()  # noqa: F823
                        if running.is_running():
                            # Schedule the coroutine and immediately return
                            # the metadata; the audio renders in the background.
                            asyncio.ensure_future(_do_speak())
                            path = None
                        else:
                            path = asyncio.run(_do_speak())
                    except RuntimeError:
                        path = asyncio.run(_do_speak())

                    return {
                        "buddha": b.name_chinese,
                        "pinyin": b.name_pinyin,
                        "text": text,
                        "audio_path": path,
                        "backend": backend_id,
                        "speaker": qwen_s if backend_id == "qwen" else edge_v,
                        "role": role,
                        "message": f"Recited {b.name_chinese} ({b.name_pinyin}) via {backend_id}.",
                    }
                except Exception as e:
                    return {
                        "buddha": b.name_chinese,
                        "pinyin": b.name_pinyin,
                        "text": text,
                        "error": str(e),
                        "message": f"Could not play recitation of {b.name_chinese}: {e}",
                    }

            elif tool_name == "start_buddha_recitation":
                from core.buddha_recitation_loop import get_recitation_loop

                loop = get_recitation_loop()
                if loop.state.running:
                    return {"status": "already_running", "message": "Recitation loop already active."}
                import asyncio

                intention = arguments.get("intention", "愿一切众生离苦得乐")
                interval = arguments.get("interval_seconds", 3.0)
                mala_cycles = arguments.get("mala_cycles")
                role = arguments.get("role", "buddhist_chant")
                project_id = arguments.get("project_id")
                voice = arguments.get("voice", "zh-CN-YunxiNeural")
                try:
                    running_loop = asyncio.get_event_loop()
                    if running_loop.is_running():
                        running_loop.create_task(
                            loop.start(
                                intention=intention,
                                interval_seconds=interval,
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
                                interval_seconds=interval,
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
                            interval_seconds=interval,
                            mala_cycles=mala_cycles,
                            voice=voice,
                            role=role,
                            project_id=project_id,
                        )
                    )
                return loop.get_status()

            elif tool_name == "stop_buddha_recitation":
                from core.buddha_recitation_loop import get_recitation_loop

                loop = get_recitation_loop()
                # dispatch() is sync but always called from an async context;
                # schedule the async stop() on the running loop.
                try:
                    asyncio.ensure_future(loop.stop())
                except RuntimeError:
                    pass
                return loop.get_status()

            elif tool_name == "get_buddha_recitation_status":
                from core.buddha_recitation_loop import get_recitation_loop

                loop = get_recitation_loop()
                return loop.get_status()

            elif tool_name == "check_saka_dawa":
                from datetime import datetime

                from core.models.practice import Practice

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

            # ---- Container-required guard ----
            if self._container is None:
                return {"error": "No container set — services unavailable"}

            # ---- Radionics ----
            if tool_name == "broadcast_healing":
                svc = self._container.radionics
                return svc.broadcast_healing(
                    target_name=arguments.get("target_name", ""),
                    duration_minutes=arguments.get("duration_minutes", 10),
                    frequency_hz=arguments.get("frequency_hz", 528.0),
                    intensity=arguments.get("intensity", 0.8),
                )

            elif tool_name == "broadcast_liberation":
                svc = self._container.radionics
                return svc.broadcast_liberation(
                    event_name=arguments.get("event_name", ""),
                    souls_count=arguments.get("souls_count", 1000),
                    duration_minutes=arguments.get("duration_minutes", 108),
                )

            elif tool_name == "get_available_intentions":
                svc = self._container.radionics
                return {"intentions": svc.get_available_intentions()}

            elif tool_name == "get_sacred_frequencies":
                svc = self._container.radionics
                return svc.get_sacred_frequencies()

            # ---- Rate Engine ----
            elif tool_name == "text_to_rate":
                from core.radionics_engine import SignatureCalculator

                calc = SignatureCalculator()
                rate = calc.text_to_rate(
                    text=arguments.get("text", ""),
                    num_dials=arguments.get("num_dials", 3),
                    algorithm="mixed",
                )
                return rate.to_dict()

            elif tool_name == "measure_general_vitality":
                from core.radionics_engine import GeneralVitalityMeter

                meter = GeneralVitalityMeter()
                stats = meter.measure_multiple(
                    count=arguments.get("samples", 10),
                    subject=arguments.get("subject", ""),
                )
                return {
                    "subject": arguments.get("subject", ""),
                    "gv_mean": stats["mean"],
                    "gv_median": stats["median"],
                    "gv_std": stats["std"],
                    "gv_min": stats["min"],
                    "gv_max": stats["max"],
                    "interpretation": meter.interpret_gv(stats["mean"]),
                    "samples": arguments.get("samples", 10),
                }

            elif tool_name == "find_balancing_rates":
                from core.radionics_engine import RadionicsAnalyzer

                analyzer = RadionicsAnalyzer()
                rates = analyzer.find_balancing_rates(
                    subject=arguments.get("subject", ""),
                    num_rates=arguments.get("num_rates", 5),
                )
                return {
                    "subject": arguments.get("subject", ""),
                    "balancing_rates": [r.to_dict() for r in rates],
                }

            elif tool_name == "search_knowledge":
                from core.knowledge_index import search_knowledge as kb_search

                results = kb_search(
                    query=arguments.get("query", ""),
                    top_k=arguments.get("top_k", 5),
                    category=arguments.get("category"),
                )
                return {"query": arguments.get("query", ""), "results": results, "count": len(results)}

            elif tool_name == "web_search":
                return self._dispatch_web_search(
                    query=arguments.get("query", ""),
                    top_k=arguments.get("top_k", 5),
                )

            elif tool_name == "web_fetch":
                return self._dispatch_web_fetch(url=arguments.get("url", ""))

            elif tool_name == "get_world_context":
                from core.internet_context import compile_world_context, format_context_for_llm

                ctx = compile_world_context()
                return {
                    "events_count": len(ctx.events),
                    "disasters_count": len(ctx.disasters),
                    "summary": ctx.summary,
                    "planetary_hour": ctx.planetary_hour,
                    "day_ruler": ctx.day_ruler,
                    "context_text": format_context_for_llm(ctx),
                }

            elif tool_name == "search_rate_database":
                results = search_rates(
                    query=arguments.get("query", ""),
                    category=arguments.get("category"),
                )
                return {"query": arguments.get("query", ""), "results": results, "count": len(results)}

            # ---- Scalar Waves ----
            elif tool_name == "generate_scalar_waves":
                svc = self._container.scalar_waves
                return svc.generate(
                    method=arguments.get("method", "hybrid"),
                    count=arguments.get("count", 10000),
                    intensity=arguments.get("intensity", 1.0),
                )

            # ---- RNG ----
            elif tool_name == "create_rng_session":
                from backend.core.services.rng_attunement_service import get_rng_service

                svc = get_rng_service()
                session_id = svc.create_session(
                    baseline_tone_arm=arguments.get("baseline_tone_arm", 5.0),
                    sensitivity=arguments.get("sensitivity", 1.0),
                )
                return {"session_id": session_id, "status": "active"}

            elif tool_name == "get_rng_reading":
                from backend.core.services.rng_attunement_service import get_rng_service

                svc = get_rng_service()
                reading = svc.get_reading(arguments["session_id"])
                if reading is None:
                    return {"error": "Session not found or inactive"}
                return {
                    "tone_arm": reading.tone_arm,
                    "needle_position": reading.needle_position,
                    "needle_state": reading.needle_state.name
                    if hasattr(reading.needle_state, "name")
                    else str(reading.needle_state),
                    "floating_needle_score": reading.floating_needle_score,
                    "coherence": reading.coherence,
                    "entropy": reading.entropy,
                }

            elif tool_name == "get_rng_summary":
                from backend.core.services.rng_attunement_service import get_rng_service

                svc = get_rng_service()
                return svc.get_session_summary(arguments["session_id"])

            # ---- Anatomy ----
            elif tool_name == "get_chakra_info":
                svc = self._container.anatomy
                return {"chakras": svc.get_chakra_info()}

            elif tool_name == "get_meridian_info":
                svc = self._container.anatomy
                return {"meridians": svc.get_meridian_info()}

            # ---- Healing ----
            elif tool_name == "create_healing_session":
                svc = self._container.healing
                return svc.create_healing_session(
                    target_name=arguments.get("target_name", ""),
                    modalities=arguments.get("modalities"),
                    duration_minutes=arguments.get("duration_minutes", 60),
                    intention=arguments.get("intention", "complete healing"),
                )

            elif tool_name == "chakra_balancing_protocol":
                svc = self._container.healing
                return svc.chakra_balancing_protocol(
                    target_name=arguments.get("target_name", ""),
                    chakras=arguments.get("chakras"),
                )

            elif tool_name == "get_healing_modalities":
                svc = self._container.healing
                return {"modalities": svc.get_available_modalities()}

            # ---- Astrology ----
            elif tool_name == "get_planetary_positions":
                svc = self._container.astrology
                if svc is None:
                    return {"error": "Astrology service not available"}
                return svc.get_planetary_positions()

            elif tool_name == "calculate_natal_chart":
                svc = self._container.astrology
                if svc is None:
                    return {"error": "Astrology service not available"}
                from datetime import datetime as dt

                birth_date = dt.fromisoformat(arguments["birth_date"])
                return svc.calculate_natal_chart(
                    name=arguments.get("name"),
                    birth_date=birth_date,
                    latitude=arguments["latitude"],
                    longitude=arguments["longitude"],
                )

            # ---- Audio ----
            elif tool_name == "generate_audio":
                svc = self._container.audio
                freq = arguments.get("frequency_hz", 136.1)
                duration = arguments.get("duration_seconds", 10)
                mode = arguments.get("mode", "prayer_bowl")
                return svc.generate_tone(
                    frequency=freq,
                    duration=duration,
                    mode=mode,
                )

            # ---- Blessings ----
            elif tool_name == "generate_blessing":
                svc = self._container.blessings
                return svc.generate_blessing(
                    target_name=arguments.get("target_name", ""),
                    intention=arguments.get("intention", "peace and happiness"),
                    tradition=arguments.get("tradition", "universal"),
                )

            elif tool_name == "get_blessing_traditions":
                svc = self._container.blessings
                return {"traditions": svc.get_available_traditions()}

            # ---- LLM Content ----
            elif tool_name == "generate_prayer":
                svc = self._container.llm
                return svc.generate_prayer(
                    intention=arguments.get("intention", "healing"),
                    tradition=arguments.get("tradition", "universal"),
                )

            elif tool_name == "generate_teaching":
                svc = self._container.llm
                return svc.generate_teaching(
                    topic=arguments.get("topic", "compassion"),
                    tradition=arguments.get("tradition", "buddhist"),
                    depth=arguments.get("length", "moderate"),
                )

            elif tool_name == "generate_meditation_script":
                svc = self._container.llm
                return svc.generate_meditation_script(
                    meditation_type=arguments.get("meditation_type", "loving-kindness"),
                    duration_minutes=arguments.get("duration_minutes", 20),
                    experience_level=arguments.get("experience_level", "beginner"),
                )

            # ---- Agentic Timing & Journey ----
            elif tool_name == "check_auspicious_timing":
                from core.auspicious_timing import check_auspicious_window

                window = check_auspicious_window(arguments.get("genre", "healing"))
                return window.to_dict()

            elif tool_name == "get_all_genre_windows":
                from core.auspicious_timing import get_all_windows

                return {"windows": get_all_windows()}

            elif tool_name == "get_current_conditions":
                from core.auspicious_timing import AuspiciousTiming

                t = AuspiciousTiming()
                return t.get_current_conditions()

            elif tool_name == "generate_character":
                return self._dispatch_operator("generate_character", {})

            elif tool_name == "start_character_journey":
                return self._dispatch_operator("start_character_journey", {})

            elif tool_name == "advance_journey":
                return self._dispatch_operator("advance_journey", {})

            elif tool_name == "get_journey_status":
                return self._dispatch_operator("get_journey_status", {})

            elif tool_name == "run_full_journey":
                return self._dispatch_operator("run_full_journey", {})

            elif tool_name == "prepare_crystal_broadcast":
                return self._dispatch_operator("prepare_crystal_broadcast", {
                    "intention": arguments.get("intention", ""),
                    "duration_minutes": arguments.get("duration_minutes", 10),
                })

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool dispatch error for {tool_name}: {e}")
            return {"error": str(e)}

    def _dispatch_operator(self, method: str, args: dict) -> dict[str, Any]:
        """Delegate to the RadionicsOperator's own methods for agentic operations."""
        if self._container:
            op = getattr(self._container, "operator", None)
            if op and hasattr(op, method):
                return getattr(op, method)(**args)
        return {"error": f"Operator method {method} unavailable"}

    def _dispatch_web_search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Search the web via DuckDuckGo (no API key needed)."""
        try:
            import urllib.parse
            import urllib.request

            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "VajraStream/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            # Simple extraction of result snippets
            results = []
            import re

            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            for s in snippets[:top_k]:
                clean = re.sub(r"<[^>]+>", "", s).strip()
                if clean:
                    results.append({"snippet": clean[:300]})

            if not results:
                # Fallback: return a note that web search requires network
                results = [
                    {
                        "snippet": f"Web search for '{query}' — results unavailable (network issue or no results). Try using the local knowledge base via search_knowledge."
                    }
                ]

            return {"query": query, "results": results, "count": len(results)}
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    def _dispatch_web_fetch(self, url: str) -> dict[str, Any]:
        """Fetch and read a web page."""
        if not url:
            return {"error": "No URL provided"}
        try:
            import urllib.request

            req = urllib.request.Request(url, headers={"User-Agent": "VajraStream/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            # Strip HTML tags for a rough text extraction
            import re

            text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return {"url": url, "content": text[:3000], "length": len(text)}
        except Exception as e:
            return {"url": url, "error": str(e)}


# ============================================================================
# Radionics Operator
# ============================================================================


class RadionicsOperator:
    """
    LLM-powered radionics operator.

    Usage:
        operator = RadionicsOperator(container, event_bus)
        result = operator.analyze_intention("Help my friend with chronic back pain")
        # result contains structured analysis, rate suggestions, frequency recommendations

        config = operator.suggest_rates("chronic back pain")
        # config contains specific rate values, frequencies, mantras

        insight = operator.generate_insight(session_context)
        # insight is a natural-language interpretation of current session state
    """

    def __init__(self, container=None, event_bus: EventBus | None = None, llm=None):
        self._container = container
        # Injected only — no private fallback bus. See ADR 003 (pub/sub split).
        self.event_bus = event_bus
        self._llm = llm
        self._creative_llm = None  # Lazy-loaded via creative_llm property
        self._dispatcher = ToolDispatcher(container)
        self._session = SessionContext()
        self._provider = "auto"
        self._autonomous_active = False
        self._autonomous_interval = 300
        self._autonomous_suggestions: list[dict[str, Any]] = []
        self._blessing_loop_active = False
        self._blessing_loop_intention = ""
        self._blessing_loop_interval = 15.0
        self._blessing_stream: list[dict[str, Any]] = []
        self._autonomous_task: asyncio.Task | None = None
        self._blessing_loop_task: asyncio.Task | None = None

    @property
    def llm(self):
        """Lazy-load the default LLM (backward compatible — uses orchestrator)."""
        return self.orchestrator_llm

    @property
    def orchestrator_llm(self):
        """LLM for orchestration — tool calling, analysis, autonomous decisions.
        Configured via LM_STUDIO_ORCHESTRATOR_MODEL env var."""
        if self._llm is None:
            try:
                import os

                from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration

                model_name = os.getenv("LM_STUDIO_ORCHESTRATOR_MODEL")
                self._llm = LLMIntegration(model_type="auto", model_name=model_name)
                self._provider = self._llm.model_type
            except ImportError:
                self._llm = None
        return self._llm

    @property
    def creative_llm(self):
        """LLM for creative content — blessings, dharma tales, prayers.
        Configured via LM_STUDIO_CREATIVE_MODEL env var.
        Falls back to orchestrator LLM if not configured."""
        if self._creative_llm is None:
            try:
                import os

                from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration

                creative_model = os.getenv("LM_STUDIO_CREATIVE_MODEL")
                if creative_model:
                    self._creative_llm = LLMIntegration(model_type="auto", model_name=creative_model)
                else:
                    self._creative_llm = self.orchestrator_llm
            except ImportError:
                self._creative_llm = self.orchestrator_llm
        return self._creative_llm

    @property
    def dispatcher(self) -> ToolDispatcher:
        return self._dispatcher

    def set_container(self, container):
        """Set the DI container (call after container is fully initialized)."""
        self._container = container
        self._dispatcher.set_container(container)

    def _refresh_astrology_context(self):
        """Auto-populate planetary_context with current transits."""
        try:
            from core.context_builder import format_astrology_for_llm

            self._session.planetary_context = format_astrology_for_llm()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_intention(self, intention: str) -> dict[str, Any]:
        """
        Analyze a user intention and return structured results.

        The LLM parses the intention into structured components,
        searches the rate database, and recommends a complete configuration.

        Returns a dict with:
            - analysis: structured intention breakdown (target, condition, chakra, etc.)
            - suggested_rates: list of rate candidates with reasoning
            - recommended_frequency: optimal carrier frequency
            - recommended_mantra: suggested mantra
            - protocol: suggested session configuration
        """
        if self.llm is None or (not self.llm.client and not self.llm.local_model):
            return self._fallback_analysis(intention)

        self._refresh_astrology_context()
        self._session.update(intention=intention)
        self._session.record_event("analyze_intention", {"intention": intention})

        # Step 1: Parse the intention into structured components
        analysis_prompt = build_intention_analysis_prompt(intention)
        system_prompt = build_system_prompt(self._session.to_dict())

        try:
            analysis_raw = self.llm.generate(
                prompt=analysis_prompt,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.3,
            )
            analysis = self._safe_json_parse(
                analysis_raw, {"intention": intention, "error": "Failed to parse analysis"}
            )
        except Exception as e:
            logger.warning(f"LLM intention analysis failed: {e}")
            analysis = self._fallback_parse_intention(intention)

        # Step 2: Search rate database
        condition = analysis.get("condition", intention)
        rate_results = search_rates(condition)

        # Step 3: Generate rate suggestions
        if rate_results:
            suggested_rates = [
                {
                    "values": r.get("values", r.get("rate", [])),
                    "name": r.get("name", r.get("id", "unknown")),
                    "source": r.get("_source", "database"),
                    "reasoning": f"Found in {r.get('_source', 'database')}: {r.get('description', r.get('condition', ''))}",
                }
                for r in rate_results[:5]
            ]
        else:
            # Generate rates from intention signature
            from core.radionics_engine import SignatureCalculator

            calc = SignatureCalculator()
            sig_rate = calc.text_to_rate(intention, num_dials=3, algorithm="mixed")
            suggested_rates = [
                {
                    "values": sig_rate.values,
                    "name": f"Signature: {intention[:30]}",
                    "source": "signature",
                    "reasoning": "Derived from intention text via mixed hash+gematria algorithm",
                }
            ]

        # Step 4: Build recommendations
        result = {
            "analysis": analysis,
            "suggested_rates": suggested_rates,
            "recommended_frequency": analysis.get("recommended_frequency", 528),
            "recommended_mantra": analysis.get("recommended_mantra_tradition", "compassion"),
            "recommended_modalities": analysis.get("modalities", ["scalar_waves", "radionics"]),
            "session_id": str(uuid.uuid4()),
        }

        # Emit event
        if self.event_bus:
            self.event_bus.publish(
                RateSuggestionGenerated(
                    rates=suggested_rates,
                    intention=intention,
                    session_id=result["session_id"],
                )
            )

        self._session.record_event("analysis_complete", result)
        return result

    def prepare_crystal_broadcast(self, intention: str, duration_minutes: int = 10) -> dict[str, Any]:
        """
        One-shot tool: analyze an intention AND prepare the crystal bowl
        broadcast configuration (carrier frequencies + prayer bowl
        parameters) in a single call.

        Calls :func:`~core.rate_to_audio.map_rate_to_carriers` on the
        best suggested rate from :meth:`analyze_intention` to produce
        Solfeggio-aligned carrier frequencies ready for prayer bowl
        synthesis via :class:`~core.enhanced_audio_generator.EnhancedAudioGenerator`.

        Returns a dict with:
            - analysis: structured intention breakdown
            - rate: the best suggested rate (dial values)
            - carriers: CarrierFrequencySet (frequencies + amplitude + overtone_richness)
            - solfeggio_names: human-readable names for each frequency
            - broadcast_config: ready-to-use config for the crystal broadcaster
        """
        analysis_result = self.analyze_intention(intention)

        # Extract the best rate from the analysis
        best_rate = None
        suggested = analysis_result.get("suggested_rates", [])
        if suggested and suggested[0].get("values"):
            best_rate = suggested[0]["values"]
        if best_rate is None:
            # Fallback: use the recommended frequency directly
            best_rate = [50, 50, 50]  # placeholder that snaps to 639

        potency = 0.8  # standard broadcast potency
        carriers = map_rate_to_carriers(best_rate, potency=potency)

        broadcast_config = {
            "intention": intention,
            "duration_minutes": duration_minutes,
            "rate_values": best_rate,
            "potency": potency,
            "frequencies": carriers.frequencies,
            "solfeggio_names": carriers.solfeggio_names,
            "amplitude": carriers.amplitude,
            "overtone_richness": carriers.overtone_richness,
            "prayer_bowl": True,
        }

        # Publish event so frontend can react
        if self.event_bus:
            from modules.interfaces import BroadcastStarted
            self.event_bus.publish(BroadcastStarted(
                timestamp=datetime.now(),
                event_id=str(uuid.uuid4()),
                session_id=analysis_result.get("session_id", ""),
                hardware_level=2,
                frequencies=carriers.frequencies,
            ))

        self._session.record_event("crystal_broadcast_prepared", broadcast_config)
        return {
            "analysis": analysis_result.get("analysis", {}),
            "rate": best_rate,
            "carriers": carriers,
            "solfeggio_names": carriers.solfeggio_names,
            "broadcast_config": broadcast_config,
        }

    def suggest_rates(self, intention_or_condition: str, count: int = 5) -> dict[str, Any]:
        """
        Generate specific rate suggestions for an intention or condition.

        Uses the rate database first, falling back to LLM-powered suggestion
        if the database has no matches.
        """
        self._session.update(intention=intention_or_condition)

        # Check database first
        db_results = search_rates(intention_or_condition)
        if db_results:
            return {
                "source": "database",
                "intention": intention_or_condition,
                "rates": [
                    {
                        "values": r.get("values", r.get("rate", [])),
                        "name": r.get("name", r.get("id", "")),
                        "description": r.get("description", r.get("condition", "")),
                        "source_db": r.get("_source", ""),
                    }
                    for r in db_results[:count]
                ],
            }

        # Fall back to signature-based rate generation
        from core.radionics_engine import RadionicsAnalyzer, SignatureCalculator

        calc = SignatureCalculator()
        sig = calc.text_to_rate(intention_or_condition, num_dials=3, algorithm="mixed")

        analyzer = RadionicsAnalyzer()
        balancing = analyzer.find_balancing_rates(intention_or_condition, num_rates=count)

        return {
            "source": "algorithmic",
            "intention": intention_or_condition,
            "signature_rate": sig.to_dict(),
            "balancing_rates": [r.to_dict() for r in balancing],
        }

    def generate_insight(self, session_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Generate a natural-language insight about the current session state.

        The LLM interprets RNG readings, GV trends, and scalar wave metrics
        to provide meaningful commentary and suggestions.
        """
        if session_context:
            self._session.update(**session_context)

        state = self._session.to_dict()

        if not state:
            return {"insight": "No active session data to analyze.", "type": "idle"}

        if self.llm is None or (not self.llm.client and not self.llm.local_model):
            return self._fallback_insight(state)

        system_prompt = build_system_prompt(state)
        insight_prompt = f"""You are monitoring a live radionics session. Based on the current state:

{json.dumps(state, indent=2, default=str)}

Provide a brief insight (2-3 sentences) about:
1. What the readings suggest about session effectiveness
2. Any adjustments you'd recommend
3. Whether to continue, extend, or conclude the session

Be concise and practical. If RNG data shows a floating needle or high coherence, note it as a positive sign."""

        try:
            insight_text = self.llm.generate(
                prompt=insight_prompt,
                system_prompt=system_prompt,
                max_tokens=200,
                temperature=0.5,
            )

            result = {
                "insight": insight_text.strip(),
                "type": "llm_generated",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"LLM insight generation failed: {e}")
            result = self._fallback_insight(state)

        # Emit event
        if self.event_bus:
            self.event_bus.publish(
                OperatorInsightGenerated(
                    insight_type=result.get("type", "insight"),
                    content=result,
                )
            )

        self._session.record_event("insight_generated", result)
        return result

    def chat(self, message: str, model_override: str | None = None) -> dict[str, Any]:
        """
        Open-ended chat with the radionics operator.

        The LLM can use tools to answer questions, make recommendations,
        and execute radionics operations.

        ``model_override`` optionally pins a specific model for this call.
        When ``None`` (the default), the operator uses the ProviderRegistry
        primary (``self.llm.model_name``). The operator chat path is NOT
        user-selectable from the UI today.
        """
        if self.llm is None:
            return {"reply": "LLM not available. Please configure an API key or local model.", "type": "error"}

        self._refresh_astrology_context()
        system_prompt = build_system_prompt(self._session.to_dict())
        tools = get_tools_for_provider(self._provider)

        try:
            if self._provider == "openai":
                return self._chat_openai(message, system_prompt, tools, model_override=model_override)
            elif self._provider == "anthropic":
                return self._chat_anthropic(message, system_prompt, tools, model_override=model_override)
            else:
                # Local model — no tool calling, just text generation
                reply = self.llm.generate(
                    prompt=message,
                    system_prompt=system_prompt,
                    max_tokens=500,
                    temperature=0.7,
                    model=model_override,
                )
                return {"reply": reply.strip(), "type": "text"}

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {"reply": f"I encountered an error: {e}", "type": "error"}

    # ------------------------------------------------------------------
    # LLM Blessing Loop — continuous stream of unique blessings
    # ------------------------------------------------------------------

    def start_blessing_loop(self, intention: str = "all beings", interval_seconds: float = 15.0) -> dict[str, Any]:
        """Start a continuous loop generating unique LLM-written blessings."""
        if self._blessing_loop_active:
            return {"status": "already_running", "message": "Blessing loop is already active"}

        # Floor the interval to avoid hammering the LLM API. The default
        # 15s is fine, but callers can request lower — we clamp to 30s so
        # an accidental 1s / 5s doesn't burn the daily cost cap.
        min_interval = 30.0
        effective_interval = max(float(interval_seconds), min_interval)
        if effective_interval != interval_seconds:
            logger.info(
                "Blessing loop interval raised from %.1fs to floor of %.1fs",
                interval_seconds, min_interval,
            )

        self._blessing_loop_active = True
        self._blessing_loop_intention = intention
        self._blessing_loop_interval = effective_interval
        self._blessing_stream: list[dict[str, Any]] = []

        # Generate first blessing immediately
        blessing = self._generate_blessing(intention)
        if blessing:
            self._blessing_stream.append(blessing)

        self._session.record_event("blessing_loop_started", {"intention": intention})

        # Start the background daemon loop
        try:
            loop = asyncio.get_running_loop()
            self._blessing_loop_task = loop.create_task(self._run_blessing_loop())
            logger.info("Blessing loop background daemon task scheduled successfully.")
        except RuntimeError:
            logger.info("No running event loop found, background blessing loop not scheduled (normal in tests).")

        return {
            "status": "started",
            "intention": intention,
            "interval_seconds": effective_interval,
            "message": f"Blessing loop started. Generating unique blessings for {intention} every {effective_interval}s.",
            "first_blessing": blessing,
        }

    async def _run_blessing_loop(self):
        """Run blessing generation periodically in the background."""
        logger.info("Blessing loop background task started.")
        while self._blessing_loop_active:
            try:
                await asyncio.sleep(self._blessing_loop_interval)
                if not self._blessing_loop_active:
                    break
                logger.info("Generating next blessing in background loop...")
                # Run blessing generation in a thread since it can involve synchronous fallback API calls
                await asyncio.to_thread(self.generate_next_blessing)
            except asyncio.CancelledError:
                logger.info("Blessing loop background task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in blessing loop cycle: {e}")

    def stop_blessing_loop(self) -> dict[str, Any]:
        """Stop the blessing loop and return collected blessings."""
        self._blessing_loop_active = False
        if self._blessing_loop_task:
            self._blessing_loop_task.cancel()
            self._blessing_loop_task = None
            logger.info("Blessing loop background task cancelled.")
        count = len(self._blessing_stream)
        self._session.record_event("blessing_loop_stopped", {"count": count})
        return {
            "status": "stopped",
            "blessings_generated": count,
            "recent": self._blessing_stream[-5:] if self._blessing_stream else [],
        }

    def get_blessing_loop_status(self) -> dict[str, Any]:
        """Get current blessing loop status."""
        return {
            "active": self._blessing_loop_active,
            "intention": getattr(self, "_blessing_loop_intention", ""),
            "interval_seconds": getattr(self, "_blessing_loop_interval", 15),
            "blessings_count": len(self._blessing_stream) if hasattr(self, "_blessing_stream") else 0,
        }

    def get_blessing_stream(self, since: int = 0) -> list[dict[str, Any]]:
        """Get blessings generated since the given index."""
        if not hasattr(self, "_blessing_stream"):
            return []
        return self._blessing_stream[since:]

    def generate_next_blessing(self) -> dict[str, Any] | None:
        """Manually trigger the next blessing generation."""
        intention = getattr(self, "_blessing_loop_intention", "all beings")
        blessing = self._generate_blessing(intention)
        if blessing:
            self._blessing_stream.append(blessing)
            try:
                from modules.interfaces import BlessingGenerated

                if self.event_bus:
                    self.event_bus.publish(
                        BlessingGenerated(
                            timestamp=datetime.now(),
                            event_id=str(uuid.uuid4()),
                            target_name=intention,
                            blessing_text=blessing.get("text", "")[:500],
                            tradition=blessing.get("tradition", "Universal"),
                        )
                    )
            except Exception as e:
                logger.error(f"Error publishing BlessingGenerated event: {e}")
        return blessing

    def _generate_blessing(self, intention: str) -> dict[str, Any] | None:
        """Generate a single unique blessing using the creative LLM."""
        creative = self.creative_llm
        if not creative or (not creative.client and not creative.local_model):
            # Fallback — use the blessings service
            if self._container:
                result = self._container.blessings.generate_blessing(
                    target_name=intention,
                    intention=intention,
                    tradition="universal",
                )
                return {
                    "text": result.get("blessing_text", ""),
                    "tradition": "universal",
                    "generator": "template",
                }
            return None

        try:
            # Vary the prompt to get unique blessings each time
            import random

            styles = ["poetic", "heartfelt", "simple", "traditional", "cosmic"]
            traditions = ["buddhist", "universal", "tibetan", "sufi", "hindu"]
            style = random.choice(styles)
            trad = random.choice(traditions)

            prompt = f"""Write a beautiful, unique blessing for {intention}.

Style: {style}
Tradition: {trad}
Length: 3-5 lines
Tone: {random.choice(["reverent", "tender", "powerful", "gentle", "radiant"])}

Make this blessing DIFFERENT from standard prayers. Let it be fresh, alive, specific.
Do not repeat phrases you've used before. Each blessing should feel like a new creation.

Write only the blessing text, no explanation."""

            system = build_system_prompt(self._session.to_dict())
            blessing_text = creative.generate(
                prompt=prompt,
                system_prompt=system,
                max_tokens=200,
                temperature=0.9,  # High temperature for creativity
            )

            return {
                "text": blessing_text.strip(),
                "tradition": trad,
                "style": style,
                "generator": "llm",
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Blessing generation failed: {e}")
            return None

    def get_status(self) -> dict[str, Any]:
        """Get operator status."""
        creative = self.creative_llm
        return {
            "llm_available": self.llm is not None,
            "llm_provider": self._provider,
            "container_available": self._container is not None,
            "active_session": bool(self._session.intention),
            "session": self._session.to_dict(),
            "tools_count": len(RADIONICS_TOOLS),
            "autonomous_mode": self._autonomous_active,
            "blessing_loop_active": getattr(self, "_blessing_loop_active", False),
            "journey_active": hasattr(self, "_active_journey") and self._active_journey is not None,
            "llm_config": {
                "orchestrator_model": getattr(self.llm, "model_name", "auto") if self.llm else "none",
                "creative_model": getattr(creative, "model_name", "auto") if creative else "none",
                "dual_llm": self._creative_llm is not None and self._creative_llm is not self._llm,
            },
        }

    # ------------------------------------------------------------------
    # Agentic Character Journey
    # ------------------------------------------------------------------

    def generate_character(self, use_llm: bool = True) -> dict[str, Any]:
        from core.character_generator import CharacterGenerator

        gen = CharacterGenerator()
        sheet = gen.generate(use_llm=use_llm, operator=self)
        return {"character": sheet.to_dict(), "backstory": sheet.backstory, "prompt_context": sheet.to_prompt_context()}

    def start_character_journey(self, character: dict[str, Any] | None = None) -> dict[str, Any]:
        from core.character_generator import CharacterSheet
        from core.character_journey import CharacterJourney

        if character is None:
            generated = self.generate_character()
            character = generated["character"]
        sheet = CharacterSheet(
            name=character.get("name", ""),
            chinese_name=character.get("chinese_name", ""),
            chinese_name_pinyin=character.get("chinese_name_pinyin", ""),
            chinese_name_meaning=character.get("chinese_name_meaning", ""),
            element={
                "name": character.get("element", ""),
                "quality": character.get("element_quality", ""),
                "color": character.get("element_color", ""),
                "chakra": character.get("element_chakra", ""),
                "frequency": character.get("element_frequency", ""),
            },
            role={
                "name": character.get("role", ""),
                "icon": character.get("role_icon", ""),
                "mantra": character.get("role_mantra", ""),
                "virtue": character.get("role_virtue", ""),
                "chinese": character.get("role_chinese", ""),
                "chinese_pinyin": character.get("role_chinese_pinyin", ""),
                "chinese_description": character.get("role_chinese_description", ""),
            },
            frequency=character.get("frequency", 528),
            origin=character.get("origin", ""),
            quest=character.get("quest", ""),
            sigil_seed=character.get("sigil_seed", ""),
            grounding_sense=character.get("grounding_sense", ""),
            channeling_state=character.get("channeling_state", ""),
            anchoring_ritual=character.get("anchoring_ritual", ""),
            backstory=character.get("backstory", ""),
            stats=character.get("stats", {}),
            generated_at=character.get("generated_at", ""),
            generator=character.get("generator", "rng"),
        )
        self._active_journey = CharacterJourney(self)
        return self._active_journey.begin(sheet)

    def advance_journey(self) -> dict[str, Any]:
        if not hasattr(self, "_active_journey") or self._active_journey is None:
            return {"error": "No active journey"}
        if self._active_journey.is_complete:
            return {"status": "complete", "harvest": self._active_journey.harvest()}
        return self._active_journey.advance()

    def get_journey_status(self) -> dict[str, Any]:
        if not hasattr(self, "_active_journey") or self._active_journey is None:
            return {"active": False}
        journey = self._active_journey
        character_data = None
        if hasattr(journey, "_character") and journey._character:
            if hasattr(journey._character, "to_dict"):
                character_data = journey._character.to_dict()
            elif isinstance(journey._character, dict):
                character_data = journey._character
        return {
            "active": True,
            "is_complete": journey.is_complete,
            "current_stage": journey.current_stage.value if journey.current_stage else None,
            "stage_index": journey._current_stage_index,
            "stages_total": 6,
            "stage_results": journey._stage_results,
            "character": character_data,
        }

    def harvest_journey(self) -> dict[str, Any]:
        if not hasattr(self, "_active_journey") or self._active_journey is None:
            return {"error": "No active journey"}
        result = self._active_journey.harvest()
        self._active_journey = None
        return result

    def run_full_journey(self, character: dict[str, Any] | None = None) -> dict[str, Any]:
        from core.character_generator import CharacterSheet
        from core.character_journey import CharacterJourney

        if character is None:
            generated = self.generate_character()
            character = generated["character"]
        sheet = CharacterSheet(
            name=character.get("name", ""),
            chinese_name=character.get("chinese_name", ""),
            chinese_name_pinyin=character.get("chinese_name_pinyin", ""),
            chinese_name_meaning=character.get("chinese_name_meaning", ""),
            element={
                "name": character.get("element", ""),
                "quality": character.get("element_quality", ""),
                "color": character.get("element_color", ""),
                "chakra": character.get("element_chakra", ""),
                "frequency": character.get("element_frequency", ""),
            },
            role={
                "name": character.get("role", ""),
                "icon": character.get("role_icon", ""),
                "mantra": character.get("role_mantra", ""),
                "virtue": character.get("role_virtue", ""),
                "chinese": character.get("role_chinese", ""),
                "chinese_pinyin": character.get("role_chinese_pinyin", ""),
                "chinese_description": character.get("role_chinese_description", ""),
            },
            frequency=character.get("frequency", 528),
            origin=character.get("origin", ""),
            quest=character.get("quest", ""),
            sigil_seed=character.get("sigil_seed", ""),
            grounding_sense=character.get("grounding_sense", ""),
            channeling_state=character.get("channeling_state", ""),
            anchoring_ritual=character.get("anchoring_ritual", ""),
            backstory=character.get("backstory", ""),
            stats=character.get("stats", {}),
            generated_at=character.get("generated_at", ""),
            generator=character.get("generator", "rng"),
        )
        journey = CharacterJourney(self)
        return journey.run_full_journey(sheet, self)

    # ------------------------------------------------------------------
    # Autonomous Operator Mode
    # ------------------------------------------------------------------

    def start_autonomous_mode(self, interval_seconds: int = 300) -> dict[str, Any]:
        """Start autonomous radionics operation — the operator checks world context
        and proposes actions on a timer."""
        if self._autonomous_active:
            return {"status": "already_running", "message": "Autonomous mode is already active"}

        self._autonomous_active = True
        self._autonomous_interval = interval_seconds
        self._autonomous_suggestions: list[dict[str, Any]] = []

        self._session.record_event("autonomous_started", {"interval": interval_seconds})

        # Run first cycle immediately
        suggestion = self._autonomous_cycle()

        # Start the background daemon loop
        try:
            loop = asyncio.get_running_loop()
            self._autonomous_task = loop.create_task(self._run_autonomous_loop())
            logger.info("Autonomous operator background daemon task scheduled successfully.")
        except RuntimeError:
            logger.info(
                "No running event loop found, background autonomous operator loop not scheduled (normal in tests)."
            )

        return {
            "status": "started",
            "interval_seconds": interval_seconds,
            "message": "Autonomous radionics operator activated. I will monitor world events and propose actions.",
            "first_suggestion": suggestion,
        }

    async def _run_autonomous_loop(self):
        """Run autonomous operator actions and journey progression periodically in the background."""
        logger.info("Autonomous operator background task started.")
        while self._autonomous_active:
            try:
                await asyncio.sleep(self._autonomous_interval)
                if not self._autonomous_active:
                    break

                # If there is an active journey, advance it!
                if hasattr(self, "_active_journey") and self._active_journey is not None:
                    if self._active_journey.is_complete:
                        logger.info("Active character journey is complete. Harvesting outcomes...")
                        await asyncio.to_thread(self.harvest_journey)
                    else:
                        logger.info("Advancing active character journey automatically...")
                        await asyncio.to_thread(self.advance_journey)
                else:
                    # Otherwise, run a new autonomous cycle to check astrological transits and start new journeys
                    logger.info("Executing autonomous operator cycle...")
                    await asyncio.to_thread(self._autonomous_cycle)
            except asyncio.CancelledError:
                logger.info("Autonomous operator background task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in autonomous operator cycle: {e}")

    def stop_autonomous_mode(self) -> dict[str, Any]:
        """Stop autonomous operation."""
        self._autonomous_active = False
        if self._autonomous_task:
            self._autonomous_task.cancel()
            self._autonomous_task = None
            logger.info("Autonomous operator background task cancelled.")
        self._session.record_event("autonomous_stopped", {})
        return {
            "status": "stopped",
            "suggestions_generated": len(self._autonomous_suggestions),
            "suggestions": self._autonomous_suggestions[-5:],
        }

    def get_autonomous_status(self) -> dict[str, Any]:
        """Get autonomous mode status."""
        return {
            "active": self._autonomous_active,
            "interval_seconds": self._autonomous_interval,
            "suggestions_count": len(self._autonomous_suggestions),
            "recent_suggestions": self._autonomous_suggestions[-5:],
        }

    def get_autonomous_suggestions(self) -> list[dict[str, Any]]:
        """Get pending autonomous suggestions for user approval."""
        return self._autonomous_suggestions

    def approve_suggestion(self, index: int) -> dict[str, Any]:
        """Approve and execute an autonomous suggestion."""
        if 0 <= index < len(self._autonomous_suggestions):
            suggestion = self._autonomous_suggestions.pop(index)
            action = suggestion.get("action")
            # Execute the suggestion if it has actionable data
            if action == "broadcast_healing" and self._container:
                suggestion["status"] = "executed"
                self._container.radionics.broadcast_healing(
                    target_name=suggestion.get("target", "World Event"),
                    frequency_hz=suggestion.get("frequency", 528),
                    duration_minutes=suggestion.get("duration_minutes", 30),
                )
            elif action == "character_journey":
                if getattr(self, "_active_journey", None):
                    if self._active_journey.is_complete:
                        result = {
                            "status": "approved",
                            "message": "Character journey approved; current journey complete — harvest to continue.",
                        }
                    else:
                        try:
                            stage_result = self._active_journey.advance()
                            suggestion["status"] = "executed"
                            return {
                                "status": "executed",
                                "message": "Character journey approved and advanced one stage.",
                                "suggestion": suggestion,
                                "stage": stage_result,
                            }
                        except Exception as e:  # noqa: BLE001
                            suggestion["status"] = "approved"
                            logger.warning(f"approve_suggestion: advance() failed: {e}")
                            result = {
                                "status": "approved",
                                "message": f"Character journey approved (advance failed: {e}).",
                            }
                else:
                    suggestion["status"] = "approved"
                    result = {"status": "approved", "message": "Journey suggestion acknowledged (no active journey)."}
                return {**result, "suggestion": suggestion}
            else:
                suggestion["status"] = "approved"
            return {"status": suggestion["status"], "suggestion": suggestion}
        return {"error": "Invalid suggestion index"}

    def dismiss_suggestion(self, index: int) -> dict[str, Any]:
        """Dismiss an autonomous suggestion without executing."""
        if 0 <= index < len(self._autonomous_suggestions):
            dismissed = self._autonomous_suggestions.pop(index)
            dismissed["status"] = "dismissed"
            if dismissed.get("action") == "character_journey":
                dismissed["journey_still_active"] = bool(
                    getattr(self, "_active_journey", None) and not self._active_journey.is_complete
                )
            return {"status": "dismissed", "suggestion": dismissed}
        return {"error": "Invalid suggestion index"}

    def analyze_trends(self, session_history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """
        Generate LLM-powered trend analysis from session history.

        The LLM reads actual session data and produces structured analysis
        with patterns, recommendations, and visualizable data points.
        """
        if not session_history:
            try:
                if self._container:
                    from backend.core.services.vajra_service import vajra_service

                    session_history = vajra_service.get_session_history()
            except Exception:
                pass

        if not session_history:
            return {
                "analysis": "No session history available for trend analysis.",
                "patterns": [],
                "recommendations": [],
                "chart_data": {"labels": [], "values": []},
            }

        # Build trend prompt
        history_summary = []
        for s in session_history[-50:]:
            cfg = s.get("config", {})
            history_summary.append(
                {
                    "name": cfg.get("name", s.get("id", "")),
                    "intention": cfg.get("intention", ""),
                    "frequency": cfg.get("audio_config", {}).get("frequency", 0) if isinstance(cfg, dict) else 0,
                    "duration": cfg.get("duration", 0) if isinstance(cfg, dict) else 0,
                    "status": s.get("status", "unknown"),
                }
            )

        if self.llm and (self.llm.client or self.llm.local_model):
            try:
                trend_prompt = f"""Analyze this radionics session history and return a JSON trend report:

Sessions: {json.dumps(history_summary[-20:], default=str)}

Return JSON with:
{{
    "analysis": "2-3 sentence natural-language analysis of patterns",
    "patterns": ["list of identified patterns in frequency usage, intention themes, timing"],
    "recommendations": ["3 actionable recommendations for future sessions"],
    "chart_data": {{"labels": ["list of session names"], "values": [list of durations in minutes]}},
    "most_used_frequency": number,
    "most_common_intention_theme": "string",
    "optimal_timing_note": "string"
}}"""
                system = build_system_prompt(self._session.to_dict())
                raw = self.llm.generate(prompt=trend_prompt, system_prompt=system, max_tokens=600, temperature=0.3)
                return self._safe_json_parse(raw, self._fallback_trends(history_summary))
            except Exception:
                pass

        return self._fallback_trends(history_summary)

    # ------------------------------------------------------------------
    # Autonomous internals
    # ------------------------------------------------------------------

    def _autonomous_cycle(self) -> dict[str, Any] | None:
        """Run one autonomous cycle: check transits → find green windows → auto-launch journeys."""
        try:
            from core.auspicious_timing import get_all_windows
            from core.character_generator import CharacterGenerator

            windows = get_all_windows()
            green = {g: w for g, w in windows.items() if w.get("go") and w.get("quality") in ("excellent", "good")}
            if not green:
                return None

            best_genre = next(iter(green))
            for g in ["healing", "compassion", "wisdom", "protection"]:
                if g in green and green[g]["quality"] == "excellent":
                    best_genre = g
                    break

            window = green[best_genre]
            gen = CharacterGenerator()
            sheet = gen.generate(use_llm=False)
            self.start_character_journey(sheet.to_dict())

            suggestion = {
                "title": f"Auto-Journey: {sheet.name} the {sheet.element.get('name', '')} {sheet.role.get('name', '')}",
                "target": sheet.name,
                "action": "character_journey",
                "genre": best_genre,
                "frequency": sheet.frequency,
                "mantra": sheet.role.get("mantra", "compassion"),
                "reasoning": f"Green window for {best_genre} ({window.get('quality')}). Character: {sheet.backstory[:100]}",
                "character": sheet.to_dict(),
                "timestamp": datetime.now().isoformat(),
            }
            self._autonomous_suggestions.append(suggestion)
            if self.event_bus:
                self.event_bus.publish(
                    OperatorInsightGenerated(
                        insight_type="autonomous_journey_launched",
                        content=suggestion,
                    )
                )
            return suggestion
        except Exception as e:
            logger.warning(f"Autonomous cycle failed: {e}")
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _chat_openai(
        self,
        message: str,
        system_prompt: str,
        tools: list,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Chat with OpenAI, handling tool calls.

        ``model_override`` lets a caller pin a specific model. When ``None``
        (the default) the operator uses ``self.llm.model_name`` — the
        ProviderRegistry's primary model. The operator chat path is NOT
        user-selectable from the UI; supply ``model_override`` explicitly
        to override.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        turn_start = time.time()
        response = self.llm.client.chat.completions.create(
            model=model_override or self.llm.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=800,
            temperature=0.7,
        )
        try:
            _usage = getattr(response, "usage", None)
            _record_operator_usage(
                provider="openai",
                model=model_override or self.llm.model_name,
                prompt_tokens=getattr(_usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(_usage, "completion_tokens", 0) or 0,
                latency_ms=(time.time() - turn_start) * 1000.0,
            )
        except Exception:  # noqa: BLE001
            logger.debug("usage record failed in _chat_openai", exc_info=True)

        choice = response.choices[0]

        # Handle tool calls
        if choice.message.tool_calls:
            tool_results = []
            for tool_call in choice.message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                result = self._dispatcher.dispatch(func_name, func_args)
                tool_results.append(
                    {
                        "tool": func_name,
                        "arguments": func_args,
                        "result": result,
                    }
                )

            return {
                "reply": f"I've executed {len(tool_results)} tool(s): " + ", ".join(t["tool"] for t in tool_results),
                "type": "tool_calls",
                "tool_results": tool_results,
            }

        return {"reply": choice.message.content, "type": "text"}

    def _chat_anthropic(
        self,
        message: str,
        system_prompt: str,
        tools: list,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Chat with Anthropic Claude, handling tool use.

        ``model_override`` lets a caller pin a specific model. When ``None``
        (the default) the operator uses ``self.llm.model_name`` — the
        ProviderRegistry's primary model. The operator chat path is NOT
        user-selectable from the UI; supply ``model_override`` explicitly
        to override.
        """
        turn_start = time.time()
        response = self.llm.client.messages.create(
            model=model_override or self.llm.model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
            tools=tools,
            max_tokens=800,
            temperature=0.7,
        )
        try:
            _usage = getattr(response, "usage", None)
            _record_operator_usage(
                provider="anthropic",
                model=model_override or self.llm.model_name,
                prompt_tokens=getattr(_usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(_usage, "output_tokens", 0) or 0,
                latency_ms=(time.time() - turn_start) * 1000.0,
            )
        except Exception:  # noqa: BLE001
            logger.debug("usage record failed in _chat_anthropic", exc_info=True)

        # Check for tool use blocks
        tool_results = []
        text_parts = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                func_name = block.name
                func_args = block.input
                result = self._dispatcher.dispatch(func_name, func_args)
                tool_results.append(
                    {
                        "tool": func_name,
                        "arguments": func_args,
                        "result": result,
                    }
                )

        reply = " ".join(text_parts) if text_parts else ""

        if tool_results:
            reply = (
                (reply + "\n\n" if reply else "")
                + f"I've executed {len(tool_results)} tool(s): "
                + ", ".join(t["tool"] for t in tool_results)
            )

        return {
            "reply": reply.strip() or "(no text response)",
            "type": "tool_calls" if tool_results else "text",
            "tool_results": tool_results if tool_results else None,
        }

    def _safe_json_parse(self, raw: str, default: dict) -> dict:
        """Safely parse JSON from LLM response, handling markdown fences."""
        raw = raw.strip()
        # Remove markdown code fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON object from the text
            import re

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return default

    def _fallback_analysis(self, intention: str) -> dict[str, Any]:
        """Fallback analysis when LLM is unavailable."""
        analysis = self._fallback_parse_intention(intention)
        from core.radionics_engine import SignatureCalculator

        calc = SignatureCalculator()
        sig_rate = calc.text_to_rate(intention, num_dials=3, algorithm="mixed")

        return {
            "analysis": analysis,
            "suggested_rates": [
                {
                    "values": sig_rate.values,
                    "name": f"Signature: {intention[:30]}",
                    "source": "signature",
                    "reasoning": "Derived from intention text (LLM unavailable — using algorithmic fallback)",
                }
            ],
            "recommended_frequency": analysis.get("recommended_frequency", 528),
            "recommended_mantra": "compassion",
            "recommended_modalities": ["scalar_waves", "radionics"],
            "session_id": str(uuid.uuid4()),
            "note": "LLM unavailable — using algorithmic fallback",
        }

    def _fallback_trends(self, history: list[dict]) -> dict[str, Any]:
        """Generate trend analysis without LLM."""
        if not history:
            return {
                "analysis": "No data.",
                "patterns": [],
                "recommendations": [],
                "chart_data": {"labels": [], "values": []},
            }

        freqs = [h.get("frequency", 0) for h in history if h.get("frequency")]
        durations = [h.get("duration", 0) for h in history if h.get("duration")]
        names = [h.get("name", f"Session {i}") for i, h in enumerate(history)]

        most_freq = max(set(freqs), key=freqs.count) if freqs else 528
        avg_dur = sum(durations) / len(durations) if durations else 0

        return {
            "analysis": f"Across {len(history)} sessions, {most_freq}Hz was the most-used frequency. Average session duration: {avg_dur:.0f}s.",
            "patterns": [f"Frequency {most_freq}Hz dominates", f"Average duration {avg_dur:.0f}s"],
            "recommendations": [
                "Try varying frequencies more",
                "Consider longer sessions for deeper effects",
                "Track intention themes over time",
            ],
            "chart_data": {"labels": names[-10:], "values": durations[-10:]},
            "most_used_frequency": most_freq,
            "most_common_intention_theme": "healing",
            "optimal_timing_note": "Consider planetary hours for timing optimization",
        }

    def _fallback_parse_intention(self, intention: str) -> dict[str, Any]:
        """Keyword-based intention parsing (no LLM required)."""
        low = intention.lower()
        chakra_map = {
            "root": "muladhara",
            "ground": "muladhara",
            "survival": "muladhara",
            "security": "muladhara",
            "sacral": "svadhisthana",
            "creativity": "svadhisthana",
            "emotion": "svadhisthana",
            "solar": "manipura",
            "power": "manipura",
            "confidence": "manipura",
            "will": "manipura",
            "heart": "anahata",
            "love": "anahata",
            "grief": "anahata",
            "compassion": "anahata",
            "throat": "vishuddha",
            "express": "vishuddha",
            "speak": "vishuddha",
            "truth": "vishuddha",
            "third eye": "ajna",
            "intuition": "ajna",
            "clarity": "ajna",
            "vision": "ajna",
            "crown": "sahasrara",
            "spirit": "sahasrara",
            "connect": "sahasrara",
            "divine": "sahasrara",
        }

        freq_map = {
            "fear": 396,
            "guilt": 396,
            "liberation": 396,
            "change": 417,
            "trauma": 417,
            "heal": 528,
            "dna": 528,
            "love": 528,
            "repair": 528,
            "relationship": 639,
            "connection": 639,
            "intuition": 741,
            "express": 741,
            "awaken": 741,
            "spirit": 852,
            "order": 852,
            "divine": 963,
            "unity": 963,
            "oneness": 963,
        }

        best_chakra = "anahata"
        best_freq = 528
        for keyword, chakra in chakra_map.items():
            if keyword in low:
                best_chakra = chakra
                break
        for keyword, freq in freq_map.items():
            if keyword in low:
                best_freq = freq
                break

        return {
            "target": "subject",
            "condition": intention,
            "primary_system": "determined by intention",
            "primary_chakra": best_chakra,
            "recommended_frequency": best_freq,
            "recommended_mantra_tradition": "compassion",
            "severity": 5,
            "modalities": ["scalar_waves", "radionics", "chakra_balancing"],
            "explanation": f"Keyword-based analysis of: {intention}",
        }

    def _fallback_insight(self, state: dict) -> dict[str, Any]:
        """Generate insight without LLM based on rule-based interpretation."""
        parts = []
        gv = state.get("gv_measurement", 0)
        rng = state.get("rng_state", {})

        if gv:
            if gv > 700:
                parts.append("GV is high — strong resonance detected.")
            elif gv > 400:
                parts.append("GV is moderate — session is active and stable.")
            else:
                parts.append("GV is low — consider increasing intensity or switching rates.")

        if rng:
            needle = rng.get("state", "")
            if needle == "floating":
                parts.append(
                    "RNG shows floating needle — this indicates a release point. Good time to conclude or shift intention."
                )
            elif needle == "rock_slam":
                parts.append(
                    "RNG shows rock slam — heavy charge detected. Continue broadcasting, the resistance is processing."
                )
            elif needle == "rising":
                parts.append("RNG needle rising — energy is building. Continue the current rate configuration.")

        if not parts:
            parts.append("Session is running. Continue with current configuration.")

        return {
            "insight": " ".join(parts),
            "type": "rule_based",
            "timestamp": datetime.now().isoformat(),
        }
