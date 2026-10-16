"""Contract tests for the single LLM tool registry (``core.tool_registry``).

The surface snapshots below are deliberate: adding, removing or moving a tool
between surfaces must fail here first. Tool names are public (prompts and
stored conversations reference them), so update a snapshot only for an
intended change, and say so in the commit.
"""

from __future__ import annotations

import inspect
import json

import pytest

from core import tool_registry as registry

# ---------------------------------------------------------------------------
# Surface snapshots
# ---------------------------------------------------------------------------

#: Advertised to the chat model, in priority order (the order is part of the
#: contract: the chat path caps the list).
CHAT_SNAPSHOT = (
    "run_working",
    "forge_witness",
    "generate_single_outlook",
    "generate_prayer",
    "generate_image",
    "generate_epic_outlook",
    "generate_blessing",
    "generate_teaching",
    "forge_sigil",
    "speak_text",
    "cast_tarot_spread",
    "cast_i_ching",
    "cast_geomancy",
    "search_grimoire_correspondences",
    "search_knowledge",
    "web_search",
    "check_auspicious_timing",
    "get_auspicious_timing_details",
    "get_celestial_night_sky",
    "get_dharani_text",
    "get_active_world_crises",
    "trigger_living_ritual_broadcast",
    "check_saka_dawa",
    "get_planetary_hours_and_transits",
    "get_random_buddha",
    "create_population",
    "list_populations",
    "update_population",
    "get_population_statistics",
    "get_system_status",
    "start_automation",
    "stop_automation",
    "get_automation_status",
    "play_chakra_healing_audio",
)

#: Executable through the chat dispatcher.
AGENT_SNAPSHOT = frozenset(
    {
        "add_agent_suggestion",
        "advance_journey",
        "broadcast_healing",
        "broadcast_liberation",
        "calculate_natal_chart",
        "cast_geomancy",
        "cast_i_ching",
        "cast_tarot_spread",
        "chakra_balancing_protocol",
        "check_auspicious_timing",
        "check_saka_dawa",
        "create_blessing_slideshow",
        "create_healing_session",
        "create_narrative_character",
        "create_narrative_location",
        "create_population",
        "create_rng_session",
        "find_balancing_rates",
        "forge_sigil",
        "forge_witness",
        "generate_audio",
        "generate_blessing",
        "generate_buddha_narrative",
        "generate_character",
        "generate_epic_outlook",
        "generate_image",
        "generate_meditation_script",
        "generate_prayer",
        "generate_scalar_waves",
        "generate_single_outlook",
        "generate_teaching",
        "get_88_buddhas_liturgy",
        "get_active_world_crises",
        "get_all_genre_windows",
        "get_auspicious_timing_details",
        "get_automation_stats",
        "get_automation_status",
        "get_available_intentions",
        "get_blessing_traditions",
        "get_buddha_recitation_status",
        "get_celestial_night_sky",
        "get_chakra_info",
        "get_current_conditions",
        "get_current_slide",
        "get_dharani_text",
        "get_healing_modalities",
        "get_journey_status",
        "get_meridian_info",
        "get_narrative_loop_status",
        "get_planetary_hours_and_transits",
        "get_planetary_positions",
        "get_population_statistics",
        "get_random_buddha",
        "get_ritual_schedule",
        "get_ritual_status",
        "get_rng_reading",
        "get_rng_summary",
        "get_sacred_frequencies",
        "get_system_status",
        "get_world_context",
        "list_narrative_characters",
        "list_narrative_locations",
        "list_populations",
        "list_practices",
        "measure_general_vitality",
        "pause_automation",
        "play_audio_preset",
        "play_chakra_healing_audio",
        "recite_buddha_name",
        "resume_automation",
        "run_full_journey",
        "run_working",
        "search_grimoire_correspondences",
        "search_knowledge",
        "search_rate_database",
        "set_audio_frequency",
        "set_audio_modulation",
        "speak_text",
        "start_automation",
        "start_buddha_recitation",
        "start_character_journey",
        "start_narrative_loop",
        "start_ritual_engine",
        "stop_automation",
        "stop_buddha_recitation",
        "stop_narrative_loop",
        "stop_ritual_engine",
        "stop_rng_session",
        "stop_slideshow",
        "text_to_rate",
        "trigger_living_ritual_broadcast",
        "trigger_ritual",
        "update_population",
        "web_fetch",
        "web_search",
    }
)

