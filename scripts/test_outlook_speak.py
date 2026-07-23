import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402

client = TestClient(app)

r = client.post(
    "/api/v1/outlook/speak",
    json={
        "text": "May all beings be happy and free from suffering.",
        "role": "outlook_narrative",
    },
)
print(f"Status: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type', '?')}")
print(f"X-TTS-Backend: {r.headers.get('x-tts-backend', '?')}")
print(f"Audio size: {len(r.content)} bytes")
if len(r.content) == 0:
    print("EMPTY AUDIO - nothing to play")
elif len(r.content) < 100:
    print(f"Content: {r.content[:100]}")
else:
    print("Audio data present - saves to generated/tts_samples/outlook_test.wav")
    with open("generated/tts_samples/outlook_test.wav", "wb") as f:
        f.write(r.content)
