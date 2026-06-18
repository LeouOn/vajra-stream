# ADR 002: Settings System Canonical Selection

- **Status:** Accepted (2026-06-18)
- **Deciders:** Wave 2 remediation
- **References:** evaluation Issue 5.2; README "Configuration" section (lines 205–227); ADR 001
- **Gates:** Blocks Wave 4 Task 27 (settings consolidation / shim deletion)

## Context

The codebase ships **two parallel configuration systems** that independently define the same audio/hardware constants. Per evaluation Issue 5.2, this is a silent drift hazard: the two files overlap on `PRAYER_BOWL_MODE`, `SAMPLE_RATE`, `BLESSING_FREQUENCIES`, and `HARDWARE_LEVEL` (among others), and there is no machinery keeping them in sync.

| # | File | Form | LOC | Read by |
|---|------|------|-----|---------|
| 1 | `config/settings.py` | Plain Python constants (module-level) | 62 | `core/audio_generator.py:50,56` |
| 2 | `backend/app/config.py` | `pydantic-settings` (`BaseSettings` subclasses) | 116 | `backend/app/main.py:68,112` + 4 others (see Migration Plan) |

### Concrete drift evidence (verified)

The two files disagree on at least one shared constant today:

| Constant | `config/settings.py` (canonical) | `backend/app/config.py` |
|----------|----------------------------------|-------------------------|
| `MAX_VOLUME` | `0.5` (comment: *"Quieter is better"*) | `0.8` |

`SAMPLE_RATE`, `AUDIO_DEVICE`, `PRAYER_BOWL_MODE`, `PRAYER_BOWL_HARMONICS`, `PRAYER_BOWL_ENVELOPES`, `HARDWARE_LEVEL`, `AMPLIFIER_CONNECTED`, `BLESSING_FREQUENCIES` are currently equal across both — but only by coincidence; nothing enforces this.

Each file is also a *divergent subset*: `config/settings.py` defines richer prayer-bowl synthesis params (`PURE_SINE_MODE`, `PRAYER_BOWL_MODULATION`, `ATTACK/DECAY/SUSTAIN/RELEASE`, `PRAYER_BOWL_CONFIG` dict) absent from the backend; `backend/app/config.py` defines env-var-driven API/CORS/LLM/TTS/ComfyUI keys absent from the canonical module.

### Documentation precedent

The README "Configuration" section (line 207) instructs users: **"Edit `config/settings.py`"** and shows the canonical constants. The pydantic system is undocumented. The documented contract therefore already names `config/settings.py` as canonical; the backend module is an undocumented parallel implementation.

### Out-of-scope note (ghost reference)

`PROJECT_STRUCTURE.md:193` lists `config/enhanced_settings.py` ("Enhanced configuration management"). This file **does not exist** on disk — it is a ghost reference. Cleanup of the ghost is **Task 18** (ghost docs cleanup), not this ADR.

## Decision

**Canonical settings source = `config/settings.py`** (plain Python constants).

1. `config/settings.py` is the single source of truth for the audio/hardware/prayer-bowl constants it declares.
2. `backend/app/config.py` is **deprecated** as of this ADR. It is converted to a thin re-export shim (see Migration Plan) for one release cycle, then deleted in Task 27.
3. The pydantic `Settings` class is preserved *only as a compatibility wrapper* during the deprecation window — env-var override behavior on audio/hardware constants is **intentionally dropped** (see Consequences). New env-var-driven concerns (LLM provider selection, API keys) are not part of this consolidation.

## Consequences

- **Positive:** Single source of truth for audio/hardware constants. The `MAX_VOLUME` drift (and any future drift) becomes impossible by construction. README, code, and reality agree.
- **Positive:** Plain-Python constants are importable everywhere (no `pydantic-settings` dependency to read `PRAYER_BOWL_CONFIG`), matching the existing `core/audio_generator.py:50` import style.
- **Negative:** Env-var overrides for audio/hardware constants (e.g. `SAMPLE_RATE=48000` in `.env`) stop working once the shim is deleted. **Accepted** — the documented contract is "edit `config/settings.py`", not "set env vars"; no consumer in the tree relies on overriding these via env today.
- **Neutral:** `LLMConfig` / `get_llm_config()` in `backend/app/config.py` are a *different concern* (runtime LLM provider routing, env-prefixed `LLM_*`) with no canonical equivalent. They are **relocated, not deleted**, in Task 27.
- **Risk:** A future contributor re-introduces a pydantic `Settings` mirror. Mitigated by this ADR + Task 27's deletion manifest.

## Migration Plan (for Task 27)

### Step 1 — Rewire importers (Task 27, mechanical)

Every importer of `backend.app.config` for audio/hardware constants is repointed at `config.settings`. Verified importer inventory (grep audit, 2026-06-18):

| File:line | Current import | New import |
|-----------|----------------|------------|
| `backend/app/main.py:68` | `from backend.app.config import get_llm_config` | unchanged (LLM concern — relocated, not consolidated) |
| `backend/app/api/v1/endpoints/outlook.py:19` | `from backend.app.config import settings` | `from config import settings` (or `from config.settings import MAX_VOLUME, ...`) |
| `backend/app/api/v1/endpoints/locations.py:25` | `from backend.app.config import settings` | `from config import settings` |
| `backend/app/api/v1/endpoints/agent_suggestions.py:9` | `from backend.app.config import settings` | `from config import settings` |
| `backend/core/services/vajra_service.py:20` | `from backend.app.config import Settings` | `from config import settings` (drop the pydantic `Settings` class ref) |

> Note: Issue 5.2 enumerated the first four importers; the grep audit surfaced `vajra_service.py:20` as a fifth. All five are in scope for Task 27.

### Step 2 — Shim `backend/app/config.py` (Task 27, one release cycle)

```python
"""DEPRECATED shim. Import from `config.settings` directly.

Removed in the release after Task 27. See ADR 002."""
from config.settings import *  # noqa: F401,F403 — re-export canonical constants
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Thin pydantic wrapper around `config.settings` for legacy importers."""
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

# LLMConfig / get_llm_config are a separate concern (LLM_* env-prefixed
# provider routing) — relocated to their own module in Task 27, not deleted.
```

### Step 3 — Delete the shim (Task 27, after one release)

After one release cycle with the shim in place (emitting a `DeprecationWarning` on import), `backend/app/config.py` is deleted entirely and the LLM provider config is moved to its own module. Task 27 owns this deletion; this ADR only records the decision.

## Alternatives Considered

### (a) Make `backend/app/config.py` canonical and migrate `config/settings.py`

**Rejected.** Contradicts the README's documented contract ("Edit `config/settings.py`"), forces the audio engine path (`core/audio_generator.py:50`) through a pydantic dependency it does not need, and elevates the *undocumented* system over the *documented* one.

### (b) Keep both; add a sync test instead of choosing

**Rejected.** A sync test would freeze the current (drifting) `MAX_VOLUME` 0.5/0.8 split into a test failure rather than resolve it. The two files are divergent subsets with different audiences (audio engine vs. FastAPI env config); pairing every constant across both is busywork that obscures which file is authoritative.

### (c) Merge everything (audio + LLM + TTS + CORS) into one mega-module

**Rejected.** Conflates user-editable tuning constants with deployment env secrets. The LLM/TTS/API-key surface legitimately belongs behind env-var loading (pydantic-settings) and stays there; this ADR is only about the audio/hardware/prayer-bowl constants where the drift lives.
