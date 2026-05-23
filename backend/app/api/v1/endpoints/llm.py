"""
LLM Agent API Endpoints
Provides chat-based interface with tool calling and rule-based local fallback.
"""

import json
import logging
import os
import re
import time
from typing import Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    import aiohttp
except ImportError:
    aiohttp = None

from backend.core.llm_agent.tools import TOOL_REGISTRY, get_tool_schemas
from backend.core.services.blessing_scheduler import get_scheduler
from backend.core.services.rng_attunement_service import get_rng_service
from backend.core.services.population_manager import get_population_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    api_key: Optional[str] = None
    provider: Optional[str] = "auto"  # 'openai', 'anthropic', 'local', 'auto'
    model: Optional[str] = None


class ToolCallLog(BaseModel):
    tool_name: str
    arguments: dict
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[ToolCallLog]


def execute_tool_locally(name: str, args: dict) -> Any:
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
        pops = pm.get_all_populations()
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
        return pop
    elif name == "update_population":
        pm = get_population_manager()
        pop = pm.update_population(args.get("population_id"), **args)
        return pop
    elif name == "start_automation":
        from backend.core.services.blessing_scheduler import get_scheduler, SchedulerConfig, SchedulerMode
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
        result = scheduler.start_automation(config=config)
        return {"session_id": result.get("session_id"), "populations_in_queue": result.get("populations_in_queue", 0)}
    elif name == "stop_automation":
        from backend.core.services.blessing_scheduler import get_scheduler
        scheduler = get_scheduler()
        result = scheduler.stop_automation(args.get("session_id"))
        return result
    elif name == "get_automation_status":
        from backend.core.services.blessing_scheduler import get_scheduler
        scheduler = get_scheduler()
        return scheduler.get_status(args.get("session_id"))
    elif name == "get_automation_stats":
        from backend.core.services.blessing_scheduler import get_scheduler
        scheduler = get_scheduler()
        return scheduler.get_stats(args.get("session_id"))
    elif name == "create_rng_session":
        from backend.core.services.rng_attunement_service import get_rng_service
        service = get_rng_service()
        result = service.create_session(
            session_id=args.get("session_id"),
            baseline_tone_arm=args.get("baseline_tone_arm", 5.0),
            sensitivity=args.get("sensitivity", 1.0),
        )
        return result
    elif name == "get_rng_reading":
        from backend.core.services.rng_attunement_service import get_rng_service
        service = get_rng_service()
        return service.get_reading(args.get("session_id"))
    elif name == "stop_rng_session":
        from backend.core.services.rng_attunement_service import get_rng_service
        service = get_rng_service()
        return service.stop_session(args.get("session_id"))
    else:
        # Fallback: call the tool function directly
        return tool_func(**args)


