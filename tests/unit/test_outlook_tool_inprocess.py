"""Outlook chat tools must call the container, not HTTP back into this process."""

from pathlib import Path

import pytest

TOOLS_PATH = Path(__file__).resolve().parents[2] / "backend" / "core" / "llm_agent" / "tools.py"


@pytest.mark.unit
def test_outlook_tools_do_not_self_http():
    source = TOOLS_PATH.read_text(encoding="utf-8")
    assert '_post("/api/v1/outlook/generate_single"' not in source
    assert '_post("/api/v1/outlook/generate_epic"' not in source
    assert "container.outlook.generate_single" in source
    assert "container.outlook.generate_epic" in source