#: Advertised to and executable by the radionics operator.
OPERATOR_SNAPSHOT = frozenset(
    {
        "advance_journey",
        "broadcast_healing",
        "broadcast_liberation",
        "calculate_natal_chart",
        "chakra_balancing_protocol",
        "check_auspicious_timing",
        "check_saka_dawa",
        "create_healing_session",
        "create_rng_session",
        "find_balancing_rates",
        "generate_audio",
        "generate_blessing",
        "generate_buddha_narrative",
        "generate_character",
        "generate_meditation_script",
        "generate_prayer",
        "generate_scalar_waves",
        "generate_teaching",
        "get_88_buddhas_liturgy",
        "get_all_genre_windows",
        "get_available_intentions",
        "get_blessing_traditions",
        "get_buddha_recitation_status",
        "get_chakra_info",
        "get_current_conditions",
        "get_healing_modalities",
        "get_journey_status",
        "get_meridian_info",
        "get_planetary_positions",
        "get_random_buddha",
        "get_rng_reading",
        "get_rng_summary",
        "get_sacred_frequencies",
        "get_world_context",
        "measure_general_vitality",
        "prepare_crystal_broadcast",
        "recite_buddha_name",
        "run_full_journey",
        "search_knowledge",
        "search_rate_database",
        "start_buddha_recitation",
        "start_character_journey",
        "stop_buddha_recitation",
        "text_to_rate",
        "web_fetch",
        "web_search",
    }
)

#: Approval-gated actions of the autonomous operator.
AUTONOMOUS_SNAPSHOT = frozenset({"broadcast_healing"})

#: Alias -> tool. Models (and stored conversations) use these names.
ALIAS_SNAPSHOT = {
    "list_targets": "list_populations",
    "show_targets": "list_populations",
    "show_populations": "list_populations",
    "get_targets": "list_populations",
    "list_population": "list_populations",
    "start_blessing": "start_automation",
    "begin_session": "start_automation",
    "stop_blessing": "stop_automation",
    "get_session": "get_automation_status",
    "session_status": "get_automation_status",
    "list_session": "get_automation_stats",
    "get_statistics": "get_system_status",
    "broadcast_crystal": "broadcast_healing",
    "set_crystal_intent": "broadcast_healing",
    "set_scalar_frequency": "set_audio_frequency",
    "set_rng_bias": "create_rng_session",
    "calibrate_rng": "create_rng_session",
    "get_night_sky": "get_celestial_night_sky",
    "night_sky": "get_celestial_night_sky",
    "celestial_sky": "get_celestial_night_sky",
    "get_dharani": "get_dharani_text",
    "dharani_text": "get_dharani_text",
    "dharani": "get_dharani_text",
    "timing_wheel": "get_auspicious_timing_details",
    "get_timing_wheel": "get_auspicious_timing_details",
    "world_crises": "get_active_world_crises",
    "get_world_crises": "get_active_world_crises",
    "active_crises": "get_active_world_crises",
    "living_ritual": "trigger_living_ritual_broadcast",
    "living_ritual_broadcast": "trigger_living_ritual_broadcast",
}


def test_chat_surface_snapshot():
    assert tuple(registry.tool_names(registry.CHAT)) == CHAT_SNAPSHOT


def test_agent_surface_snapshot():
    assert frozenset(registry.tool_names(registry.AGENT)) == AGENT_SNAPSHOT


def test_operator_surface_snapshot():
    assert frozenset(registry.tool_names(registry.OPERATOR)) == OPERATOR_SNAPSHOT


def test_autonomous_surface_snapshot():
    assert frozenset(registry.tool_names(registry.AUTONOMOUS)) == AUTONOMOUS_SNAPSHOT


def test_alias_snapshot():
    aliases = {alias: spec.name for spec in registry.specs() for alias in spec.aliases}
    assert aliases == ALIAS_SNAPSHOT
    for alias, name in ALIAS_SNAPSHOT.items():
        assert registry.resolve_name(alias) == name


