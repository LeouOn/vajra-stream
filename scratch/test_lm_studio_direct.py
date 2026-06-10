import json
import time
import urllib.error
import urllib.request

url = "http://127.0.0.1:1234/v1"
print("Probing LM Studio models list...")
try:
    req = urllib.request.Request(f"{url}/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print("Reachable! Available models:")
        models = [m["id"] for m in data.get("data", [])]
        for model in models:
            print(f" - {model}")

        if not models:
            print("No models loaded in LM Studio!")
            exit(1)

        selected_model = models[0]
except Exception as e:
    print(f"Error querying models: {e}")
    exit(1)

print(f"\nAttempting chat completion with model: {selected_model}...")
payload = {
    "model": selected_model,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello in one word."},
    ],
    "temperature": 0.7,
    "max_tokens": 10,
}

start_time = time.time()
try:
    req = urllib.request.Request(
        f"{url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode())
        duration = time.time() - start_time
        print(f"Success in {duration:.2f}s!")
        print("Response JSON:")
        print(json.dumps(res, indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"General Error: {e}")
