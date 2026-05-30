import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time

from core.llm_integration import LLMIntegration

print("Initializing LLMIntegration(model_type='auto')...")
llm = LLMIntegration(model_type="auto")

print(f"Detected model_type: {llm.model_type}")
print(f"Detected model_name: {llm.model_name}")
print(f"Detected base_url: {llm.base_url}")

prompt = "Say hello in one word."
system_prompt = "You are a helpful assistant."

print("\nCalling llm.generate()...")
start = time.time()
try:
    response = llm.generate(prompt=prompt, system_prompt=system_prompt, max_tokens=10)
    duration = time.time() - start
    print(f"Success in {duration:.2f}s!")
    print(f"Response: {response!r}")
except Exception as e:
    print(f"Failed to generate: {type(e).__name__}: {e}")
