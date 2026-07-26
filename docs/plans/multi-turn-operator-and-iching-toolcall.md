# Multi-Turn Operator & I Ching Toolcall — Plan & Progress

## Status: In Progress

**Branch:** `feat/healing-dialogue`
**Last pushed:** `722f583`

---

## Completed This Session

1. ✅ **Remote sync** — Fetched and merged `origin/main` (5 new commits: LLM tool parsers, cancel button, provider fallback fixes, TTS improvements)
2. ✅ **New LLM models added** — MiniMax-M3, Ling-3.0-flash:free, Laguna-S/XS:free added to fallback chain
3. ✅ **Fallback chain cleaned** — Removed deepseek-chat and gpt-4o-mini; 5 models remain (3 free)
4. ✅ **Ruff cleanup** — All 49 new lint errors fixed after merge
5. ✅ **Esoteric Tutor** — LLM-based learning for astrology, tarot, I Ching with dedicated `/llm/teach` endpoint
6. ✅ **Transit time fix** — `/transits` endpoint now accepts `at` query param
7. ✅ **Multi-turn astrologer** — Conversation history + New Reading button in Cosmic Clock

---

## Planned Next (when plan agent was aborted)

### 1. Multi-Turn Operator with Subagents

**Goal:** The operator should be able to spawn sub-agents for complex tasks, show their progress, and evaluate their output. This should be a configurable setting.

**Research needed:**
- How OpenCode handles subagent orchestration (session management, delegation patterns)
- How other LLM harnesses (Claude Code, Cursor, Cline) structure multi-turn agent workflows
- Evaluation patterns for subagent output quality

**Implementation plan:**

#### Backend (`backend/app/api/v1/endpoints/operator.py`)
- Add `SubagentConfig` model: `enabled: bool`, `max_concurrent: int`, `evaluation_mode: str`
- Add `/subagent/spawn` endpoint — spawns a subagent with a task description
- Add `/subagent/status/{id}` endpoint — returns progress, partial results
- Add `/subagent/evaluate/{id}` endpoint — runs evaluation on subagent output
- Add `/subagent/config` GET/PUT — configure subagent behavior

#### Frontend (`frontend/src/components/UI/CommandCenter.tsx`)
- Add a "Subagents" collapsible panel below the chat
- Show active subagents with progress bars
- Show evaluation results (pass/fail with reasoning)
- Add toggle in Settings to enable/disable subagents

#### Settings (`frontend/src/components/UI/Settings/LLMSettingsPanel.tsx`)
- Add "Multi-Agent Mode" section with:
  - Enable/disable toggle
  - Max concurrent subagents slider (1-5)
  - Evaluation mode dropdown (none, basic, strict)

### 2. Unicode & Formatting Improvements

**Goal:** Clean up how toolcall outputs render in the UI. Some outputs are blobs of JSON that are hard to scan.

**Issues identified:**
- I Ching toolcall dumps all 6 line meanings as one blob
- Tarot card meanings are raw arrays
- No visual hexagram diagram shown
- Tool results in CommandCenter are plain text, not structured

**Implementation plan:**

#### I Ching toolcall (`backend/core/services/divination_service.py`)
- Convert line values (6,7,8,9) to visual representation:
  - 6 (Old Yin): `- -` (changing)
  - 7 (Young Yang): `━━━`
  - 8 (Young Yin): `- -`
  - 9 (Old Yang): `━━━` (changing)
- Generate ASCII art hexagram instead of just returning SVG
- Show only the **changing lines' meanings** (not all 6) unless asked
- Format output as a clean markdown card with:
  - Hexagram name (Chinese + Pinyin + English)
  - Visual diagram (ASCII or SVG)
  - Judgment + Image text (2-3 sentences)
  - Only changing line meanings (if any)
  - Relating hexagram name

#### Tarot toolcall (`backend/core/services/divination_service.py`)
- Format cards as clean markdown with:
  - Card name + position
  - Upright/reversed indicator
  - 2-3 sentence meaning (not the full text)
  - Keywords as tags

### 3. I Ching Hexagram Cast Toolcall — Concrete Changes

**Current output issues (from user's example):**
The tool returns a massive dict with:
- `cast_lines: [7, 9, 7, 9, 8, 6]` — raw integers, meaningless to user
- Full hexagram data dumped including all 6 line meanings
- Relating hexagram data also full dump
- No visual representation

**New output format:**

```
☯️ I CHING CAST

PRIMARY: Dà Zhuàng / The Power of the Great (大壮)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Diagram:
  ━━━  line 6 (changing → Yin)
  ━━━  line 5  
  - -  line 4
  - -  line 3  
  ━━━  line 2 (changing → Yin)
  ━━━  line 1

Judgment: The Power of the Great. Perseverance furthers.
Image: Thunder in heaven above: the image of the Power of the Great. Thus the superior man does not tread upon paths that do not accord with order.

Changing Lines:
• Line 1 (9→8): Power in the toes. Continuing brings misfortune.
• Line 5 (6→7): Loses the goat in easiness. No remorse.

RELATING: Guài / Breakthrough (夬)
Decisive resolution, clearing out of remaining obstacles.
```

**Code changes needed:**
1. `divination_service.py:cast_i_ching()` — restructure the return dict to include a `formatted` field
2. `divination_service.py` — add helper `_format_hexagram_markdown(hex_data, lines)` 
3. `llm_agent/tools.py:cast_i_ching` — the tool wrapper should return the formatted version to the LLM
4. `OperationsPanel.tsx` — render the formatted output with proper markdown

---

## Priority Order

| # | Feature | Effort | Impact |
|---|---------|--------|--------|
| 1 | I Ching toolcall formatting | Medium | High — user explicitly asked |
| 2 | Unicode/formatting general | Medium | Medium |
| 3 | Multi-turn subagents | High | High — complex feature |

---

## Open Questions

- Should subagents share conversation history with the parent operator?
- Should evaluation be automated (LLM judges output) or manual (user rates)?
- Should the I Ching formatted output be returned to the LLM or only shown in UI?

---

*Plan written 2026-07-23 after plan agent was aborted.*
