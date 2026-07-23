import os
import sys

sys.path.insert(0, os.getcwd())

print("=== Combined tool test ===")
from backend.core.llm_agent.tools import TOOL_REGISTRY, get_system_status  # noqa: E402

assert "get_system_status" in TOOL_REGISTRY, "MISSING get_system_status"
assert "get_statistics" in TOOL_REGISTRY, "MISSING get_statistics"
assert TOOL_REGISTRY["get_statistics"] is TOOL_REGISTRY["get_system_status"], "not aliased"
print("TOOL_REGISTRY: OK")

result = get_system_status()
print(f"Keys: {list(result.keys())}")
print(f"Summary: {result['summary']}")
assert "population_stats" in result
assert "automation_status" in result
assert "summary" in result
print("get_system_status: OK")

print("\n=== Alias test ===")
from backend.app.api.v1.endpoints.llm import _resolve_tool_name  # noqa: E402

for name, expected in [
    ("get_system_status", "get_system_status"),
    ("get_statistics", "get_system_status"),
    ("broadcast_crystal", "broadcast_healing"),
    ("set_scalar_frequency", "set_audio_frequency"),
    ("list_targets", "list_populations"),
]:
    resolved = _resolve_tool_name(name)
    assert resolved == expected, f"{name} -> {resolved} != {expected}"
    print(f"  {name} -> {resolved} OK")
print("All aliases pass")

print("\n=== End-to-end API test ===")
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

client = TestClient(app)
r = client.post(
    "/api/v1/llm/chat",
    json={
        "messages": [{"role": "user", "content": "get statistics"}],
        "provider": "auto",
        "debug_mode": True,
    },
)
data = r.json()
tcs = data.get("tool_calls", [])
print(f"Tool calls: {len(tcs)}")
for tc in tcs:
    name = tc.get("tool_name")
    status = tc.get("status")
    print(f"  {name} -> {status}")
dbg = data.get("debug_info", {})
responses = dbg.get("raw_llm_responses", [])
if responses:
    print(f"LLM turns: {len(responses)}")
    for rr in responses:
        print(
            f"  Turn {rr.get('turn')}: native={rr.get('native_tool_names')}, text_parsed={rr.get('text_parsed_tool_calls')}"
        )
response = data.get("response", "")
print(f"\nResponse length: {len(response)}")
print(f"Preview: {response[:300]}")