def test_every_tool_is_on_a_known_surface():
    every = set(registry.tool_names())
    assert every == AGENT_SNAPSHOT | OPERATOR_SNAPSHOT
    assert set(CHAT_SNAPSHOT) <= AGENT_SNAPSHOT, "an advertised chat tool must be executable"


# ---------------------------------------------------------------------------
# Every tool: a handler and a valid schema
# ---------------------------------------------------------------------------

ALL_SPECS = registry.specs()


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda s: s.name)
def test_tool_has_a_callable_handler(spec):
    module, _, attr = spec.handler.partition(":")
    assert module and attr, f"{spec.name}: handler must be 'module:function', got {spec.handler!r}"
    fn = registry.resolve_handler(spec)
    assert callable(fn)


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda s: s.name)
def test_tool_schema_is_valid(spec):
    assert spec.name.isidentifier()
    assert isinstance(spec.description, str) and spec.description.strip()
    params = spec.parameters
    json.dumps(params)  # serializable as sent to the providers
    assert params.get("type") == "object"
    props = params.get("properties")
    assert isinstance(props, dict)
    for prop_name, prop in props.items():
        assert isinstance(prop, dict), f"{spec.name}.{prop_name} is not a schema object"
        assert "type" in prop or "enum" in prop or "anyOf" in prop, f"{spec.name}.{prop_name} has no type"
    required = params.get("required", [])
    assert isinstance(required, list)
    assert set(required) <= set(props), f"{spec.name}: required names missing from properties"


@pytest.mark.parametrize("spec", ALL_SPECS, ids=lambda s: s.name)
def test_handler_signature_matches_schema(spec):
    """The handler accepts every advertised argument and requires only required ones."""
    sig = inspect.signature(registry.resolve_handler(spec))
    params = sig.parameters
    var_kw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    props = set(spec.parameters.get("properties") or {})
    if not var_kw:
        assert props <= set(params), f"{spec.name}: handler ignores {sorted(props - set(params))}"
    must = {
        n for n, p in params.items() if p.default is p.empty and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
    }
    assert must <= set(spec.parameters.get("required") or []), f"{spec.name}: handler requires {sorted(must)}"


def test_operator_openai_format_matches_plain():
    plain = registry.schemas(registry.OPERATOR)
    openai = registry.schemas(registry.OPERATOR, fmt="openai")
    anthropic = registry.schemas(registry.OPERATOR, fmt="anthropic")
    assert [t["function"] for t in openai] == plain
    assert all(t["type"] == "function" for t in openai)
    assert [
        {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]} for t in anthropic
    ] == plain


def test_schemas_are_copies():
    first = registry.schemas(registry.CHAT)
    first[0]["parameters"]["properties"]["mutated"] = {"type": "string"}
    assert "mutated" not in registry.schemas(registry.CHAT)[0]["parameters"]["properties"]


def test_flags():
    assert registry.once_per_sitting_names() == {
        "generate_single_outlook",
        "generate_prayer",
        "generate_blessing",
        "generate_epic_outlook",
        "run_working",
    }
    assert registry.timeout_for("generate_single_outlook", 25.0) == 200.0
    assert registry.timeout_for("generate_epic_outlook", 25.0) == 300.0
    assert registry.timeout_for("list_populations", 25.0) == 25.0
    assert {s.name for s in registry.specs() if s.requires_approval} == AUTONOMOUS_SNAPSHOT
    for spec in registry.specs():
        if spec.result_provenance is not None:
            assert set(spec.result_provenance.values()) <= registry.PROVENANCE_KINDS, spec.name


# ---------------------------------------------------------------------------
# Lookup, approval, argument preparation
# ---------------------------------------------------------------------------


def test_unknown_and_off_surface_tools_are_rejected():
    with pytest.raises(registry.UnknownToolError):
        registry.get_spec("no_such_tool")
    # forge_sigil is a chat tool, not an operator tool.
    with pytest.raises(registry.UnknownToolError):
        registry.get_spec("forge_sigil", registry.OPERATOR)
    # prepare_crystal_broadcast is operator-only.
    with pytest.raises(registry.UnknownToolError):
        registry.get_spec("prepare_crystal_broadcast", registry.AGENT)


