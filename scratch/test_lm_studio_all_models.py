import json
import time
import urllib.error
import urllib.request
from pathlib import Path

# Load latest prompt
log_dir = Path(__file__).parent.parent / "session_logs"
latest_prompt_file = log_dir / "outlook_prompt_LATEST.txt"
if not latest_prompt_file.exists():
    print(f"Error: {latest_prompt_file} does not exist.")
    exit(1)

with open(latest_prompt_file, encoding="utf-8") as f:
    full_prompt = f.read()

url = "http://127.0.0.1:1234/v1"
print("Fetching all models from LM Studio...")
try:
    req = urllib.request.Request(f"{url}/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        models = [m["id"] for m in data.get("data", [])]
except Exception as e:
    print(f"Error: {e}")
    exit(1)

print(f"Found {len(models)} models.")

for model in models:
    # Skip embedding models if any
    if "embed" in model:
        continue

    print(f"\n--- Testing model: {model} ---")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.8,
        "max_tokens": 30
    }

    start_time = time.time()
    try:
        req = urllib.request.Request(
            f"{url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        # Use a 30s timeout per model for testing
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode())
            duration = time.time() - start_time
            print(f"SUCCESS in {duration:.2f}s!")
            print(f"Response: {res['choices'][0]['message']['content'][:100]}...")
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
