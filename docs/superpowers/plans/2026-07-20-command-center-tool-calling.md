# Command Center Tool Calling Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make LLM tool calls actually execute regardless of which provider/model the user selects — including free models that don't support native function calling.

**Architecture:** Consolidate the 4 overlapping dispatch paths (native tool_calls, text-mode JSON parser, keyword fallback, rule-based commands) into a single pipeline: try native → parse text → execute → return results. Remove dead code paths that intercept before the LLM even runs.

**Tech Stack:** Python (FastAPI, OpenAI client), existing TOOL_REGISTRY (80+ tools).

## Global Constraints

- Must work with: OpenRouter free models (no native function calling), DeepSeek, LM Studio, and OpenAI.
- Must NOT break the existing keyword-based quick actions (operator buttons in CommandCenter).
- The `/llm/teach` endpoint (clean LLM, no tools) must remain untouched.
- All tool results must appear in `data.tool_calls` so the frontend `CommandCenter.tsx` renders them.

---

## Task 1: Fix the regex bug in `_parse_text_tool_calls`

**Files:**
- Modify: `backend/app/api/v1/endpoints/llm.py` (`_parse_text_tool_calls`, ~line 149)

**Problem:** The regex `[^{}]*?` cannot match `"arguments": {}` because `{}` contains braces. The fallback bracket-depth counter works but only checks `content.find('{"tool"')` — misses `{"name":...}` and `{"function":...}` variants.

- [ ] **Step 1: Replace regex with robust JSON extraction**

Replace the entire `_TOOL_CALL_JSON_RE` regex and `_parse_text_tool_calls` with a brace-depth scanner that finds ALL `{...}` blocks in the content and tries to parse each as a tool call:

```python
def _parse_text_tool_calls(content: str) -> list[dict[str, Any]]:
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
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        name = parsed.get("tool") or parsed.get("name") or parsed.get("function") or ""
        args = parsed.get("arguments") or parsed.get("parameters") or parsed.get("args") or {}
        if name and isinstance(name, str) and len(candidate) > 15:
            results.append({"name": name.strip(), "arguments": args if isinstance(args, dict) else {}})
    return results
```

- [ ] **Step 2: Run tests to verify**

```bash
.venv\Scripts\python.exe -m pytest tests/unit/test_llm_tool_parsing.py -v
```

Expected: All 11 pass, including the inline JSON test that was failing.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/llm.py
git commit -m "fix(llm): replace regex tool parser with brace-depth scanner"
```

---

## Task 2: Fix provider fallback chain — don't intercept before OpenRouter

**Files:**
- Modify: `backend/app/api/v1/endpoints/llm.py` (`chat_interaction`, ~line 1530-1660)

**Problem:** When `provider == "auto"` and `DEEPSEEK_API_KEY` is set, DeepSeek is tried first. If it 401s, the `except` block falls to `run_rule_based_fallback` instead of trying the next provider (OpenRouter). The user selected an OpenRouter model but it never gets called.

- [ ] **Step 1: Add provider chain with fallthrough**

In `chat_interaction`, after `provider = request.provider or "auto"`, add logic: if the user explicitly selected a model (e.g., `nvidia/nemotron-...`), route to the provider that hosts that model. Also, when auto-provider fails, fall through to the next provider instead of jumping to rule-based fallback.

Minimal fix: in the DeepSeek `except` block, instead of immediately calling `run_rule_based_fallback`, check if OpenRouter is available and try it:

```python
except Exception as auto_ex:
    logger.error(f"DeepSeek failed: {auto_ex}. Trying next provider...")
    # Don't fall to rule-based yet — try OpenRouter if available
    if os.getenv("OPENROUTER_API_KEY"):
        # Fall through to the OpenRouter block below
        pass
    else:
        ...rule-based fallback...
```

- [ ] **Step 2: Test with the E2E script**

```bash
.venv\Scripts\python.exe scripts\test_tool_calling_e2e.py
```

Expected: When DeepSeek 401s, OpenRouter is tried; tool calls are parsed from text output.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/endpoints/llm.py
git commit -m "fix(llm): provider chain falls through to OpenRouter when DeepSeek fails"
```

---

## Task 3: Wire tool results into the frontend display

**Files:**
- Modify: `frontend/src/components/UI/CommandCenter.tsx` (tool call rendering, ~line 668)

**Problem:** Even when the backend returns `tool_calls`, the frontend doesn't render the tool RESULTS inline in the chat message. The user only sees the raw LLM text response.

- [ ] **Step 1: Add tool result rendering to RenderMessageWidgets**

In the chat message rendering, when `msg.toolCalls` has entries with `status: "success"`, render the result data as a formatted block below the LLM text. Currently the code only logs to `addToolLog` but doesn't render results in the message bubble.

- [ ] **Step 2: Verify in browser**

Start the app, type "list populations", verify the response shows the population list inline.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/UI/CommandCenter.tsx
git commit -m "feat(ui): render tool call results inline in Command Center chat"
```

---

## Task 4: Integration test — full automation flow

**Files:**
- Create: `scripts/test_automation_flow.py`

- [ ] **Step 1: Write test script that exercises the full flow**

```python
# Test: "list populations" → tool executes → results in response
# Test: "start automation" → session starts → status returned
# Test: "start rng session" → RNG session created → readings available
# Test: "forge sigil" → sigil created → SVG in response
```

- [ ] **Step 2: Run it**

- [ ] **Step 3: Commit**