def test_autonomous_call_requires_approval():
    with pytest.raises(registry.ApprovalRequiredError):
        registry.call("broadcast_healing", {"target_name": "x"}, surface=registry.AUTONOMOUS)


def _args(name: str, args: dict) -> dict:
    return registry.prepare_arguments(registry.get_spec(name), args)


def test_global_arg_aliases_apply_only_where_the_tool_lacks_the_name():
    # run_working takes ``intention`` and ``target`` itself: they pass through.
    assert _args("run_working", {"intention": "peace", "target": "Kyiv"}) == {"intention": "peace", "target": "Kyiv"}
    # The outlook tool takes neither: they map onto its real parameters.
    out = _args("generate_single_outlook", {"intention": "peace", "target": ["pop_1"]})
    assert out == {"custom_context": "peace", "population_ids": ["pop_1"]}
    # forge_sigil keeps its intention (it used to be renamed away).
    assert _args("forge_sigil", {"intention": "clarity"}) == {"intention": "clarity"}
    # ``duration`` stays ``duration`` where that is the parameter.
    assert _args("play_chakra_healing_audio", {"chakra_name": "heart", "duration": 12}) == {
        "chakra_name": "heart",
        "duration": 12,
    }


def test_tool_arg_aliases_fill_only_absent_arguments():
    assert _args("get_celestial_night_sky", {"lat": 1.5, "lng": 2.5}) == {"latitude": 1.5, "longitude": 2.5}
    assert _args("get_celestial_night_sky", {"latitude": 3.0, "lat": 1.5}) == {"latitude": 3.0}
    assert _args("get_dharani_text", {"id": "cundi_dharani"}) == {"dharani_id_or_name": "cundi_dharani"}


def test_arguments_are_cleaned_and_coerced():
    out = _args("run_working", {"duration_minutes": "7", "broadcast": "false", "bogus": 1, "target": None})
    assert out == {"duration_minutes": 7, "broadcast": False}
    # A model can never pass the DI container.
    assert "container" not in _args("broadcast_healing", {"target_name": "x", "container": object()})


def test_container_is_injected_for_container_handlers():
    class _Radionics:
        def broadcast_healing(self, **kwargs):
            return {"called_with": kwargs}

    class _Container:
        radionics = _Radionics()

    out = registry.call("broadcast_healing", {"target_name": "Tara"}, surface=registry.OPERATOR, container=_Container())
    assert out["called_with"]["target_name"] == "Tara"
    assert out["called_with"]["intensity"] == 0.8


async def test_acall_awaits_async_handlers_and_runs_sync_ones():
    res = await registry.acall("get_dharani", {"dharani_id_or_name": "list"}, surface=registry.AGENT)
    assert res["status"] == "list"


# ---------------------------------------------------------------------------
# Consumers read the registry
# ---------------------------------------------------------------------------


def test_legacy_views_are_derived_from_the_registry():
    from backend.core.llm_agent import tools

    assert set(tools.TOOL_REGISTRY) == AGENT_SNAPSHOT | {a for a, n in ALIAS_SNAPSHOT.items() if n in AGENT_SNAPSHOT}
    assert tools.ESSENTIAL_TOOL_ORDER == list(CHAT_SNAPSHOT)
    assert [s["name"] for s in tools.get_tool_schemas()] == list(CHAT_SNAPSHOT)
    assert {s["name"] for s in tools.get_tool_schemas(essential_only=False)} == AGENT_SNAPSHOT


def test_operator_dispatcher_uses_the_operator_surface():
    from modules.radionics_operator import ToolDispatcher

    dispatcher = ToolDispatcher(container=None)
    assert dispatcher.dispatch("forge_sigil", {"intention": "x"}) == {"error": "Unknown tool: forge_sigil"}
    assert dispatcher.dispatch("broadcast_healing", {"target_name": "x"}) == {
        "error": "No container set — services unavailable"
    }
    assert "buddha" in dispatcher.dispatch("get_random_buddha", {})