def run_rule_based_fallback(query: str) -> ChatResponse:
    """
    Intelligent fallback system that matches natural language commands
    and executes tools directly on the backend.
    """
    query_lower = query.lower().strip()
    tool_calls = []
    response_text = ""

    # 1. Start Automation
    if re.search(r"\b(start|begin|activate|turn\s*on|enable)\s*(the\s*)?(automation|scheduler|rotation|cycle)\b", query_lower):
        try:
            res = execute_tool_locally("start_automation", {})
            tool_calls.append(ToolCallLog(
                tool_name="start_automation",
                arguments={},
                status="success",
                result=res
            ))
            response_text = (
                f"🔮 **Vajra.Stream Automation Initiated**\n\n"
                f"I have successfully activated the automated blessing rotation.\n"
                f"- **Session ID**: `{res.get('session_id')}`\n"
                f"- **Populations in queue**: {res.get('populations_in_queue')}\n"
                f"- **Status**: Continuous rotation started."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(
                tool_name="start_automation",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to start automation: {str(e)}"

    # 2. Stop Automation
    elif re.search(r"\b(stop|pause|suspend|disable|turn\s*off|end)\s*(the\s*)?(automation|scheduler|rotation|cycle)\b", query_lower):
        try:
            scheduler = get_scheduler()
            active_sessions = list(scheduler.sessions.keys())
            if active_sessions:
                session_id = active_sessions[0]
                res = execute_tool_locally("stop_automation", {"session_id": session_id})
                tool_calls.append(ToolCallLog(
                    tool_name="stop_automation",
                    arguments={"session_id": session_id},
                    status="success",
                    result=res
                ))
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
            tool_calls.append(ToolCallLog(
                tool_name="stop_automation",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to stop automation: {str(e)}"

    # 3. List Populations
    elif re.search(r"\b(list|show|view|get)\s*(the\s*)?(populations|targets)\b", query_lower):
        try:
            res = execute_tool_locally("list_populations", {})
            tool_calls.append(ToolCallLog(
                tool_name="list_populations",
                arguments={},
                status="success",
                result=res
            ))
            if res:
                response_text = "👥 **Vajra.Stream Target Populations**\n\nHere are the registered blessing target populations:\n\n"
                for pop in res:
                    response_text += (
                        f"- **{pop.get('name')}** (Category: `{pop.get('category')}`)\n"
                        f"  - Intentions: {', '.join(pop.get('intentions', []))}\n"
                        f"  - Priority: {pop.get('priority')}/10 | Photo Count: {pop.get('photo_count')}\n"
                    )
            else:
                response_text = "ℹ️ No populations are registered. Go to Targets to add one!"
        except Exception as e:
            tool_calls.append(ToolCallLog(
                tool_name="list_populations",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to list populations: {str(e)}"

    # 4. Get Population Statistics
    elif re.search(r"\b(stats|statistics|overall\s*stats|summary)\s*(of\s*populations|across\s*populations|of\s*blessings)?\b", query_lower):
        try:
            res = execute_tool_locally("get_population_statistics", {})
            tool_calls.append(ToolCallLog(
                tool_name="get_population_statistics",
                arguments={},
                status="success",
                result=res
            ))
            response_text = (
                f"📈 **Vajra.Stream System-Wide Blessing Stats**\n\n"
                f"- **Total Blessings Sent**: {res.get('total_blessings_sent', 0)}\n"
                f"- **Total Mantras Repeated**: {res.get('total_mantras_repeated', 0)}\n"
                f"- **Total Blessing Duration**: {res.get('total_blessing_duration', 0):.1f} seconds\n"
                f"- **Active Populations Count**: {res.get('total_populations', 0)}"
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(
                tool_name="get_population_statistics",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to retrieve statistics: {str(e)}"

    # 5. Start RNG Session
    elif re.search(r"\b(start|create|begin|activate)\s*(a\s*)?(rng|random\s*number\s*generator|attunement|needle)\s*(session)?\b", query_lower):
        try:
            res = execute_tool_locally("create_rng_session", {"baseline_tone_arm": 5.0, "sensitivity": 1.0})
            tool_calls.append(ToolCallLog(
                tool_name="create_rng_session",
                arguments={"baseline_tone_arm": 5.0, "sensitivity": 1.0},
                status="success",
                result=res
            ))
            response_text = (
                f"🔮 **RNG Attunement Session Created**\n\n"
                f"The random number generator is now capturing local quantum fluctuations.\n"
                f"- **Session ID**: `{res.get('session_id')}`\n"
                f"- Tone Arm Baseline calibrated to 5.0."
            )
        except Exception as e:
            tool_calls.append(ToolCallLog(
                tool_name="create_rng_session",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to start RNG session: {str(e)}"

    # 6. Stop RNG Session
    elif re.search(r"\b(stop|end|terminate|deactivate)\s*(the\s*)?(rng|random\s*number\s*generator|attunement|needle)\s*(session)?\b", query_lower):
        try:
            service = get_rng_service()
            active_rng = service.get_all_sessions()
            if active_rng:
                session_id = active_rng[-1]  # Take the last active session
                res = execute_tool_locally("stop_rng_session", {"session_id": session_id})
                tool_calls.append(ToolCallLog(
                    tool_name="stop_rng_session",
                    arguments={"session_id": session_id},
                    status="success",
                    result=res
                ))
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
            tool_calls.append(ToolCallLog(
                tool_name="stop_rng_session",
                arguments={},
                status="error",
                error=str(e)
            ))
            response_text = f"❌ Failed to stop RNG session: {str(e)}"

    # 7. Predefined Dharma Tales Fallback
    elif re.search(r"\b(tell|generate|show|give|read)\s*(me\s*)?(a\s*)?(dharma\s*tale|teaching|story|wisdom|parable|tale)\b", query_lower):
        parable = (
            "🏯 **Zen Wisdom: A Cup of Tea**\n\n"
            "Nan-in, a Japanese master during the Meiji era, received a university professor who came to inquire about Zen.\n\n"
            "Nan-in served tea. He poured his visitor's cup full, and then kept on pouring.\n\n"
            "The professor watched the overflow until he no longer could restrain himself. "
            "\"It is overfull. No more will go in!\"\n\n"
            "\"Like this cup,\" Nan-in said, \"you are full of your own opinions and speculations. "
            "How can I show you Zen unless you first empty your cup?\""
        )
        response_text = parable

    # 8. Help / Introduction
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
            "- 📚 `Tell me a dharma tale` - Generates a story or parable for your contemplation."
        )

    return ChatResponse(response=response_text, tool_calls=tool_calls)


@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest):
    """
    Chat with the AI Command Center to run magical computer operations.
    Integrates with OpenAI/Anthropic tool calling with local rule-based fallback.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Message list cannot be empty")

    query = request.messages[-1].content
    
    # Retrieve key from request or env
    api_key = request.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    provider = request.provider or "auto"

    # If no provider API key and provider isn't local model, use rule-based fallback
    if not api_key and provider != "local":
        logger.info("No API keys found. Falling back to rule-based parser.")
        return run_rule_based_fallback(query)

    # Convert request messages to format required by standard libraries
    # Let's support OpenAI or Anthropic tool calling
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

    tool_logs: List[ToolCallLog] = []

    # Handle OpenAI Client Tool Calling
    if api_key and (provider == "openai" or (provider == "auto" and os.getenv("OPENAI_API_KEY"))):
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            # Format messages
            openai_messages = [{"role": "system", "content": system_prompt}]
            for msg in request.messages:
                openai_messages.append({"role": msg.role, "content": msg.content})

            # Format tools for OpenAI
            openai_tools = []
            for schema in tool_schemas:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": schema["name"],
                        "description": schema["description"],
                        "parameters": schema["parameters"]
                    }
                })

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"OpenAI turn {turn}...")
                response = client.chat.completions.create(
                    model=request.model or "gpt-4o-mini",
                    messages=openai_messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                    temperature=0.7
                )
                
                msg = response.choices[0].message
                openai_messages.append(msg)

                # Check if tool calls exist
                if not msg.tool_calls:
                    return ChatResponse(response=msg.content or "", tool_calls=tool_logs)

                # Process tool calls
                for tool_call in msg.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    try:
                        result = execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="success",
                            result=result
                        ))
                        # Append tool output message
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": json.dumps(result)
                        })
                    except Exception as ex:
                        logger.error(f"Error executing tool {name}: {ex}")
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="error",
                            error=str(ex)
                        ))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": json.dumps({"error": str(ex)})
                        })

        except Exception as e:
            logger.error(f"OpenAI execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = run_rule_based_fallback(query)
            fallback_res.response = f"*(OpenAI Call Failed: {str(e)} - Switched to Local Interpreter)*\n\n" + fallback_res.response
            return fallback_res

    # Handle LM Studio Local Model Tool Calling
    elif provider == "local" or provider == "lm_studio" or (provider == "auto" and not api_key):
        try:
            import openai as openai_lib
            lm_studio_config = {
                "base_url": os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234"),
                "api_key": "not-required",
                "timeout": 300,
            }
            client = openai_lib.OpenAI(
                api_key=lm_studio_config["api_key"],
                base_url=f"{lm_studio_config['base_url']}/v1",
                timeout=lm_studio_config["timeout"]
            )

            # Format messages - LM Studio/Qwen models expect only user messages after system
            openai_messages = [{"role": "system", "content": system_prompt}]
            for msg in request.messages:
                if msg.role == "user":
                    openai_messages.append({"role": "user", "content": msg.content})
                # Skip existing assistant messages to avoid confusing the model's Jinja template

            # Format tools for OpenAI-compatible LM Studio API
            openai_tools = []
            for schema in tool_schemas:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": schema["name"],
                        "description": schema["description"],
                        "parameters": schema["parameters"]
                    }
                })

            # Default to qwen model for tool calling
            model_name = request.model or "openyourmind-qwen3.6-35b-a3b-kuato-dpo-abliterated-uncensored-i1"

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"LM Studio turn {turn} with model {model_name}...")
                logger.info(f"Sending messages to LM Studio: {len(openai_messages)} messages, {len(openai_tools)} tools")
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=openai_messages,
                        tools=openai_tools if openai_tools else None,
                        tool_choice="auto" if openai_tools else None,
                        temperature=0.7
                    )
                    logger.info(f"LM Studio response received, finish_reason: {response.choices[0].finish_reason}")
                except Exception as timeout_err:
                    err_str = str(timeout_err).lower()
                    if "timeout" in err_str or "timed out" in err_str or "timed-out" in err_str:
                        logger.error(f"LM Studio request timed out: {timeout_err}")
                        fallback_res = run_rule_based_fallback(query)
                        fallback_res.response = f"*(LM Studio Request Timed Out - Switched to Local Interpreter)*\n\n" + fallback_res.response
                        return fallback_res
                    raise
                
                msg = response.choices[0].message
                openai_messages.append(msg)

                # Check if tool calls exist
                if not msg.tool_calls:
                    return ChatResponse(response=msg.content or "", tool_calls=tool_logs)

                # Process tool calls
                for tool_call in msg.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    try:
                        result = execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="success",
                            result=result
                        ))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": json.dumps(result)
                        })
                    except Exception as ex:
                        logger.error(f"Error executing tool {name}: {ex}")
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="error",
                            error=str(ex)
                        ))
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": json.dumps({"error": str(ex)})
                        })

        except Exception as e:
            err_str = str(e).lower()
            logger.error(f"LM Studio execution failed: {e}")
            fallback_res = run_rule_based_fallback(query)
            if "jinja" in err_str or "no user query" in err_str or "prompt template" in err_str:
                fallback_res.response = f"*(LM Studio Prompt Template Error - Check model prompt template settings in LM Studio)*\n\n" + fallback_res.response
            elif "timeout" in err_str or "timed out" in err_str:
                fallback_res.response = f"*(LM Studio Request Timed Out - Switched to Local Interpreter)*\n\n" + fallback_res.response
            elif "connection" in err_str or "refused" in err_str:
                fallback_res.response = f"*(LM Studio Not Available (Connection Refused) - Switched to Local Interpreter)*\n\n" + fallback_res.response
            else:
                fallback_res.response = f"*(LM Studio Call Failed: {str(e)[:100]} - Switched to Local Interpreter)*\n\n" + fallback_res.response
            return fallback_res

    # Handle Anthropic Client Tool Calling
    elif api_key and (provider == "anthropic" or (provider == "auto" and os.getenv("ANTHROPIC_API_KEY"))):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            
            # Format messages for Claude (system is a top-level parameter)
            claude_messages = []
            for msg in request.messages:
                claude_messages.append({"role": msg.role, "content": msg.content})

            # Format tools for Claude
            claude_tools = []
            for schema in tool_schemas:
                claude_tools.append({
                    "name": schema["name"],
                    "description": schema["description"],
                    "input_schema": schema["parameters"]
                })

            max_turns = 5
            for turn in range(max_turns):
                logger.info(f"Anthropic turn {turn}...")
                response = client.messages.create(
                    model=request.model or "claude-3-5-haiku-20241022",
                    system=system_prompt,
                    messages=claude_messages,
                    tools=claude_tools,
                    temperature=0.7,
                    max_tokens=2000
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
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                
                claude_messages.append({"role": "assistant", "content": assistant_content})

                if not tool_requests:
                    # Extract final text response
                    text_resp = "".join([b.text for b in response.content if b.type == "text"])
                    return ChatResponse(response=text_resp, tool_calls=tool_logs)

                # Process tool calls
                tool_results_content = []
                for tool_use in tool_requests:
                    name = tool_use.name
                    args = tool_use.input
                    
                    try:
                        result = execute_tool_locally(name, args)
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="success",
                            result=result
                        ))
                        tool_results_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result)
                        })
                    except Exception as ex:
                        logger.error(f"Error executing Anthropic tool {name}: {ex}")
                        tool_logs.append(ToolCallLog(
                            tool_name=name,
                            arguments=args,
                            status="error",
                            error=str(ex)
                        ))
                        tool_results_content.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps({"error": str(ex)})
                        })
                
                claude_messages.append({"role": "user", "content": tool_results_content})

        except Exception as e:
            logger.error(f"Anthropic execution failed: {e}. Falling back to rule-based parser.")
            fallback_res = run_rule_based_fallback(query)
            fallback_res.response = f"*(Anthropic Call Failed: {str(e)} - Switched to Local Interpreter)*\n\n" + fallback_res.response
            return fallback_res

    # Default fallback
    return run_rule_based_fallback(query)
