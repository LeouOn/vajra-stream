"""Debug where LM Studio flow hangs"""

import json
import time
import urllib.error
import urllib.request


def post_json(url, payload, timeout=30):
    print(f"  Posting to {url}...")
    data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    print(f"  Opening connection (timeout={timeout})...")
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            print(f"  Connection opened in {time.time() - start:.1f}s, status={resp.status}")
            body = resp.read()
            print(f"  Body read in {time.time() - start:.1f}s, length={len(body)}")
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error after {time.time() - start:.1f}s: {e.code}")
        print(f"  Error body: {e.read().decode()[:200]}")
        raise


url = "http://localhost:8008/api/v1/llm/chat"
payload = {"messages": [{"role": "user", "content": "list populations"}], "provider": "local"}

print("Testing LM Studio flow...")
try:
    result = post_json(url, payload, timeout=120)
    print(f"Success: response len={len(result.get('response', ''))}")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
