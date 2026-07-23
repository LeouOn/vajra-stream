import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

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
print(f"Status: {r.status_code}")
print(f"Tool calls: {len(data.get('tool_calls', []))}")
for tc in data.get("tool_calls", []):
    name = tc.get("tool_name", "?")
    args = tc.get("arguments", {})
    status = tc.get("status", "?")
    result = tc.get("result", "")
    print(f"  {name}({args}) -> {status}")
    if status == "success":
        print(f"    Result type: {type(result).__name__}, len: {len(str(result))}")

print(f"\nResponse:\n{data.get('response', '')[:500]}")

dbg = data.get("debug_info", {})
if dbg:
    raw = dbg.get("raw_tool_results", [])
    if raw:
        print(f"\nRaw tool results ({len(raw)}):")
        for i, r2 in enumerate(raw):
            print(
                f"  [{i}] tool={r2.get('tool')}, status={r2.get('status')}, "
                f"result_keys={list(r2.get('result', {}).keys()) if isinstance(r2.get('result'), dict) else 'NOT_DICT'}"
            )

raw_responses = dbg.get("raw_llm_responses", [])
if raw_responses:
    print(f"\nRaw LLM responses ({len(raw_responses)} turns):")
    for rr in raw_responses:
        print(
            f"  Turn {rr.get('turn')}: native={rr.get('has_native_tool_calls')}, "
            f"names={rr.get('native_tool_names')}, text_parsed={rr.get('text_parsed_tool_calls')}, "
            f"finish={rr.get('finish_reason')}"
        )
        print(f"    Content preview: {rr.get('content_preview', '')[:80]}")
