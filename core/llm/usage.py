"""
LLM Usage Tracker — token counting, cost estimation, and balance management.

Tracks every LLM API call: tokens sent, tokens received, estimated cost,
cumulative spending, and remaining balance. Supports multiple providers
with configurable per-model pricing.

Writes a JSONL usage log and maintains an in-memory session summary
accessible to the frontend for real-time cost display and provider switching.

Dependencies:
    os, json, time, threading (stdlib only).

Exports:
    UsageRecord — dataclass for a single API call.
    LLMUsageTracker — singleton tracker with log, balance, and reporting.
    PROVIDER_PRICING — default per-token costs for major providers.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Default pricing per MILLION tokens (USD)
# =============================================================================

PROVIDER_PRICING: dict[str, dict[str, float]] = {
    "deepseek": {
        "input_per_m": float(os.getenv("DEEPSEEK_INPUT_COST_PER_M", "0.098")),
        "output_per_m": float(os.getenv("DEEPSEEK_OUTPUT_COST_PER_M", "0.196")),
        # V4 Flash pricing on OpenRouter
        "deepseek-v4-flash_input_per_m": 0.098,
        "deepseek-v4-flash_output_per_m": 0.196,
    },
    "openai": {
        "input_per_m": float(os.getenv("OPENAI_INPUT_COST_PER_M", "2.50")),
        "output_per_m": float(os.getenv("OPENAI_OUTPUT_COST_PER_M", "10.00")),
        # gpt-4o-mini is cheaper; we detect model name and adjust at record time
        "gpt-4o-mini_input_per_m": 0.15,
        "gpt-4o-mini_output_per_m": 0.60,
    },
    "anthropic": {
        "input_per_m": float(os.getenv("ANTHROPIC_INPUT_COST_PER_M", "3.00")),
        "output_per_m": float(os.getenv("ANTHROPIC_OUTPUT_COST_PER_M", "15.00")),
        "claude-3-5-haiku_input_per_m": 0.80,
        "claude-3-5-haiku_output_per_m": 4.00,
    },
    "local": {
        "input_per_m": 0.0,
        "output_per_m": 0.0,
    },
    "lm_studio": {
        "input_per_m": 0.0,
        "output_per_m": 0.0,
    },
}


@dataclass
class UsageRecord:
    """A single LLM API call record.

    Attributes:
        timestamp: ISO-8601 timestamp of the call.
        provider: Provider identifier (``"deepseek"``, ``"openai"``, etc.).
        model: Model name (e.g. ``"deepseek-v4-flash"``, ``"gpt-4o-mini"``).
        prompt_tokens: Estimated or reported input token count.
        completion_tokens: Estimated or reported output token count.
        total_tokens: Sum of prompt + completion tokens.
        cost_usd: Estimated cost in USD.
        latency_ms: Round-trip latency in milliseconds.
        endpoint: Which API endpoint was called (``"chat"``, ``"tts"``, etc.).
        success: Whether the call succeeded.
    """

    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    provider: str = "unknown"
    model: str = "unknown"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    endpoint: str = "chat"
    success: bool = True


class LLMUsageTracker:
    """Singleton tracker for LLM API usage across all providers.

    Tracks cumulative token counts, estimated costs, and remaining balance.
    Writes a JSONL log file for persistence. Thread-safe.

    Usage:
        >>> tracker = LLMUsageTracker.get()
        >>> tracker.record(UsageRecord(provider="deepseek", prompt_tokens=500, completion_tokens=200))
        >>> print(tracker.get_summary())
    """

    _instance: Optional["LLMUsageTracker"] = None
    _lock = threading.Lock()

    def __init__(self, log_path: str | None = None, starting_balance: float = 0.0):
        """Initialise the tracker.

        Args:
            log_path: Path to JSONL usage log file (default from env or ``./logs/llm_usage.jsonl``).
            starting_balance: Initial balance in USD (0 = no limit).
        """
        self.log_path = log_path or os.getenv("LLM_USAGE_LOG_PATH", "./logs/llm_usage.jsonl")
        self.starting_balance = starting_balance

        # Cumulative counters
        self.total_calls: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0

        # Per-provider counters
        self.provider_stats: dict[str, dict] = {}

        # Session records (in-memory for frontend polling)
        self.session_records: list[UsageRecord] = []

        # Daily cost tracking (resets at first record of a new calendar day).
        # ``_daily_cost_date`` is "" until the first record sets it.
        self._daily_cost_date: str = ""
        self.daily_cost_usd: float = 0.0
        self.daily_cost_cap: float = float(os.getenv("LLM_DAILY_COST_CAP", "10"))

        # Over-cap flag — set when the daily cap or starting balance is breached.
        # Read by ``get_summary`` so the frontend can surface a banner.
        self.over_cap: bool = False

        # WS broadcast throttling.  Every ``_broadcast_every`` records we
        # invoke the registered callbacks with a fresh summary dict.
        # Callbacks receive the summary dict and are expected to schedule
        # their own async work (we are called from a sync context).
        self._on_record_callbacks: list[Callable[[dict], None]] = []
        self._broadcast_every: int = 10
        self._broadcast_counter: int = 0

        self._enabled = os.getenv("LLM_USAGE_TRACKING", "true").lower() != "false"

        # Ensure log directory exists
        if self._enabled:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)

    @classmethod
    def get(cls, log_path: str | None = None) -> "LLMUsageTracker":
        """Get or create the singleton tracker instance.

        Args:
            log_path: Path for the JSONL log (only used on first call).

        Returns:
            The singleton :class:`LLMUsageTracker`.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(log_path=log_path)
        return cls._instance

    def record(self, record: UsageRecord):
        """Record a single LLM API call.

        Updates cumulative counters, per-provider stats, session records,
        and appends to the JSONL log file.

        Args:
            record: The :class:`UsageRecord` to log.
        """
        if not self._enabled:
            return

        # Normalise total_tokens if the caller didn't set it.
        if not record.total_tokens:
            record.total_tokens = record.prompt_tokens + record.completion_tokens

        # Compute cost if the caller didn't (best-effort — never block on failure).
        if not record.cost_usd:
            try:
                record.cost_usd = self.estimate_cost(
                    record.provider, record.model,
                    record.prompt_tokens, record.completion_tokens,
                )
            except Exception:  # noqa: BLE001
                record.cost_usd = 0.0

        should_broadcast = False
        with self._lock:
            # Roll over the daily cost bucket at the first record of a new day.
            today = datetime.now().strftime("%Y-%m-%d")
            if self._daily_cost_date != today:
                self._daily_cost_date = today
                self.daily_cost_usd = 0.0
                self.over_cap = False

            # Circuit-breaker check: if we're already over the starting
            # balance or the daily cap, warn and skip accumulation. The
            # JSONL audit log is still written so the overage is visible.
            cap_breached = (
                (self.starting_balance > 0 and self.total_cost_usd >= self.starting_balance)
                or (
                    self.daily_cost_cap > 0
                    and self.daily_cost_usd >= self.daily_cost_cap
                )
            )
            if cap_breached:
                self.over_cap = True
                logger.warning(
                    "LLMUsageTracker: cost cap breached — "
                    "total=$%.4f (cap=$%.4f starting_balance=$%.4f), "
                    "daily=$%.4f (daily_cap=$%.4f). "
                    "Skipping in-memory accumulation; JSONL audit log still written.",
                    self.total_cost_usd, self.starting_balance, self.starting_balance,
                    self.daily_cost_usd, self.daily_cost_cap,
                )
                self._append_log(record)
                return

            self.total_calls += 1
            self.total_prompt_tokens += record.prompt_tokens
            self.total_completion_tokens += record.completion_tokens
            self.total_cost_usd += record.cost_usd
            self.daily_cost_usd += record.cost_usd

            # Per-provider
            if record.provider not in self.provider_stats:
                self.provider_stats[record.provider] = {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost_usd": 0.0,
                }
            ps = self.provider_stats[record.provider]
            ps["calls"] += 1
            ps["prompt_tokens"] += record.prompt_tokens
            ps["completion_tokens"] += record.completion_tokens
            ps["cost_usd"] += record.cost_usd

            # Session records (keep last 1000 in memory)
            self.session_records.append(record)
            if len(self.session_records) > 1000:
                self.session_records = self.session_records[-1000:]

            # Persist to log file
            self._append_log(record)

            # Throttled broadcast notification.
            self._broadcast_counter += 1
            if self._broadcast_every > 0 and (
                self._broadcast_counter % self._broadcast_every == 0
            ):
                should_broadcast = True

        if should_broadcast:
            summary = None
            try:
                summary = self.get_summary()
            except Exception:  # noqa: BLE001
                summary = None
            if summary is not None:
                for cb in list(self._on_record_callbacks):
                    try:
                        cb(summary)
                    except Exception:  # noqa: BLE001 — never let a callback kill record()
                        logger.debug("LLMUsageTracker on_record callback raised", exc_info=True)

    def add_on_record_callback(self, callback: Callable[[dict], None]) -> None:
        """Register a summary broadcast callback (see ``record`` docstring)."""
        with self._lock:
            self._on_record_callbacks.append(callback)

    def reset(self) -> None:
        """Reset all in-memory counters (JSONL log file is preserved)."""
        with self._lock:
            self.total_calls = 0
            self.total_prompt_tokens = 0
            self.total_completion_tokens = 0
            self.total_cost_usd = 0.0
            self.provider_stats = {}
            self.session_records = []
            self._daily_cost_date = ""
            self.daily_cost_usd = 0.0
            self.over_cap = False
            self._broadcast_counter = 0

    def _append_log(self, record: UsageRecord):
        """Append a single record to the JSONL log file."""
        try:
            with open(self.log_path, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "timestamp": record.timestamp,
                            "provider": record.provider,
                            "model": record.model,
                            "prompt_tokens": record.prompt_tokens,
                            "completion_tokens": record.completion_tokens,
                            "total_tokens": record.total_tokens,
                            "cost_usd": record.cost_usd,
                            "latency_ms": record.latency_ms,
                            "endpoint": record.endpoint,
                            "success": record.success,
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass  # Logging is best-effort — never crash on log write

    def get_summary(self) -> dict:
        """Return a JSON-serialisable usage summary for the frontend.

        Returns:
            Dict with ``total_calls``, ``total_prompt_tokens``, ``total_completion_tokens``,
            ``total_cost_usd``, ``remaining_balance``, ``provider_stats``,
            and ``recent_calls`` (last 50 records).
        """
        with self._lock:
            remaining = None
            if self.starting_balance > 0:
                remaining = round(self.starting_balance - self.total_cost_usd, 6)

            return {
                "total_calls": self.total_calls,
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "remaining_balance": remaining,
                "daily_cost_usd": round(self.daily_cost_usd, 6),
                "daily_cost_cap": self.daily_cost_cap,
                "daily_cost_date": self._daily_cost_date,
                "over_cap": self.over_cap,
                "starting_balance": self.starting_balance,
                "calls_today": self.total_calls,
                "cost_today": round(self.daily_cost_usd, 6),
                "provider_stats": {
                    p: {
                        "calls": s["calls"],
                        "prompt_tokens": s["prompt_tokens"],
                        "completion_tokens": s["completion_tokens"],
                        "cost_usd": round(s["cost_usd"], 6),
                    }
                    for p, s in self.provider_stats.items()
                },
                "recent_calls": [
                    {
                        "timestamp": r.timestamp,
                        "provider": r.provider,
                        "model": r.model,
                        "total_tokens": r.total_tokens,
                        "cost_usd": r.cost_usd,
                        "latency_ms": r.latency_ms,
                        "success": r.success,
                    }
                    for r in self.session_records[-50:]
                ],
            }

    @property
    def recent_calls(self) -> list[UsageRecord]:
        """Direct accessor alias for the in-memory record list."""
        return self.session_records

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimator (4 chars ≈ 1 token for English).

        This is a fast approximation. When the API returns actual token counts
        (usage.prompt_tokens / usage.completion_tokens), those should be used
        instead and passed directly to :meth:`record`.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    def estimate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate USD cost for a call based on provider pricing.

        Checks for model-specific pricing first (e.g. ``gpt-4o-mini`` rates),
        then falls back to the provider default.

        Args:
            provider: Provider key (``"deepseek"``, ``"openai"``, etc.).
            model: Model name for fine-grained pricing.
            prompt_tokens: Input token count.
            completion_tokens: Output token count.

        Returns:
            Estimated cost in USD.
        """
        pricing = PROVIDER_PRICING.get(provider, {})
        if not pricing:
            return 0.0

        # Check for model-specific pricing
        model_key = model.lower().replace("-", "_")
        input_rate = pricing.get(f"{model_key}_input_per_m", pricing.get("input_per_m", 0.0))
        output_rate = pricing.get(f"{model_key}_output_per_m", pricing.get("output_per_m", 0.0))

        input_cost = (prompt_tokens / 1_000_000) * input_rate
        output_cost = (completion_tokens / 1_000_000) * output_rate

        return round(input_cost + output_cost, 8)

    def reset_session(self):
        """Clear in-memory session records (does not touch the log file)."""
        with self._lock:
            self.session_records.clear()


if __name__ == "__main__":
    print("Testing LLM Usage Tracker")
    print("=" * 60)

    tracker = LLMUsageTracker.get(log_path="./logs/test_usage.jsonl")

    # Simulate a DeepSeek call
    record = UsageRecord(
        provider="deepseek",
        model="deepseek-v4-flash",
        prompt_tokens=500,
        completion_tokens=200,
        total_tokens=700,
        cost_usd=tracker.estimate_cost("deepseek", "deepseek-v4-flash", 500, 200),
        latency_ms=420.0,
        endpoint="chat",
    )
    tracker.record(record)

    # Simulate an OpenAI call
    record2 = UsageRecord(
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=1000,
        completion_tokens=300,
        total_tokens=1300,
        cost_usd=tracker.estimate_cost("openai", "gpt-4o-mini", 1000, 300),
        latency_ms=850.0,
    )
    tracker.record(record2)

    summary = tracker.get_summary()
    print(f"\nTotal calls: {summary['total_calls']}")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Total cost: ${summary['total_cost_usd']}")
    print("\nPer-provider:")
    for p, s in summary["provider_stats"].items():
        print(f"  {p}: {s['calls']} calls, {s['prompt_tokens']}+{s['completion_tokens']} tokens, ${s['cost_usd']}")

    print("\nRecent calls:")
    for r in summary["recent_calls"]:
        print(f"  {r['timestamp']} | {r['provider']}/{r['model']} | {r['total_tokens']} tok | ${r['cost_usd']}")
