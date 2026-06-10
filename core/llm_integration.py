"""
LLM Integration — unified interface for API and local language models.

Provides a single abstraction over multiple LLM backends:
- **DeepSeek v4** — OpenAI-compatible cloud API (deepseek-chat). Uses
  ``DEEPSEEK_API_KEY`` and ``DEEPSEEK_BASE_URL`` env vars.
- **OpenAI API** (GPT-4o, GPT-4o-mini) — also supports any OpenAI-compatible
  endpoint via ``OPENAI_BASE_URL`` (Together, Groq, Fireworks, etc.).
- **Anthropic API** (Claude 3.5 Sonnet/Haiku).
- **LM Studio** — OpenAI-compatible local server at http://127.0.0.1:1234.
- **Local GGUF models** via llama-cpp-python (offline, private, zero cost).
- **openai_compatible** — generic mode: set ``OPENAI_BASE_URL`` + ``OPENAI_API_KEY``
  + a model name to point at any OpenAI-compatible endpoint.

The auto-detection system (``model_type="auto"``) probes in order:
LM Studio → DeepSeek → local GGUF → Anthropic → OpenAI.

All API calls are tracked via :class:`~core.llm_usage.LLMUsageTracker` for
token counting, cost estimation, and balance management.

Exports:
    LLMIntegration — multi-backend LLM client with auto-detection + usage tracking.
    DharmaLLM — specialised interface for Buddhist/dharma content generation.

Dependencies:
    Optional (imported lazily): openai, anthropic, llama_cpp, urllib.

Typical usage:
    >>> llm = LLMIntegration(model_type="deepseek")
    >>> dharma = DharmaLLM(llm)
    >>> print(dharma.generate_prayer("peace and healing for all beings"))
    >>> print(llm.get_usage_summary())
"""

from __future__ import annotations

import glob
import os
import time

try:
    from core.llm_usage import LLMUsageTracker, UsageRecord

    HAS_USAGE_TRACKER = True
except ImportError:
    HAS_USAGE_TRACKER = False


