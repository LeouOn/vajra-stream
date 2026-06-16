import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration
from core.outlook_generator import OutlookGenerator

print("1. Initializing LLMIntegration...")
llm = LLMIntegration(model_type="auto")
print(f"   Model type: {llm.model_type}")

print("\n2. Initializing OutlookGenerator...")
generator = OutlookGenerator(llm_integration=llm)

print("\n3. Testing _gather_astrology_context...")
start = time.time()
astro = generator._gather_astrology_context(34.0, -118.0)
print(f"   Success in {time.time() - start:.2f}s!")
print(f"   Preview: {astro[:150]}...")

print("\n4. Testing _gather_divination_data...")
start = time.time()
div_ctx, div_raw = generator._gather_divination_data(include_tarot=True, include_iching=True)
print(f"   Success in {time.time() - start:.2f}s!")
print(f"   Preview: {div_ctx[:150]}...")

print("\n5. Testing _select_sacred_entities...")
start = time.time()
entities = generator._select_sacred_entities()
print(f"   Success in {time.time() - start:.2f}s!")
print(f"   Preview: {entities[:150]}...")

print("\n6. Testing full generate_single_outlook...")
start = time.time()
result = generator.generate_single_outlook(
    lat=34.0,
    lon=-118.0,
    languages=["English"],
    genre="healing",
    include_astrology=True,
    include_tarot=True,
    include_iching=True,
)
print(f"   Success in {time.time() - start:.2f}s!")
print(f"   Narrative Preview: {result['narrative'][:200]}...")
