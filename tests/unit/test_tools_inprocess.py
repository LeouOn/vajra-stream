"""LLM agent tools must run in-process — no HTTP back into this server.

The old ``APIClient`` made every tool POST/GET ``/api/v1/...`` against
``localhost:8008``. Under a saturated worker that socket hop can deadlock,
it couples tools to a hardcoded port, and endpoint drift turned several
paths into silent 404s (``/rng/session/{id}/reading``, ``/rng/attunement``,
``/practices/active``, ``/api/v1/current``). The client class was deleted;
this guard keeps it dead.
"""

from pathlib import Path

import pytest

TOOLS_PATH = Path(__file__).resolve().parents[2] / "backend" / "core" / "llm_agent" / "tools.py"


@pytest.mark.unit
def test_tools_contain_no_self_http_calls():
    source = TOOLS_PATH.read_text(encoding="utf-8")
    assert "requests.post" not in source
    assert "requests.get" not in source
    assert "requests.put" not in source
    assert '"/api/v1/' not in source
    assert "get_client" not in source
    assert "APIClient" not in source


@pytest.mark.unit
def test_outlook_tools_call_container_in_process():
    source = TOOLS_PATH.read_text(encoding="utf-8")
    assert "container.outlook.generate_single" in source
    assert "container.outlook.generate_epic" in source
