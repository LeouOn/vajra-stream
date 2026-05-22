#!/usr/bin/env python3
"""
Full Stack Integration Tests for Vajra.Stream
Tests backend API, WebSocket, and frontend connectivity
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime

import requests

BACKEND_URL = "http://localhost:8008"
WEBSOCKET_URL = "ws://localhost:8008/ws"
LLM_BASE_URL = "http://127.0.0.1:1234"
LLM_MODEL = "gemma-4-e4b-it-uncensored-max-opus-4.7"


def test_backend_health():
    print("\n" + "=" * 60)
    print("TEST 1: Backend Health Check")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        print("  [OK] Backend health check passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Backend health check failed: {e}")
        return False


def test_backend_api_root():
    print("\n" + "=" * 60)
    print("TEST 2: Backend API Root")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        print("  [OK] Backend API root passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Backend API root failed: {e}")
        return False


def test_audio_generate_api():
    print("\n" + "=" * 60)
    print("TEST 3: Audio Generate API")
    print("=" * 60)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/audio/generate",
            json={
                "frequency": 528.0,
                "duration": 1.0,
                "volume": 0.8,
                "prayer_bowl_mode": True,
                "harmonic_strength": 0.3,
                "modulation_depth": 0.05,
            },
            timeout=30,
        )
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response status: {data.get('status')}")
        print(f"  Audio generated: {data.get('audio_generated', False)}")
        if data.get("status") == "success":
            print("  [OK] Audio generate API passed")
            return True
        else:
            print(f"  [FAIL] Audio generation failed: {data.get('detail')}")
            return False
    except Exception as e:
        print(f"  [FAIL] Audio generate API failed: {e}")
        return False


def test_audio_play_api():
    print("\n" + "=" * 60)
    print("TEST 4: Audio Play API")
    print("=" * 60)

    try:
        resp = requests.post(f"{BACKEND_URL}/api/v1/audio/play", json={"hardware_level": 2}, timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {data}")
        if data.get("status") in ["success", "playing"]:
            print("  [OK] Audio play API passed")
            return True
        else:
            print("  [FAIL] Audio play API returned error")
            return False
    except Exception as e:
        print(f"  [FAIL] Audio play API failed: {e}")
        return False


def test_audio_status_api():
    print("\n" + "=" * 60)
    print("TEST 5: Audio Status API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/audio/status", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        print("  [OK] Audio status API passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Audio status API failed: {e}")
        return False


def test_websocket_connectivity():
    print("\n" + "=" * 60)
    print("TEST 6: WebSocket Connectivity")
    print("=" * 60)

    ws = None
    try:
        import websocket as ws_client

        ws = ws_client.create_connection(WEBSOCKET_URL, timeout=10)
        print(f"  Connected to {WEBSOCKET_URL}")

        # Wait for initial message
        data = ws.recv()
        print(f"  Received: {data[:100]}...")

        # Send a test message
        ws.send(json.dumps({"type": "ping", "timestamp": datetime.now().isoformat()}))
        print("  Sent ping message")

        ws.close()
        print("  [OK] WebSocket connectivity passed")
        return True
    except Exception as e:
        print(f"  [FAIL] WebSocket connectivity failed: {e}")
        if ws:
            ws.close()
        return False


def test_sessions_api():
    print("\n" + "=" * 60)
    print("TEST 7: Sessions API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/sessions/", timeout=5)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
        print("  [OK] Sessions API passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Sessions API failed: {e}")
        return False


def test_astrology_api():
    print("\n" + "=" * 60)
    print("TEST 8: Astrology API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/astrology/current", timeout=5)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"  Response: {str(resp.json())[:100]}...")
            print("  [OK] Astrology API passed")
            return True
        else:
            print("  [FAIL] Astrology API returned non-200 status")
            return False
    except Exception as e:
        print(f"  [FAIL] Astrology API failed: {e}")
        return False


def test_scalar_waves_api():
    print("\n" + "=" * 60)
    print("TEST 9: Scalar Waves API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/scalar/status", timeout=5)
        print(f"  Status: {resp.status_code}")
        if resp.status_code in [200, 404]:
            print(f"  Response: {resp.json() if resp.status_code == 200 else 'Not Found (optional)'}")
            print("  [OK] Scalar Waves API passed (or not implemented yet)")
            return True
        else:
            print("  [FAIL] Scalar Waves API returned unexpected status")
            return False
    except Exception as e:
        print(f"  [FAIL] Scalar Waves API failed: {e}")
        return False


def test_llm_integration():
    print("\n" + "=" * 60)
    print("TEST 10: LLM Integration (Local Gemma)")
    print("=" * 60)

    try:
        # Test chat completion
        resp = requests.post(
            f"{LLM_BASE_URL}/v1/chat/completions",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a helpful meditation guide."},
                    {"role": "user", "content": "Give me a one-sentence meditation tip."},
                ],
                "max_tokens": 50,
                "temperature": 0.7,
            },
            timeout=30,
        )
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            print(f"  Response: {reply}")
            print("  [OK] LLM integration passed")
            return True
        else:
            print(f"  [FAIL] LLM returned error: {resp.text}")
            return False
    except Exception as e:
        print(f"  [FAIL] LLM integration failed: {e}")
        return False


def test_prayer_wheel_llm_flow():
    print("\n" + "=" * 60)
    print("TEST 11: Prayer Wheel → LLM Flow")
    print("=" * 60)

    try:
        from core.audio_generator import ScalarWaveGenerator
        from core.prayer_wheel import PrayerWheel

        class LocalLLM:
            def __init__(self):
                self.model_type = "local"

            def generate(self, prompt, system_prompt=None, max_tokens=200, temperature=0.7):
                resp = requests.post(
                    f"{LLM_BASE_URL}/v1/chat/completions",
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=60,
                )
                return resp.json()["choices"][0]["message"]["content"]

        llm = LocalLLM()
        audio = ScalarWaveGenerator()
        pw = PrayerWheel(llm_integration=llm, audio_generator=audio, tts_engine=None)

        prayer = pw.generate_prayer(intention="peace", use_llm=True)
        print(f"  Generated prayer (first 100 chars): {prayer[:100]}...")

        print("  [OK] Prayer Wheel → LLM flow passed")
        return True
    except Exception as e:
        print(f"  [FAIL] Prayer Wheel → LLM flow failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dharma_tales_api():
    print("\n" + "=" * 60)
    print("TEST 12: Dharma Tales API")
    print("=" * 60)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/dharma/tale/generate",
            json={"theme": "compassion", "tradition": "zen", "length": "short"},
            timeout=30,
        )
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  Tale: {data.get('tale', '')[:100]}...")
            print("  [OK] Dharma Tales API passed")
            return True
        else:
            print(f"  [FAIL] Dharma Tales API returned: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Dharma Tales API failed: {e}")
        return False


def test_personal_healing_api():
    print("\n" + "=" * 60)
    print("TEST 13: Personal Healing API")
    print("=" * 60)

    try:
        resp = requests.get(f"{BACKEND_URL}/api/v1/healing/chakra/all", timeout=10)
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            chakras = list(data.get("chakras", {}).keys())
            print(f"  Chakras: {chakras}")
            print("  [OK] Personal Healing API passed")
            return True
        else:
            print(f"  [FAIL] Personal Healing API returned: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Personal Healing API failed: {e}")
        return False


def test_healing_sequence():
    print("\n" + "=" * 60)
    print("TEST 14: Healing Sequence API")
    print("=" * 60)

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/v1/healing/chakra/balance",
            json={"intention": "healing", "sequence_type": "full"},
            timeout=10,
        )
        print(f"  Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            seq = data.get("sequence", {})
            chakra_names = [c["name"] for c in seq.get("chakras", [])]
            print(f"  Sequence: {chakra_names}")
            print("  [OK] Healing Sequence API passed")
            return True
        else:
            print(f"  [FAIL] Healing Sequence API returned: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] Healing Sequence API failed: {e}")
        return False


def main():
    print("\n" + "#" * 60)
    print("# VAJRA.STREAM - FULL STACK INTEGRATION TESTS")
    print(f"# Backend: {BACKEND_URL}")
    print(f"# WebSocket: {WEBSOCKET_URL}")
    print(f"# LLM: {LLM_MODEL} at {LLM_BASE_URL}")
    print("#" * 60)

    tests = [
        ("Backend Health", test_backend_health),
        ("Backend API Root", test_backend_api_root),
        ("Audio Generate API", test_audio_generate_api),
        ("Audio Play API", test_audio_play_api),
        ("Audio Status API", test_audio_status_api),
        ("WebSocket Connectivity", test_websocket_connectivity),
        ("Sessions API", test_sessions_api),
        ("Astrology API", test_astrology_api),
        ("Scalar Waves API", test_scalar_waves_api),
        ("LLM Integration", test_llm_integration),
        ("Prayer Wheel → LLM Flow", test_prayer_wheel_llm_flow),
        ("Dharma Tales API", test_dharma_tales_api),
        ("Personal Healing API", test_personal_healing_api),
        ("Healing Sequence API", test_healing_sequence),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"  [FAIL] Test failed with exception: {e}")
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

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
