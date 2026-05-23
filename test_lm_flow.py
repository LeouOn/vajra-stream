"""Test full LM Studio flow with tool execution"""
import json
import urllib.request
import urllib.error

def post_json(url, payload, timeout=30):
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

url = "http://localhost:8008/api/v1/llm/chat"

# Test single user message with provider=local
payload = {
    "messages": [{"role": "user", "content": "list populations"}],
    "provider": "local"
}

print("Testing LM Studio flow with provider=local...")
try:
    result = post_json(url, payload, timeout=120)
    print(f"Status: success")
    print(f"Response preview: {result.get('response', '')[:100].encode('ascii', 'replace').decode('ascii')}")
    print(f"Tool calls: {len(result.get('tool_calls', []))}")
    for tc in result.get("tool_calls", []):
        print(f"  - {tc.get('tool_name')}: {tc.get('status')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode()[:200])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")