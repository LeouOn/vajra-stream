#!/usr/bin/env python3
"""
Test LLM Tool Calling and Narrative Magic Operations
Launches a temporary backend server and exercises:
- Chat command center local rule-based parsing and tool execution
- Radionics narrative generation
- Global intention mapping and Solfeggio frequency recommendations
- Automatic lifecycle cleanup of the server
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure console encoding for Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


PORT = 8012
BASE_URL = f"http://localhost:{PORT}"


def print_title(title):
    print("\n" + "=" * 80)
    print(f" {title.upper()}")
    print("=" * 80)


def post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  [HTTP ERROR {e.code}]: {e.read().decode()[:300]}")
        raise
    except Exception as e:
        print(f"  [CONNECTION ERROR]: {e}")
        raise


def main():
    print_title("LLM Tool Calling & Narrative Magic Test Suite")

    # 1. Start temporary backend server
    print(f"1. Starting backend server on port {PORT}...")
    server_process = subprocess.Popen(
        [sys.executable, "run.py", "serve", "--port", str(PORT)],
        cwd=str(PROJECT_ROOT),
        shell=True if sys.platform == "win32" else False,
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )

    # Wait for server to boot up
    time.sleep(5)
    print("   Server should be ready.")

    try:
        # Test 1: Verify server health
        print("\n2. Checking server health...")
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"   Health Check: Status={health.get('status')} | Service={health.get('service')}")

        # Test 2: Chat command - list populations
        print_title("Test 2: Chat command 'list populations'")
        payload = {"messages": [{"role": "user", "content": "list populations"}], "provider": "auto"}
        status, res = post_json("/api/v1/llm/chat", payload)
        print(f"   Status: {status}")
        print(f"   Response:\n{res.get('response')[:300]}...\n")
        print(f"   Tool calls executed: {len(res.get('tool_calls', []))}")
        for tc in res.get("tool_calls", []):
            print(f"     - Tool: {tc.get('tool_name')} | Status: {tc.get('status')}")

        # Test 3: Chat command - forge sigil for Refugees & War Victims
        print_title("Test 3: Chat command 'forge sigil for Refugees & War Victims'")
        payload = {
            "messages": [{"role": "user", "content": "forge sigil for Refugees & War Victims"}],
            "provider": "auto",
        }
        status, res = post_json("/api/v1/llm/chat", payload)
        print(f"   Status: {status}")
        print(f"   Response:\n{res.get('response')}\n")
        print(f"   Tool calls executed: {len(res.get('tool_calls', []))}")
        for tc in res.get("tool_calls", []):
            print(f"     - Tool: {tc.get('tool_name')} | Status: {tc.get('status')} | Result: {tc.get('result')}")

        # Test 4: Chat command - cast geomancy
        print_title("Test 4: Chat command 'cast geomancy'")
        payload = {"messages": [{"role": "user", "content": "cast geomancy"}], "provider": "auto"}
        status, res = post_json("/api/v1/llm/chat", payload)
        print(f"   Status: {status}")
        print(f"   Response:\n{res.get('response')[:400]}...\n")
        print(f"   Tool calls executed: {len(res.get('tool_calls', []))}")
        for tc in res.get("tool_calls", []):
            print(f"     - Tool: {tc.get('tool_name')} | Status: {tc.get('status')}")

        # Test 5: Global Intention Narrative - world peace
        print_title("Test 5: Global Intention Narrative: 'world peace'")
        payload = {"intention": "world peace", "theme": "manifestation"}
        status, res = post_json("/api/v1/radionics/narrative/global-intention", payload)
        print(f"   Status: {status}")
        print("   Matched Radionics Data:")
        rd = res.get("radionics_data", {})
        print(f"     - Planet:     {rd.get('planetary_planets')} ({rd.get('planetary_frequency')} Hz)")
        print(f"     - Solfeggio:  {rd.get('solfeggio_name')}")
        print(f"     - Location:   {rd.get('location')}")
        print(f"     - Chakra:     {rd.get('chakra')}")
        print(f"     - Broadcast:  {rd.get('broadcast_recommendation')}")
        # Note: If LLM is not running, narrative endpoint raises 503 or error. Let's catch and gracefully log it.
        print(f"   Generated Narrative Preview: {res.get('narrative', 'N/A')[:200]}...")

        # Test 6: Global Intention Narrative - reforestation the world (Amazon)
        print_title("Test 6: Global Intention Narrative: 'reforestation the world'")
        payload = {"intention": "reforestation the world", "theme": "healing"}
        status, res = post_json("/api/v1/radionics/narrative/global-intention", payload)
        print(f"   Status: {status}")
        print("   Matched Radionics Data:")
        rd = res.get("radionics_data", {})
        print(f"     - Planet:     {rd.get('planetary_planets')} ({rd.get('planetary_frequency')} Hz)")
        print(f"     - Solfeggio:  {rd.get('solfeggio_name')}")
        print(f"     - Location:   {rd.get('location')}")
        print(f"     - Chakra:     {rd.get('chakra')}")
        print(f"     - Broadcast:  {rd.get('broadcast_recommendation')}")
        print(f"   Generated Narrative Preview: {res.get('narrative', 'N/A')[:200]}...")

    except Exception as e:
        print(f"\n❌ Test suite execution failed: {e}")
    finally:
        # 6. Shutdown temporary backend server
        print("\n6. Shutting down temporary backend server...")
        server_process.terminate()
        server_process.wait()
        print("   Server stopped.")

    print_title("LLM Tool Calling & Narrative Test Suite Complete")


if __name__ == "__main__":
    main()
