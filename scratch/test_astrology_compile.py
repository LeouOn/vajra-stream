import asyncio
import logging
import os
import sys

# Configure stdout/stderr for Unicode encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Adjust path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.api.v1.endpoints.llm import compile_astrology_context

# Mock setup logging
logging.basicConfig(level=logging.INFO)


async def test_compile():
    print("Testing compile_astrology_context()...")
    context = await compile_astrology_context()
    print("--- ASTROLOGY CONTEXT OUTPUT ---")
    print(context)
    print("--------------------------------")

    # Assertions
    assert "COSMIC CLOCKWORK SYSTEM" in context
    assert "Western Tropical Astrology" in context
    assert "Indian Vedic Astrology" in context
    assert "Chinese Lunisolar Astrology" in context
    assert "Planetary Coordinates" in context
    assert "Wu Xing" in context
    assert "Tithi" in context
    print("SUCCESS: Context generated with all expected components!")


if __name__ == "__main__":
    asyncio.run(test_compile())
