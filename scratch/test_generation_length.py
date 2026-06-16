import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration
from core.outlook_generator import OutlookGenerator

print("Initializing...")
llm = LLMIntegration(model_type="auto")
generator = OutlookGenerator(llm_integration=llm)

print("\nGathering prompt...")
prompt = generator.generate_single_outlook(
    lat=34.0,
    lon=-118.0,
    languages=["English"],
    genre="healing",
    include_astrology=True,
    include_tarot=True,
    include_iching=True,
)

# Extract prompt that was logged
log_dir = Path(__file__).parent.parent / "session_logs"
latest_prompt_file = log_dir / "outlook_prompt_LATEST.txt"
with open(latest_prompt_file, encoding="utf-8") as f:
    full_prompt = f.read()

print(f"Prompt length: {len(full_prompt)} chars")

print("\nTesting generation with max_tokens=50...")
start = time.time()
response = llm.generate(
    prompt=full_prompt, system_prompt="You are a transcendent oracle and dharma scribe.", max_tokens=50, temperature=0.8
)
duration = time.time() - start
print(f"Completed in {duration:.2f}s!")
print(f"Response: {response!r}")
print(f"Estimated speed: {len(response.split()) / duration:.2f} words/sec")
