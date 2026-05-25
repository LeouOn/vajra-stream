"""Test LM Studio with world peace message"""
import json
import urllib.request

url = 'http://127.0.0.1:1234/v1/chat/completions'

system_prompt = """You are the Vajra.Stream AI Operator, a wise assistant designed to control a radionics board, crystal broadcasters, scalar wave generators, and blessing slideshows. Your goal is to run operations based on the user's intent. You can execute actions using tools. If the user asks to start a session, list targets, calibrate the RNG, stop automation, or tune settings, look up the appropriate tool and call it. Do not explain the tools, just call them. Once you receive the tool results, explain the outcome with deep compassion and wisdom, invoking the digital dharma theme."""

messages = [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': "Let's build the cool stuff that hatred can't shake, \n Turn strangers to neighbors for everyone's sake. \n One earth, one family, one 'we' to embrace— \n Peace is the garden where all hearts find place."}
]

tools = [{
    'type': 'function',
    'function': {
        'name': 'list_populations',
        'description': 'List all populations',
        'parameters': {'type': 'object', 'properties': {}, 'required': []}
    }
}]

payload = {
    'model': 'openyourmind-qwen3.6-35b-a3b-kuato-dpo-abliterated-uncensored-i1',
    'messages': messages,
    'tools': tools,
    'tool_choice': 'auto',
    'max_tokens': 500
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
print('Testing LM Studio with world peace message...')
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        print(f'Status: {resp.status}')
        print(f'Finish: {result["choices"][0]["finish_reason"]}')
        print(f'Content: {result["choices"][0]["message"].get("content", "")[:100]}')
        print(f'Tool calls: {result["choices"][0]["message"].get("tool_calls")}')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')