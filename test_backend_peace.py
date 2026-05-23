"""Test the actual backend flow - ASCII safe"""
import json
import urllib.request
import urllib.error
import sys

def post_json(url, payload, timeout=30):
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

url = "http://localhost:8008/api/v1/llm/chat"

# Test with provider=local and peace message
payload = {
    "messages": [
        {"role": "assistant", "content": "I am your AI operator. How shall we direct the intention today?"},
        {"role": "user", "content": "Let's build the cool stuff that hatred can't shake, \n Turn strangers to neighbors for everyone's sake. \n One earth, one family, one "we" to embrace— \n Peace is the garden where all hearts find place."}
    ],
    "provider": "local"
}

print("Testing backend with message history and provider=local...")
try:
    result = post_json(url, payload, timeout=180)
    print("SUCCESS!")
    resp = result.get('response', '')[:200].encode('ascii', 'replace').decode('ascii')
    print(f"Response: {resp}")
    print(f"Tool calls: {len(result.get('tool_calls', []))}")
    for tc in result.get("tool_calls", []):
        print(f"  - {tc.get('tool_name')}: {tc.get('status')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode()[:300])
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")