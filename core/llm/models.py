# core/llm/models.py
"""Pydantic models for the LLM provider layer."""
import time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = "auto"
    model: str | None = None
    max_tokens: int = Field(default=1000, ge=1, le=32000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    system_prompt: str | None = None
    stream: bool = False
    tools: list[ToolDefinition] = Field(default_factory=list)
    include_astrology: bool = False
    include_anatomy: bool = False
    include_hardware: bool = False
    astrology_data: dict[str, Any] | None = None


class ChatChunk(BaseModel):
    content: str
    done: bool = False
    provider: str
    model: str


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    finish_reason: str = "stop"
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class HealthStatus(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float = 0.0
    error: str | None = None
    last_checked: float = Field(default_factory=time.time)
    models_available: int = 0


class ModelInfo(BaseModel):
    id: str
    provider: str
    context_window: int | None = None
    supports_tools: bool = False
    supports_streaming: bool = True


class ProviderConfig(BaseModel):
    name: str
    priority: int = Field(ge=0, le=100)
    enabled: bool = True
    api_key_env: str | None = None
    base_url_env: str | None = None
    default_model: str | None = None
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    extra: dict[str, Any] = Field(default_factory=dict)