class LLMIntegration:
    """Unified multi-backend LLM client with auto-detection and usage tracking.

    Supports these ``model_type`` values:
    - ``"auto"`` (default) — probes: LM Studio → DeepSeek → local GGUF → Anthropic → OpenAI.
    - ``"deepseek"`` — DeepSeek v4 API (OpenAI-compatible, ~$0.14/M input tokens).
    - ``"openai"`` — OpenAI chat completions (or any OpenAI-compatible endpoint
      via ``OPENAI_BASE_URL``).
    - ``"anthropic"`` — Anthropic Messages API.
    - ``"openai_compatible"`` — generic mode: set ``OPENAI_BASE_URL``,
      ``OPENAI_API_KEY``, and a model name to use any compatible endpoint.
    - ``"local"`` — loads a GGUF model via llama-cpp-python.

    Every ``generate()`` call is tracked via :class:`~core.llm_usage.LLMUsageTracker`
    (token counts, cost estimation, latency). Use :meth:`get_usage_summary` to
    retrieve the JSON-serialisable summary for the frontend.

    Attributes:
        model_type: Resolved backend name.
        model_name: Active model identifier.
        client: OpenAI or Anthropic client instance (None for local models).
        local_model: llama-cpp-python Llama instance (None for API backends).
        base_url: Custom API base URL (set for DeepSeek / openai_compatible).
        provider_key: Provider key for usage tracking (``"deepseek"``, ``"openai"``, etc.).
    """

    def __init__(
        self,
        model_type: str = "auto",
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        local_models_dir: str = "./models",
    ):
        """Initialize LLM integration with optional custom base URL.

        Args:
            model_type: One of ``"auto"``, ``"deepseek"``, ``"openai"``,
                ``"anthropic"``, ``"openai_compatible"``, or ``"local"``.
            model_name: Specific model name or GGUF file path.
            api_key: API key (overrides env vars).
            base_url: Custom API base URL (overrides env vars).
            local_models_dir: Directory to scan for GGUF models.
        """
        self.model_type = model_type
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url
        self.local_models_dir = local_models_dir
        self.provider_key = "unknown"  # Set during init

        self.client = None
        self.local_model = None

        # Usage tracker (singleton — shared across all instances)
        self._tracker = LLMUsageTracker.get() if HAS_USAGE_TRACKER else None

        # Initialize based on type
        if model_type == "auto":
            self._initialize_auto()
        elif model_type == "deepseek":
            self._initialize_deepseek()
        elif model_type == "openai_compatible":
            self._initialize_openai_compatible()
        elif model_type == "openai":
            self._initialize_openai()
        elif model_type == "openrouter":
            self._initialize_openrouter()
        elif model_type == "anthropic":
            self._initialize_anthropic()
        elif model_type == "local":
            self._initialize_local()

    def _initialize_auto(self) -> None:
        """Auto-detect: LM Studio → DeepSeek → OpenRouter → local GGUF → Anthropic → OpenAI."""
        print("Auto-detecting available LLM...")

        # 1. Try LM Studio (OpenAI-compatible local server)
        lm_studio_url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234")
        try:
            import json
            import urllib.request

            # A. Try to check legacy /api/v0/models or /api/v1/models for loaded models first
            loaded_model = None
            try:
                req = urllib.request.Request(f"{lm_studio_url}/api/v0/models")
                with urllib.request.urlopen(req, timeout=1.0) as response:
                    if response.status == 200:
                        v0_data = json.loads(response.read().decode())
                        for m in v0_data.get("data", []):
                            if m.get("state") == "loaded":
                                loaded_model = m.get("id")
                                break
            except Exception:
                pass

            if not loaded_model:
                try:
                    req = urllib.request.Request(f"{lm_studio_url}/api/v1/models")
                    with urllib.request.urlopen(req, timeout=1.0) as response:
                        if response.status == 200:
                            v1_data = json.loads(response.read().decode())
                            for m in v1_data.get("data", []):
                                if m.get("loaded") is True or m.get("status") == "loaded" or m.get("is_loaded") is True:
                                    loaded_model = m.get("id")
                                    break
                except Exception:
                    pass

            # B. Query the OpenAI-compatible endpoint to check model availability
            req = urllib.request.Request(f"{lm_studio_url}/v1/models")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.status == 200:
                    models_data = json.loads(response.read().decode())
                    models = [m["id"] for m in models_data.get("data", [])]
                    if models:
                        from openai import OpenAI

                        self.client = OpenAI(base_url=f"{lm_studio_url}/v1", api_key="lm-studio")
                        self.model_type = "lm_studio"
                        self.provider_key = "lm_studio"

                        # Preference logic:
                        # 1. Environment variable LM_STUDIO_MODEL
                        # 2. Currently loaded model resolved from API
                        # 3. Smaller known models in the list
                        # 4. First model in list
                        env_model = os.getenv("LM_STUDIO_MODEL")
                        if env_model and env_model in models:
                            self.model_name = env_model
                        elif loaded_model and loaded_model in models:
                            self.model_name = loaded_model
                        else:
                            # Avoid loading 35B models by default: prefer smaller GGUFs if they are in the list
                            small_model = None
                            for m in models:
                                m_lower = m.lower()
                                if any(x in m_lower for x in ["darwin", "altair", "mn-12b", "4b", "7b", "8b", "12b"]):
                                    small_model = m
                                    break
                            self.model_name = self.model_name or small_model or models[0]

                        self.base_url = f"{lm_studio_url}/v1"
                        print(f"[OK] Using LM Studio model: {self.model_name}")
                        return
                    else:
                        print("[INFO] LM Studio reachable but no model loaded — trying other backends")
        except Exception:
            pass

        # 2. Try DeepSeek API
        if os.getenv("DEEPSEEK_API_KEY"):
            try:
                self._initialize_deepseek()
                if self.client:
                    print("[OK] Using DeepSeek API")
                    return
            except Exception as e:
                print(f"  DeepSeek not available: {e}")

        # 3. Try OpenRouter API
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                self._initialize_openrouter()
                if self.client:
                    print("[OK] Using OpenRouter API")
                    return
            except Exception as e:
                print(f"  OpenRouter not available: {e}")

        # 4. Try local GGUF
        try:
            self._initialize_local()
            if self.local_model:
                print(f"[OK] Using local model: {self.model_name}")
                return
        except Exception as e:
            print(f"  Local model not available: {e}")

        # 5. Fall back to Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                self._initialize_anthropic()
                print("[OK] Using Anthropic API")
                return
            except Exception:
                pass

        # 6. Fall back to OpenAI (or OpenAI-compatible)
        if os.getenv("OPENAI_API_KEY"):
            try:
                self._initialize_openai()
                print("[OK] Using OpenAI API")
                return
            except Exception:
                pass

        print("[WARN] No LLM available. Set OPENROUTER_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or add GGUF models.")

    def _initialize_local(self) -> None:
        """Initialize local GGUF model"""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")

        # Find GGUF models
        if self.model_name and os.path.exists(self.model_name):
            model_path = self.model_name
        else:
            model_path = self._find_gguf_model()

        if not model_path:
            raise FileNotFoundError(f"No GGUF models found in {self.local_models_dir}")

        print(f"Loading local model: {model_path}")

        # Load model with reasonable defaults
        self.local_model = Llama(
            model_path=model_path,
            n_ctx=2048,  # Context window
            n_threads=4,  # CPU threads
            n_gpu_layers=0,  # Set > 0 if you have GPU
            verbose=False,
        )

        self.model_type = "local"
        self.model_name = os.path.basename(model_path)

    def _find_gguf_model(self) -> str | None:
        """Scan directory for GGUF models"""
        os.makedirs(self.local_models_dir, exist_ok=True)

        # Search for .gguf files
        patterns = [
            os.path.join(self.local_models_dir, "*.gguf"),
            os.path.join(self.local_models_dir, "**/*.gguf"),
        ]

        for pattern in patterns:
            models = glob.glob(pattern, recursive=True)
            if models:
                # Prefer models with 'instruct' or 'chat' in name
                for model in models:
                    if "instruct" in model.lower() or "chat" in model.lower():
                        return model
                # Otherwise return first found
                return models[0]

        return None

    def _initialize_openai(self) -> None:
        """Initialize OpenAI API (or any OpenAI-compatible endpoint).

        Reads ``OPENAI_BASE_URL`` from env or constructor. When set, the client
        points at that URL — enabling DeepSeek, Together, Groq, Fireworks, etc.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        base = self.base_url or os.getenv("OPENAI_BASE_URL")
        key = self.api_key or os.getenv("OPENAI_API_KEY")

        if base:
            self.client = OpenAI(base_url=base, api_key=key)
            self.base_url = base
        else:
            self.client = OpenAI(api_key=key)

        self.model_type = "openai"
        self.provider_key = "openai"
        if not self.model_name:
            self.model_name = "gpt-4o-mini"

    def _initialize_deepseek(self) -> None:
        """Initialize DeepSeek v4 API (OpenAI-compatible).

        Uses ``DEEPSEEK_API_KEY`` and ``DEEPSEEK_BASE_URL`` env vars.
        Default base URL: ``https://api.deepseek.com``.
        Default model: ``deepseek-chat``.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        base = self.base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        key = self.api_key or os.getenv("DEEPSEEK_API_KEY")

        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set")

        self.client = OpenAI(base_url=base, api_key=key)
        self.base_url = base
        self.model_type = "deepseek"
        self.provider_key = "deepseek"
        if not self.model_name:
            self.model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        print(f"[OK] DeepSeek client ready — model: {self.model_name} @ {base}")

    def _initialize_openrouter(self) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        base = self.base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        key = self.api_key or os.getenv("OPENROUTER_API_KEY")

        if not key:
            raise ValueError("OPENROUTER_API_KEY not set")

        self.client = OpenAI(base_url=base, api_key=key)
        self.base_url = base
        self.model_type = "openrouter"
        self.provider_key = "openrouter"
        if not self.model_name:
            self.model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
        print(f"[OK] OpenRouter client ready — model: {self.model_name} @ {base}")

    def _initialize_openai_compatible(self) -> None:
        """Initialize a generic OpenAI-compatible endpoint.

        Requires ``OPENAI_BASE_URL`` and ``OPENAI_API_KEY`` env vars.
        Model name must be provided via constructor or ``OPENAI_MODEL`` env var.
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        base = self.base_url or os.getenv("OPENAI_BASE_URL")
        key = self.api_key or os.getenv("OPENAI_API_KEY")

        if not base:
            raise ValueError("OPENAI_BASE_URL must be set for model_type='openai_compatible'")
        if not key:
            raise ValueError("OPENAI_API_KEY must be set for model_type='openai_compatible'")

        self.client = OpenAI(base_url=base, api_key=key)
        self.base_url = base
        self.model_type = "openai_compatible"
        self.provider_key = "openai_compatible"
        if not self.model_name:
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"[OK] OpenAI-compatible client ready — model: {self.model_name} @ {base}")

    def _initialize_anthropic(self) -> None:
        """Initialize Anthropic API"""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.client = Anthropic(api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model_type = "anthropic"
        if not self.model_name:
            self.model_name = "claude-3-5-haiku-20241022"  # Default to Haiku

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str:
        """Generate text from prompt.

        If a specific model name/string is supplied, dynamically routes to the
        correct provider (local GGUF, DeepSeek, OpenAI, Anthropic, or LM Studio)
        based on prefixes (e.g. 'local:', 'deepseek:', 'openai:', 'anthropic:',
        'lm_studio:') or model name auto-detection.

        Args:
            prompt: User prompt.
            system_prompt: System instructions.
            max_tokens: Maximum response length.
            temperature: Creativity (0-1).
            model: Override model name/provider string (e.g., 'gpt-4o-mini',
                'deepseek:deepseek-v4-flash', or 'local:darwin-4b-genesis-i1.gguf').
        """
        # DEBUG: trace model parameter flow
        print(f"[DEBUG generate] model={model!r}, self.model_type={self.model_type!r}, self.client={'set' if self.client else 'None'}")
        # If model_type is still "auto" (meaning previous detection failed), try one more time
        if self.model_type == "auto" or getattr(self, "model_type", "auto") == "auto":
            self._initialize_auto()

        # If no model is supplied, use configured default behavior
        if not model:
            if self.model_type == "local":
                return self._generate_local(prompt, system_prompt, max_tokens, temperature)
            elif self.model_type in ("openai", "deepseek", "openai_compatible"):
                return self._generate_openai(prompt, system_prompt, max_tokens, temperature, self.model_name)
            elif self.model_type == "anthropic":
                return self._generate_anthropic(prompt, system_prompt, max_tokens, temperature, self.model_name)
            elif self.model_type == "lm_studio":
                model_str = f"lm_studio:{self.model_name}"
            else:
                return "No LLM initialized. Please configure an API key or local model."
        else:
            model_str = model.strip()
            if model_str.lower() == "auto":
                model_str = self.model_name or "auto"

        # Parse provider prefix if present
        provider: str | None = None
        target_model: str = model_str

        if ":" in model_str:
            parts = model_str.split(":", 1)
            pref = parts[0].lower()
            val = parts[1]
            if pref == "local":
                provider = "local"
                target_model = val
            elif pref == "deepseek":
                provider = "deepseek"
                target_model = val
            elif pref == "openai":
                provider = "openai"
                target_model = val
            elif pref == "anthropic":
                provider = "anthropic"
                target_model = val
            elif pref in ("lm_studio", "lm-studio"):
                provider = "lm_studio"
                target_model = val

        # Fallback to name-based detection if no prefix was specified
        if not provider:
            lower_model = model_str.lower()
            if lower_model.endswith(".gguf") or "gguf" in lower_model:
                provider = "local"
            elif "deepseek" in lower_model:
                provider = "deepseek"
            elif "claude" in lower_model or "haiku" in lower_model or "sonnet" in lower_model:
                provider = "anthropic"
            elif "gpt-" in lower_model:
                provider = "openai"
            else:
                # Default back to self.model_type if resolved, or lm_studio
                provider = self.model_type if self.model_type != "auto" else "lm_studio"

        # Execute completion based on mapped provider
        if provider == "local":
            try:
                from llama_cpp import Llama
            except ImportError:
                return "llama-cpp-python not installed. Run: pip install llama-cpp-python"

            # Resolve model file path
            model_path = target_model
            if not os.path.exists(model_path):
                check_path = os.path.join(self.local_models_dir, target_model)
                if os.path.exists(check_path):
                    model_path = check_path
                elif not model_path.endswith(".gguf"):
                    check_path_gguf = check_path + ".gguf"
                    if os.path.exists(check_path_gguf):
                        model_path = check_path_gguf
                    else:
                        # Case-insensitive scan
                        os.makedirs(self.local_models_dir, exist_ok=True)
                        for f in os.listdir(self.local_models_dir):
                            if f.lower().startswith(target_model.lower()):
                                model_path = os.path.join(self.local_models_dir, f)
                                break

            # Fallback to any GGUF in the folder if the specified one doesn't exist
            if not os.path.exists(model_path):
                found = self._find_gguf_model()
                if found:
                    model_path = found
                else:
                    return f"Local GGUF model file not found for '{target_model}' and no fallback available in {self.local_models_dir}."

            # Re-initialize local model if path changes or not loaded
            current_path = getattr(self, "_loaded_local_path", None)
            if not self.local_model or current_path != model_path:
                print(f"Loading local model dynamically: {model_path}")
                try:
                    self.local_model = Llama(
                        model_path=model_path,
                        n_ctx=2048,
                        n_threads=4,
                        n_gpu_layers=0,
                        verbose=False,
                    )
                    self._loaded_local_path = model_path
                except Exception as e:
                    return f"Failed to load local GGUF model '{model_path}': {e}"

            formatted_prompt = f"### System:\n{system_prompt}\n\n### User:\n{prompt}\n\n### Assistant:\n" if system_prompt else prompt
            response = self.local_model(
                formatted_prompt, max_tokens=max_tokens, temperature=temperature, stop=["###", "\n\n\n"], echo=False
            )
            return response["choices"][0]["text"].strip()

        elif provider == "deepseek":
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                return "DEEPSEEK_API_KEY is not configured in environment."

            try:
                from openai import OpenAI
                client = OpenAI(base_url=base_url, api_key=api_key)
            except Exception as e:
                return f"Failed to initialize OpenAI client for DeepSeek: {e}"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            start_time = time.time()
            try:
                response = client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                result = response.choices[0].message.content
                latency_ms = (time.time() - start_time) * 1000

                if HAS_USAGE_TRACKER and self._tracker:
                    try:
                        prompt_tokens = response.usage.prompt_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(prompt + (system_prompt or ""))
                        completion_tokens = response.usage.completion_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(result)
                        cost = self._tracker.estimate_cost("deepseek", target_model, prompt_tokens, completion_tokens)
                        self._tracker.record(UsageRecord(
                            provider="deepseek",
                            model=target_model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=prompt_tokens + completion_tokens,
                            cost_usd=cost,
                            latency_ms=latency_ms,
                            endpoint="chat",
                            success=True,
                        ))
                    except Exception:
                        pass
                return result
            except Exception as e:
                return f"DeepSeek generation failed: {e}"

        elif provider == "openai":
            base_url = os.getenv("OPENAI_BASE_URL")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key.startswith("sk-your-"):
                return "OPENAI_API_KEY is not configured or invalid in environment."

            try:
                from openai import OpenAI
                if base_url:
                    client = OpenAI(base_url=base_url, api_key=api_key)
                else:
                    client = OpenAI(api_key=api_key)
            except Exception as e:
                return f"Failed to initialize OpenAI client: {e}"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            start_time = time.time()
            try:
                response = client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                result = response.choices[0].message.content
                latency_ms = (time.time() - start_time) * 1000

                if HAS_USAGE_TRACKER and self._tracker:
                    try:
                        prompt_tokens = response.usage.prompt_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(prompt + (system_prompt or ""))
                        completion_tokens = response.usage.completion_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(result)
                        cost = self._tracker.estimate_cost("openai", target_model, prompt_tokens, completion_tokens)
                        self._tracker.record(UsageRecord(
                            provider="openai",
                            model=target_model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=prompt_tokens + completion_tokens,
                            cost_usd=cost,
                            latency_ms=latency_ms,
                            endpoint="chat",
                            success=True,
                        ))
                    except Exception:
                        pass
                return result
            except Exception as e:
                return f"OpenAI generation failed: {e}"

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key or api_key.startswith("sk-ant-your-"):
                return "ANTHROPIC_API_KEY is not configured or invalid in environment."

            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
            except Exception as e:
                return f"Failed to initialize Anthropic client: {e}"

            kwargs = {
                "model": target_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            start_time = time.time()
            try:
                response = client.messages.create(**kwargs)
                result = response.content[0].text
                latency_ms = (time.time() - start_time) * 1000

                if HAS_USAGE_TRACKER and self._tracker:
                    try:
                        usage = response.usage if hasattr(response, "usage") else None
                        prompt_tokens = usage.input_tokens if usage else self._tracker.estimate_tokens(prompt + (system_prompt or ""))
                        completion_tokens = usage.output_tokens if usage else self._tracker.estimate_tokens(result)
                        cost = self._tracker.estimate_cost("anthropic", target_model, prompt_tokens, completion_tokens)
                        self._tracker.record(UsageRecord(
                            provider="anthropic",
                            model=target_model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=prompt_tokens + completion_tokens,
                            cost_usd=cost,
                            latency_ms=latency_ms,
                            endpoint="chat",
                            success=True,
                        ))
                    except Exception:
                        pass
                return result
            except Exception as e:
                return f"Anthropic generation failed: {e}"

        elif provider == "lm_studio":
            base_url = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234")
            try:
                from openai import OpenAI
                client = OpenAI(base_url=f"{base_url}/v1", api_key="lm-studio")
            except Exception as e:
                return f"Failed to initialize LM Studio client: {e}"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            try:
                response = client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                msg = response.choices[0].message
                result = msg.content or ""
                
                reasoning = ""
                if hasattr(msg, "model_dump"):
                    try:
                        msg_dump = msg.model_dump()
                        if isinstance(msg_dump, dict):
                            reasoning = msg_dump.get("reasoning_content", "")
                    except Exception:
                        pass
                if isinstance(reasoning, str) and reasoning:
                    if not result:
                        result = "<thought>\n" + reasoning + "\n</thought>\n"
                    else:
                        result = "<thought>\n" + reasoning + "\n</thought>\n\n" + result
                return result
            except Exception as e:
                return f"LM Studio generation failed: {e}"

        return f"Unknown provider or model type: {provider}"

    def _generate_local(self, prompt: str, system_prompt: str | None, max_tokens: int, temperature: float) -> str:
        """Generate using local GGUF model"""
        # Format prompt with system message if provided
        if system_prompt:
            formatted_prompt = f"### System:\n{system_prompt}\n\n### User:\n{prompt}\n\n### Assistant:\n"
        else:
            formatted_prompt = prompt

        # Generate
        response = self.local_model(
            formatted_prompt, max_tokens=max_tokens, temperature=temperature, stop=["###", "\n\n\n"], echo=False
        )

        return response["choices"][0]["text"].strip()

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
        model: str | None = None,
    ) -> str:
        """Generate using OpenAI API (or LM Studio / DeepSeek / any compatible endpoint).

        Tracks usage via :class:`~core.llm_usage.LLMUsageTracker`.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        target_model = model or self.model_name
        start_time = time.time()
        success = True

        try:
            response = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            msg = response.choices[0].message
            result = msg.content or ""
            
            reasoning = ""
            if hasattr(msg, "model_dump"):
                try:
                    msg_dump = msg.model_dump()
                    if isinstance(msg_dump, dict):
                        reasoning = msg_dump.get("reasoning_content", "")
                except Exception:
                    pass
            if isinstance(reasoning, str) and reasoning:
                if not result:
                    result = "<thought>\n" + reasoning + "\n</thought>\n"
                else:
                    result = "<thought>\n" + reasoning + "\n</thought>\n\n" + result
        except Exception as e:
            success = False
            if model and model != self.model_name:
                print(f"[WARN] Failed with model '{model}': {e}. Falling back to '{self.model_name}'...")
                try:
                    start_time = time.time()
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    msg2 = response.choices[0].message
                    result = msg2.content or ""
                    
                    reasoning2 = ""
                    if hasattr(msg2, "model_dump"):
                        try:
                            msg2_dump = msg2.model_dump()
                            if isinstance(msg2_dump, dict):
                                reasoning2 = msg2_dump.get("reasoning_content", "")
                        except Exception:
                            pass
                    if isinstance(reasoning2, str) and reasoning2:
                        if not result:
                            result = "<thought>\n" + reasoning2 + "\n</thought>\n"
                        else:
                            result = "<thought>\n" + reasoning2 + "\n</thought>\n\n" + result
                    success = True
                except Exception as fallback_err:
                    print(f"[ERROR] Fallback also failed: {fallback_err}")
                    result = ""
            else:
                print(f"[ERROR] OpenAI/LM Studio generation failed: {e}")
                result = ""

        latency_ms = (time.time() - start_time) * 1000

        # Track usage
        if HAS_USAGE_TRACKER and self._tracker and success:
            try:
                prompt_tokens = response.usage.prompt_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(prompt + (system_prompt or ""))
                completion_tokens = response.usage.completion_tokens if hasattr(response, "usage") and response.usage else self._tracker.estimate_tokens(result)
                cost = self._tracker.estimate_cost(self.provider_key, target_model, prompt_tokens, completion_tokens)

                self._tracker.record(UsageRecord(
                    provider=self.provider_key,
                    model=target_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    endpoint="chat",
                    success=success,
                ))
            except Exception:
                pass  # Never let tracking break generation

        if not success and not result:
            raise RuntimeError(f"LLM generation failed for provider '{self.provider_key}'")

        return result

    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: str | None,
        max_tokens: int,
        temperature: float,
        model: str | None = None,
    ) -> str:
        """Generate using Anthropic API with usage tracking."""
        kwargs = {
            "model": model or self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        target_model = kwargs["model"]
        start_time = time.time()
        success = True

        try:
            response = self.client.messages.create(**kwargs)
            result = response.content[0].text
        except Exception as e:
            success = False
            if model and model != self.model_name:
                print(f"[WARN] Failed with model '{model}': {e}. Falling back to '{self.model_name}'...")
                kwargs["model"] = self.model_name
                try:
                    start_time = time.time()
                    response = self.client.messages.create(**kwargs)
                    result = response.content[0].text
                    success = True
                except Exception as fallback_err:
                    print(f"[ERROR] Fallback also failed: {fallback_err}")
                    result = ""
            else:
                result = ""

        latency_ms = (time.time() - start_time) * 1000

        # Track usage
        if HAS_USAGE_TRACKER and self._tracker and success:
            try:
                usage = response.usage if hasattr(response, "usage") else None
                prompt_tokens = usage.input_tokens if usage else self._tracker.estimate_tokens(prompt + (system_prompt or ""))
                completion_tokens = usage.output_tokens if usage else self._tracker.estimate_tokens(result)
                cost = self._tracker.estimate_cost("anthropic", target_model, prompt_tokens, completion_tokens)

                self._tracker.record(UsageRecord(
                    provider="anthropic",
                    model=target_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    endpoint="chat",
                    success=success,
                ))
            except Exception:
                pass

        if not success and not result:
            raise RuntimeError("Anthropic generation failed")

        return result

    def list_available_models(self) -> dict[str, list[str]]:
        """List all available models across all providers.

        Returns:
            Dict with keys ``"local"``, ``"api"``, ``"current_provider"``, and
            ``"current_model"``.
        """
        available: dict[str, list[str]] = {"local": [], "api": []}

        # Local GGUF models
        patterns = [
            os.path.join(self.local_models_dir, "*.gguf"),
            os.path.join(self.local_models_dir, "**/*.gguf"),
        ]
        for pattern in patterns:
            models = glob.glob(pattern, recursive=True)
            available["local"].extend([os.path.basename(m) for m in models])

        # API providers
        if os.getenv("DEEPSEEK_API_KEY"):
            available["api"].append(
                f"DeepSeek ({os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')})"
            )

        if os.getenv("OPENAI_API_KEY"):
            label = "OpenAI (gpt-4o, gpt-4o-mini, etc.)"
            if os.getenv("OPENAI_BASE_URL"):
                label += f" @ {os.getenv('OPENAI_BASE_URL')}"
            available["api"].append(label)

        if os.getenv("ANTHROPIC_API_KEY"):
            available["api"].append("Anthropic (claude-3-5-sonnet, claude-3-5-haiku)")

        # Current active
        available["current_provider"] = [self.provider_key]
        available["current_model"] = [self.model_name or "unknown"]

        return available

    def get_usage_summary(self) -> dict:
        """Return the usage tracker summary (tokens, cost, per-provider stats).

        Returns:
            Dict from :meth:`LLMUsageTracker.get_summary`, or an empty dict if
            usage tracking is disabled.
        """
        if self._tracker:
            return self._tracker.get_summary()
        return {}

    def get_active_provider(self) -> dict:
        """Return info about the currently active provider.

        Returns:
            Dict with ``provider``, ``model``, ``base_url``, and ``model_type``.
        """
        return {
            "provider": self.provider_key,
            "model": self.model_name,
            "base_url": getattr(self, "base_url", None),
            "model_type": self.model_type,
        }


class DharmaLLM:
    """Specialised LLM interface for Buddhist / dharma content generation.

    Wraps an :class:`LLMIntegration` instance with a dharma-teacher system
    prompt and convenience methods for common spiritual content types:
    prayers, teachings, meditation instructions, dedications, and
    contemplation exercises.

    The system prompt instructs the model to respond as a wise dharma teacher
    versed in Theravada, Mahayana, and Vajrayana traditions.

    Attributes:
        llm: The underlying :class:`LLMIntegration` instance.
        dharma_system: System prompt string used for all generation calls.
    """

    def __init__(self, llm: LLMIntegration):
        self.llm = llm

        # System prompt for dharma content
        self.dharma_system = """You are a wise dharma teacher versed in Buddhist philosophy,
meditation practices, and contemplative traditions. You speak with clarity, compassion,
and depth. Your teachings are rooted in the Buddhadharma but accessible to all beings.
You draw from Theravada, Mahayana, and Vajrayana traditions as appropriate."""

    def generate_prayer(self, intention: str, tradition: str = "universal") -> str:
        """
        Generate a prayer/aspiration based on intention

        Args:
            intention: What the prayer is for (e.g., "healing", "peace", "wisdom")
            tradition: 'universal', 'buddhist', 'tibetan', 'zen'
        """
        prompt = f"""Generate a beautiful prayer or aspiration for {intention}.

Style: {tradition}
Length: 3-5 lines
Tone: Heartfelt, sincere, universal in scope

The prayer should:
- Be inclusive of all beings
- Express genuine aspiration
- Be poetic but not flowery
- Suitable for contemplation

Generate only the prayer text, no explanation."""

        return self.llm.generate(prompt, system_prompt=self.dharma_system, max_tokens=200, temperature=0.8)

    def generate_teaching(self, topic: str, length: str = "short") -> str:
        """
        Generate a dharma teaching on a topic

        Args:
            topic: Teaching topic (e.g., "impermanence", "compassion", "emptiness")
            length: 'short' (paragraph), 'medium' (2-3 paragraphs), 'long' (essay)
        """
        length_map = {"short": "1 paragraph", "medium": "2-3 paragraphs", "long": "4-6 paragraphs"}

        prompt = f"""Offer a teaching on {topic}.

Length: {length_map.get(length, "1 paragraph")}

The teaching should:
- Be clear and accessible
- Include practical application
- Be rooted in dharma wisdom
- Inspire practice

Generate the teaching:"""

        max_tokens_map = {"short": 300, "medium": 600, "long": 1200}

        return self.llm.generate(
            prompt, system_prompt=self.dharma_system, max_tokens=max_tokens_map.get(length, 300), temperature=0.7
        )

    def generate_meditation_instruction(self, practice: str) -> str:
        """
        Generate meditation instructions

        Args:
            practice: Type of meditation (e.g., "loving-kindness", "shamatha", "vipassana")
        """
        prompt = f"""Provide clear meditation instructions for {practice} practice.

Format:
1. Posture and preparation (brief)
2. Main practice instructions (detailed)
3. Closing (brief)

Keep it practical and clear. Suitable for beginners but also valuable for experienced practitioners.

Generate the instructions:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system, max_tokens=800, temperature=0.6)

    def generate_dedication(self) -> str:
        """Generate a dedication of merit"""
        prompt = """Generate a brief dedication of merit to conclude a practice session.

2-4 lines that dedicate any benefit to all beings.

Generate only the dedication text:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system, max_tokens=150, temperature=0.8)

    def generate_contemplation(self, theme: str) -> str:
        """
        Generate a contemplation prompt

        Args:
            theme: Theme to contemplate (e.g., "death", "interdependence", "buddha-nature")
        """
        prompt = f"""Create a contemplation exercise on {theme}.

Format:
- Opening reflection question
- 2-3 points to consider
- Closing invitation

Make it profound yet accessible.

Generate the contemplation:"""

        return self.llm.generate(prompt, system_prompt=self.dharma_system, max_tokens=400, temperature=0.7)


