#!/usr/bin/env python3
"""
Test all data flows in Vajra.Stream with local LLM at http://127.0.0.1:1234
Tests: PrayerWheel → DharmaTales → LLM → Audio → PersonalHealing
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import requests

LLM_BASE_URL = "http://127.0.0.1:1234"
LLM_MODEL = "gemma-4-e4b-it-uncensored-max-opus-4.7"


class LocalLLMIntegration:
    """LLM integration for local gemma endpoint with OpenAI-compatible API"""

    def __init__(self, base_url: str = LLM_BASE_URL, model: str = LLM_MODEL):
        self.base_url = base_url
        self.model = model
        self.model_type = "local"

    def generate(self, prompt: str, system_prompt: str = None, max_tokens: int = 500, temperature: float = 0.7) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
            timeout=120,
        )

        if resp.status_code != 200:
            raise Exception(f"LLM error: {resp.status_code} - {resp.text}")

        return resp.json()["choices"][0]["message"]["content"]

    def list_models(self):
        resp = requests.get(f"{self.base_url}/v1/models")
        return resp.json()


def test_llm_connectivity():
    print("\n" + "=" * 60)
    print("TEST 1: LLM Connectivity")
    print("=" * 60)

    llm = LocalLLMIntegration()

    print(f"  Base URL: {LLM_BASE_URL}")
    print(f"  Model: {LLM_MODEL}")

    models = llm.list_models()
    print(f"  Available models: {[m['id'] for m in models.get('data', [])]}")

    result = llm.generate("Respond with exactly one word: hello")
    print(f"  Test generation: '{result}'")
    print("  [OK] LLM connectivity OK")
    return True


def test_prayer_wheel_with_llm():
    print("\n" + "=" * 60)
    print("TEST 2: Prayer Wheel → LLM → Prayer Text")
    print("=" * 60)

    try:
        from core.audio_generator import ScalarWaveGenerator
        from core.prayer_wheel import PrayerWheel
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

    llm = LocalLLMIntegration()
    audio = ScalarWaveGenerator()

    pw = PrayerWheel(llm_integration=llm, audio_generator=audio, tts_engine=None)

    print("  Generating blessing for 'healing' intention...")
    blessing = pw.generate_prayer(intention="healing", use_llm=True)

    print(f"  Generated prayer:\n  {blessing[:200]}...")
    print("  [OK] Prayer Wheel → LLM OK")
    return True


def test_dharma_tales_with_llm():
    print("\n" + "=" * 60)
    print("TEST 3: DharmaTalesGenerator → LLM → Teaching Story")
    print("=" * 60)

    try:
        from core.dharma_tales import DharmaTalesGenerator
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

    llm = LocalLLMIntegration()
    dtg = DharmaTalesGenerator(llm_integration=llm)

    print("  Generating teaching story about impermanence...")
    story = dtg.generate_tale(theme="impermanence", tradition="zen", length="short")

    print(f"  Generated story:\n  {story[:300]}...")
    print("  [OK] DharmaTalesGenerator → LLM OK")
    return True


def test_audio_generation():
    print("\n" + "=" * 60)
    print("TEST 4: AudioGenerator → Frequency Waves")
    print("=" * 60)

    try:
        from core.audio_generator import ScalarWaveGenerator
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

    gen = ScalarWaveGenerator()

    print("  Generating Schumann resonance (7.83 Hz)...")
    wave = gen.generate_schumann_resonance(duration=1)
    print(f"    Wave shape: {wave.shape}, duration: 1s")

    print("  Generating layered frequencies (528 Hz + 639 Hz)...")
    freqs = [(528, 0.5), (639, 0.5)]
    wave = gen.layer_frequencies(freqs, duration=1)
    print(f"    Wave shape: {wave.shape}")

    print("  [OK] Audio generation OK")
    return True


def test_personal_healing_module():
    print("\n" + "=" * 60)
    print("TEST 5: PersonalHealingModule → Chakra Balancing")
    print("=" * 60)

    try:
        from modules.personal_healing import PersonalHealingModule
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

    phm = PersonalHealingModule()

    print("  Running chakra healing sequence for 'balance' intention...")
    sequence = phm.create_chakra_healing_sequence(sequence_type="full", duration_per=1)
    print(f"    Sequence type: {sequence['type']}")
    print(f"    Total duration: {sequence['total_duration']}s")
    print(f"    Chakras: {[c['name'] for c in sequence['chakras']]}")
    print("  [OK] PersonalHealingModule OK")
    return True


def test_full_flow():
    print("\n" + "=" * 60)
    print("TEST 6: Full Flow - PrayerWheel → DharmaTales → Audio")
    print("=" * 60)

    try:
        from core.audio_generator import ScalarWaveGenerator
        from core.dharma_tales import DharmaTalesGenerator
        from core.prayer_wheel import PrayerWheel
        from modules.personal_healing import PersonalHealingModule
    except ImportError as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

    llm = LocalLLMIntegration()
    audio = ScalarWaveGenerator()
    pw = PrayerWheel(llm_integration=llm, audio_generator=audio, tts_engine=None)
    dtg = DharmaTalesGenerator(llm_integration=llm)
    phm = PersonalHealingModule()

    intention = "healing"

    print(f"  Intention: {intention}")
    print("  Step 1: Generate prayer...")
    prayer = pw.generate_prayer(intention=intention, use_llm=True)
    print(f"    Prayer: {prayer[:100]}...")

    print("  Step 2: Generate teaching story...")
    story = dtg.generate_tale(theme="compassion", tradition="buddhist", length="short")
    print(f"    Story: {story[:100]}...")

    print("  Step 3: Get chakra frequencies...")
    sequence = phm.create_chakra_healing_sequence(sequence_type="full", duration_per=1)
    print(f"    Chakras: {[c['name'] for c in sequence['chakras']]}")

    print("  Step 4: Generate layered audio...")
    freqs = []
    for c in sequence["chakras"][:3]:
        freq = c["frequencies"]["root"]
        freqs.append((freq, 0.3))
    wave = audio.layer_frequencies(freqs, duration=1)
    print(f"    Wave shape: {wave.shape}")

    print("  [OK] Full flow OK")
    return True


def main():
    print("\n" + "#" * 60)
    print("# VAJRA.STREAM - DATA FLOW TESTS")
    print(f"# LLM: {LLM_MODEL} at {LLM_BASE_URL}")
    print("#" * 60)

    tests = [
        ("LLM Connectivity", test_llm_connectivity),
        ("Prayer Wheel → LLM", test_prayer_wheel_with_llm),
        ("Dharma Tales → LLM", test_dharma_tales_with_llm),
        ("Audio Generation", test_audio_generation),
        ("Personal Healing Module", test_personal_healing_module),
        ("Full Flow Integration", test_full_flow),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  [FAIL] FAILED: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {status}: {name}")

    passed = sum(1 for _, r in results if r)
    print(f"\n  Total: {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
