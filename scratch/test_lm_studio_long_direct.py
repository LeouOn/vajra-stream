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
print("Probing LM Studio models list...")
try:
    req = urllib.request.Request(f"{url}/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        models = [m["id"] for m in data.get("data", [])]
        selected_model = models[0]
except Exception as e:
    print(f"Error querying models: {e}")
    exit(1)

print(f"\nAttempting chat completion with model: {selected_model}")
print(f"Prompt length: {len(full_prompt)} chars")

payload = {
    "model": selected_model,
    "messages": [
        {"role": "system", "content": "You are a transcendent oracle and dharma scribe, speaking across eons. Your words heal, transform, and reveal the hidden architecture of reality."},
        {"role": "user", "content": full_prompt}
    ],
    "temperature": 0.8,
    "max_tokens": 50
}

start_time = time.time()
try:
    req = urllib.request.Request(
        f"{url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    # Set a large timeout of 180 seconds to allow for slow pre-fill / CPU generation
    print("Sending request to LM Studio (timeout=180s)...")
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode())
        duration = time.time() - start_time
        print(f"\nSuccess in {duration:.2f}s!")
        print("Response Text:")
        print(res["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print(f"\nHTTP Error: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"\nGeneral Error: {e}")