if __name__ == "__main__":
    print("Testing LLM Integration")
    print("=" * 60)

    # List available models
    llm = LLMIntegration(model_type="auto")
    available = llm.list_available_models()

    print("\nAvailable Models:")
    print(f"  Local: {available['local'] if available['local'] else 'None found in ./models/'}")
    print(f"  API: {available['api'] if available['api'] else 'No API keys configured'}")

    # Test dharma content generation if LLM is available
    if llm.client or llm.local_model:
        print("\n" + "=" * 60)
        print("Testing Dharma Content Generation")
        print("=" * 60)

        dharma = DharmaLLM(llm)

        print("\n1. Generating prayer for peace...")
        prayer = dharma.generate_prayer("peace and healing for all beings")
        print(f"\n{prayer}\n")

        print("=" * 60)
        print("\n2. Generating short teaching on compassion...")
        teaching = dharma.generate_teaching("compassion", length="short")
        print(f"\n{teaching}\n")

        print("=" * 60)
        print("\n[OK] LLM integration test complete")
    else:
        print("\n[INFO] No LLM available for content generation test")
        print("  To enable:")
        print("  - Add GGUF models to ./models/ directory")
        print("  - OR set ANTHROPIC_API_KEY environment variable")
        print("  - OR set OPENAI_API_KEY environment variable")
