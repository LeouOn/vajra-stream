"""Test LM Studio with message history format"""
import json
import urllib.request

url = 'http://127.0.0.1:1234/v1/chat/completions'

# Simulate what the frontend sends with message history
messages = [
    {"role": "assistant", "content": "I am your AI operator. How shall we direct the intention today?"},
    {"role": "user", "content": "Let's build the cool stuff that hatred can't shake, \n Turn strangers to neighbors for everyone's sake. \n One earth, one family, one 'we' to embrace— \n Peace is the garden where all hearts find place."}
]

tools = [{
    "type": "function",
    "function": {
        "name": "list_populations",
        "description": "List all populations",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}]

payload = {
    "model": "openyourmind-qwen3.6-35b-a3b-kuato-dpo-abliterated-uncensored-i1",
    "messages": messages,
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 300
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

print("Testing LM Studio with message history...")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        print(f"Finish reason: {result['choices'][0]['finish_reason']}")
        print(f"Content: {result['choices'][0]['message'].get('content', '')[:100]}")
        print(f"Tool calls: {result['choices'][0]['message'].get('tool_calls')}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

# Now test with only user messages (the fix)
print("\n" + "="*60)
print("Testing with only user messages (the fix)...")
user_only_messages = [
    {"role": "user", "content": "Let's build the cool stuff that hatred can't shake, \n Turn strangers to neighbors for everyone's sake. \n One earth, one family, one 'we' to embrace— \n Peace is the garden where all hearts find place."}
]

payload2 = {
    "model": "openyourmind-qwen3.6-35b-a3b-kuato-dpo-abliterated-uncensored-i1",
    "messages": user_only_messages,
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 300
}

data2 = json.dumps(payload2).encode("utf-8")
req2 = urllib.request.Request(url, data=data2, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req2, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        print(f"Finish reason: {result['choices'][0]['finish_reason']}")
        print(f"Content: {result['choices'][0]['message'].get('content', '')[:100]}")
        print(f"Tool calls: {result['choices'][0]['message'].get('tool_calls')}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")