# Extracting ImageGenerationService into a Standalone Repo

The `ImageGenerationService` is intentionally self-contained — it can be lifted
out of Vajra.Stream into a standalone Python package with zero refactoring.
This document is the receipt for that claim.

## What gets extracted

| File | Purpose | Standalone? |
|---|---|---|
| `backend/core/services/image_generation_service.py` | The entire service (provider-agnostic image generation) | Yes — zero project deps |
| `backend/app/api/v1/endpoints/image_generation.py` | Thin FastAPI adapter for Vajra.Stream | No — stays behind |
| `backend/core/llm_agent/tools.py::generate_image` | LLM tool registration | No — stays behind |

The tripwire test
[`tests/unit/test_image_generation_service.py::test_service_module_has_no_project_imports`](../../tests/unit/test_image_generation_service.py)
verifies the service file imports nothing from `backend.*`, `core.*`,
`container`, or `config.*`. If you add a project-relative import to the
service, that test fails.

## Extraction steps

```bash
# 1. Create the new repo
mkdir vajra-image-gen && cd vajra-image-gen
git init

# 2. Copy the service file
#    (relative to the Vajra.Stream project root)
cp ../vajra-stream/backend/core/services/image_generation_service.py ./image_gen.py

# 3. Replace the module path so the import works
#    In the new repo, the file is the package itself.
#    Rename the docstring and keep the public surface as-is.

# 4. Add pyproject.toml
cat > pyproject.toml <<'EOF'
[project]
name = "vajra-image-gen"
version = "0.1.0"
description = "Provider-agnostic image generation with cost & rate guards"
requires-python = ">=3.10"
dependencies = ["httpx>=0.27"]

[project.optional-dependencies]
test = ["pytest>=7.4", "pytest-asyncio>=0.21"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
EOF

# 5. Smoke-test it standalone
python -c "from image_gen import ImageGenerationService; print(ImageGenerationService().config)"
```

The output should print the default config dict — no `ModuleNotFoundError`
for `backend.*`, `core.*`, `container`, or `config.*`.

## Standalone usage

```python
from image_gen import ImageGenerationService

service = ImageGenerationService({
    "openrouter_api_key": "sk-or-v1-...",
    "minimax_api_key":   "sk-mm-...",
    "enabled":           True,
    "daily_cost_cap_usd": 0.50,
    "default_model":     "google/gemini-3.1-flash-lite-image",
})

result = await service.generate(prompt="Heart chakra mandala, golden sacred geometry")
print(result["image_data_url"])  # data:image/png;base64,...
```

## Or via environment variables

```python
import os
from image_gen import create_service_from_env

service = create_service_from_env({"enabled": True})
# Reads OPENROUTER_API_KEY + MINIMAX_API_KEY from os.environ
```

## Provider abstraction

The service is built around a small `ImageProvider` ABC. Adding a new provider
(Stable Diffusion, AWS Bedrock, etc.) is a 30-line subclass:

```python
from image_gen import ImageProvider, ProviderResult, ImageGenerationService

class StableDiffusionProvider(ImageProvider):
    URL = "https://api.stability.ai/v2beta/stable-image/generate/core"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(self, *, prompt, model, size, quality, n, **kwargs):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                self.URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"none": ""},
                data={"prompt": prompt, "output_format": "png"},
            )
        b64 = base64.b64encode(r.content).decode("ascii")
        return ProviderResult(
            image_data_url=f"data:image/png;base64,{b64}",
            model=model,
            cost_usd=0.04,
            provider="stability",
        )

# Register it
service = ImageGenerationService({"stability_api_key": "sk-..."})
service._providers["stability"] = StableDiffusionProvider(service._config["stability_api_key"])
# (or extend `_get_provider` for first-class routing)
```

## Public API surface

Everything you should depend on is exported from the module:

- `ImageGenerationService` — the main class
- `ImageProvider` — abstract base for new providers
- `ProviderResult` — return type for provider implementations
- `OpenRouterProvider` / `MiniMaxProvider` — reference implementations
- `create_service_from_env` — env-driven factory
- `DEFAULT_CONFIG` — baseline config dict
- `MODEL_COST_USD` — model → cost map (edit to reflect your own pricing)

## Verification status

The provider HTTP contracts (OpenRouter `/api/v1/images`, MiniMax
`/v1/image_generation`) are implemented from documented specs. As of this
commit, the integration has **not** been round-trip verified against live
API keys. Unit tests mock `httpx`; the smoke test (`scripts/smoke_image_generation.py`)
exercises the FastAPI routing in-process but does not egress to real
providers.

Before relying on this in production:
1. Get a capped ($0.50) OpenRouter key and run one real `generate()` call.
2. Repeat with MiniMax.
3. If response shapes differ from the parsers in `OpenRouterProvider._extract_data_url`
   / `MiniMaxProvider._extract_data_url`, adjust the parser and add a golden-file
   test fixture from the real response.
4. Verify end-to-end via the LLM chat: type "draw a heart chakra mandala" and
   confirm the `generate_image` tool fires and the image renders inline.

## Why this matters

You asked for a modular service so you could extract it and ship it as a
separate product. The work here is the receipt:

1. Zero project imports in the service module (verified by a tripwire test)
2. Single dependency (`httpx`) — no `fastapi`, no `sqlalchemy`, no `pydantic`
3. Config injected via constructor — no `config.settings` coupling
4. Cost tracking and caching live on the instance, not on a global singleton
5. Provider interface is a small ABC — adding a provider is a single subclass

If you ever want to harden this for distribution: add a `py.typed` marker,
fill out the docstrings with examples for each provider, and add a CLI
entrypoint with `argparse` for the same `generate()` API.

_May this be of benefit._