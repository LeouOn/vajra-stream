import json
import sys
import urllib.request

# Configure stdout/stderr for Unicode encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def test_chat():
    url = "http://localhost:8008/api/v1/llm/chat"
    payload = {
        "messages": [{"role": "user", "content": "Tell me about the current planetary energies and active aspects."}],
        "provider": "local",  # fallback or local
        "include_astrology": True,
        "debug_mode": True,
    }

    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print("Chat Response received!")
            print("Provider selected:", res_data.get("debug_info", {}).get("provider_selected"))

            system_prompt = res_data.get("debug_info", {}).get("system_prompt", "")
            print("\n--- SYSTEM PROMPT FROM DEBUG INFO ---")
            print(system_prompt)
            print("-------------------------------------")

            # Assertions
            assert "COSMIC CLOCKWORK SYSTEM" in system_prompt
            assert "Western Tropical Astrology" in system_prompt
            assert "Indian Vedic Astrology" in system_prompt
            assert "Chinese Lunisolar Astrology" in system_prompt
            assert "Wu Xing" in system_prompt
            print(
                "\nSUCCESS: The full Cosmic Clockwork system data is successfully present in the injected prompt context!"
            )
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, "read"):
            print("Error details:", e.read().decode("utf-8"))
        sys.exit(1)


if __name__ == "__main__":
    test_chat()
