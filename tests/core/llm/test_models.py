# tests/core/llm/test_models.py
import pytest
from pydantic import ValidationError

from core.llm.models import (
    ChatMessage,
    ChatRequest,
    HealthStatus,
    ProviderConfig,
)


def test_chat_message_required_role():
    msg = ChatMessage(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"


def test_chat_request_defaults():
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    assert req.provider == "auto"
    assert req.model is None
    assert req.max_tokens == 1000
    assert req.temperature == 0.7


def test_chat_request_temperature_bounds():
    with pytest.raises(ValidationError):
        ChatRequest(
            messages=[ChatMessage(role="user", content="hi")],
            temperature=2.5,
        )


def test_health_status_defaults():
    h = HealthStatus(provider="openai", healthy=True)
    assert h.latency_ms == 0.0
    assert h.error is None
    assert h.last_checked > 0


def test_provider_config_priority_must_be_non_negative():
    with pytest.raises(ValidationError):
        ProviderConfig(name="openai", priority=-1)
