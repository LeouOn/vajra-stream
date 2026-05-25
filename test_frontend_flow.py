"""Test full flow mimicking frontend"""
import json
import urllib.request
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def test_backend_with_local():
    """Test the backend with provider=local like the frontend does"""
    url = "http://localhost:8008/api/v1/llm/chat"

    # This is what the frontend sends (with message history)
    payload = {
        "messages": [
            {"role": "assistant", "content": "I am your AI operator. How shall we direct the intention today?"},
            {"role": "user", "content": "Let's build the cool stuff that hatred can't shake, \n Turn strangers to neighbors for everyone's sake. \n One earth, one family, one \"we\" to embrace— \n Peace is the garden where all hearts find place."}
        ],
        "provider": "auto"
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    print("Testing with message history (like frontend does)...")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Status: {resp.status}")
            print(f"Response: {result.get('response', '')[:200]}")
            print(f"Tool calls: {len(result.get('tool_calls', []))}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

def test_backend_simple():
    """Test with just a simple message"""
    url = "http://localhost:8008/api/v1/llm/chat"
    payload = {
        "messages": [{"role": "user", "content": "list populations"}],
        "provider": "auto"
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    print("\nTesting with simple message...")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Status: {resp.status}")
            print(f"Response: {result.get('response', '')[:200]}")
            print(f"Tool calls: {len(result.get('tool_calls', []))}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_backend_with_local()
    test_backend_simple()