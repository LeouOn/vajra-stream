import sys, os, json
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
from backend.app.main import app
client = TestClient(app)

print("=== Test with debug_mode=True ===")
r = client.post("/api/v1/llm/chat", json={
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "auto",
    "debug_mode": True,
})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Tool calls: {len(data.get('tool_calls', []))}")

dbg = data.get("debug_info", {})
if dbg:
    print(f"\n--- DEBUG INFO ---")
    print(f"Provider selected: {dbg.get('provider_selected')}")
    print(f"Model requested: {dbg.get('model_requested')}")
    print(f"Tools count: {dbg.get('tools_count')}")
    print(f"Env keys: {dbg.get('env_keys')}")
    print(f"System prompt length: {dbg.get('system_prompt_length')}")
    print(f"System prompt preview: {dbg.get('system_prompt', '')[:150]}...")
    
    raw = dbg.get("raw_llm_responses", [])
    print(f"\nRaw LLM responses ({len(raw)} turns):")
    for r in raw:
        print(f"  Turn {r.get('turn')}: native_tool_calls={r.get('has_native_tool_calls')} "
              f"names={r.get('native_tool_names')} "
              f"text_parsed={r.get('text_parsed_tool_calls')} "
              f"finish={r.get('finish_reason')}")
        print(f"    Content preview: {r.get('content_preview', '')[:100]}")
else:
    print("No debug_info returned!")

print(f"\nResponse (first 200): {data.get('response', '')[:200]}")
