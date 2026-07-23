import os
import sys

sys.path.insert(0, os.getcwd())
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

client = TestClient(app)

# Test 1: Post-update checkout — does tool calling work?
r = client.post(
    "/api/v1/llm/chat",
    json={
        "messages": [{"role": "user", "content": "start rng session"}],
        "provider": "auto",
    },
)
data = r.json()
print(
    f"start rng session: status={r.status_code}, tool_calls={len(data.get('tool_calls', []))}, response={data.get('response', '')[:120]}..."
)

# Test 2: Remaining quick tests
for prompt in ["forge sigil for peace", "cast tarot", "get automation status"]:
    r = client.post(
        "/api/v1/llm/chat",
        json={
            "messages": [{"role": "user", "content": prompt}],
            "provider": "auto",
        },
    )
    data = r.json()
    tcs = data.get("tool_calls", [])
    names = [tc.get("tool_name") for tc in tcs]
    ok = any(tc.get("status") == "success" for tc in tcs)
    print(f"{prompt}: status={r.status_code}, tools={names}, ok={ok}, preview={data.get('response', '')[:80]}...")
