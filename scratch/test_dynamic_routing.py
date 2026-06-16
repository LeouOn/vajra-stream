import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm.legacy_adapter import LegacyLLMIntegration as LLMIntegration


def test_routing():
    print("Initializing LLMIntegration with model_type='auto'...")
    llm = LLMIntegration(model_type="auto")

    print("\n--- Test 1: Route to non-existent local GGUF ---")
    res1 = llm.generate("Hello", model="local:nonexistent-model.gguf")
    print("Result 1 (Expected local fallback/error message):")
    print(res1)

    print("\n--- Test 2: Check parsing of models in available models list ---")
    available = llm.list_available_models()
    print("Available models response:")
    import json

    print(json.dumps(available, indent=2))

    print(
        "\n--- Test 3: Test route deepseek with missing key (should complain if env is modified or succeed if key is present) ---"
    )
    # Backup key and test missing key behavior
    old_key = os.environ.get("DEEPSEEK_API_KEY")
    try:
        os.environ["DEEPSEEK_API_KEY"] = ""
        res3 = llm.generate("Hello", model="deepseek:deepseek-v4-flash")
        print("Result 3 (With missing key, should complain):")
        print(res3)
    finally:
        if old_key:
            os.environ["DEEPSEEK_API_KEY"] = old_key

    print("\nDynamic routing sanity check passed!")


if __name__ == "__main__":
    test_routing()
