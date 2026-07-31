"""End-to-end async chat test.

Simulates the frontend flow:
1. Connect WebSocket, get connection_id
2. POST /llm/chat/async with connection_id
3. Listen for WebSocket events (chat_started, chat_tool_start, chat_complete)
4. Report what happened
"""
from __future__ import annotations

import asyncio
import json
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import time

import httpx
import websockets

BASE = "http://localhost:8008"
WS_URL = "ws://127.0.0.1:8008/ws"


async def main() -> int:
    print("=" * 60)
    print("END-TO-END ASYNC CHAT TEST")
    print("=" * 60)

    # ── Step 1: Connect WebSocket ──────────────────────────────
    print("\n[1] Connecting WebSocket...")
    try:
        ws = await websockets.connect(WS_URL)
        # Wait for the connection_id message
        welcome = await asyncio.wait_for(ws.recv(), timeout=5.0)
        welcome_data = json.loads(welcome)
        print(f"    Welcome: type={welcome_data.get('type')}")
        # The connection_id is sent in a connection_status or on open
        conn_id = None
        if welcome_data.get("connection_id"):
            conn_id = welcome_data["connection_id"]
        else:
            # Try to receive connection_status
            try:
                msg2 = await asyncio.wait_for(ws.recv(), timeout=3.0)
                d2 = json.loads(msg2)
                print(f"    Second msg: type={d2.get('type')}")
                conn_id = d2.get("connection_id")
            except asyncio.TimeoutError:
                pass

        if not conn_id:
            print("    WARNING: No connection_id received yet, continuing...")
            conn_id = "unknown"
        else:
            print(f"    Connection ID: {conn_id}")
    except Exception as e:
        print(f"    FAIL: WebSocket connect failed: {e}")
        return 1

    # ── Step 2: Send async chat request ────────────────────────
    print("\n[2] Sending async chat request...")
    job_id = None
    async with httpx.AsyncClient(timeout=10.0) as client:
        body = {
            "messages": [{"role": "user", "content": "say hello"}],
            "connection_id": conn_id,
        }
        try:
            resp = await client.post(f"{BASE}/api/v1/llm/chat/async", json=body)
            print(f"    Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                job_id = data.get("job_id")
                print(f"    Job ID: {job_id}")
            else:
                print(f"    Body: {resp.text[:200]}")
        except Exception as e:
            print(f"    FAIL: {e}")
            await ws.close()
            return 1

    # ── Step 3: Listen for WebSocket events ────────────────────
    print("\n[3] Listening for WebSocket events (120s timeout)...")
    events = []
    start = time.time()
    try:
        while time.time() - start < 120:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(raw)
                msg_type = data.get("type", "?")
                events.append(data)
                # Print key events
                if msg_type in (
                    "chat_started",
                    "chat_tool_start",
                    "chat_tool_complete",
                    "chat_tool_error",
                    "chat_complete",
                    "chat_error",
                ):
                    extra = ""
                    if msg_type == "chat_tool_start":
                        extra = f" tool={data.get('tool')}"
                    elif msg_type == "chat_complete":
                        resp = str(data.get("response", ""))[:80]
                        extra = f" response='{resp}...'"
                    elif msg_type == "chat_error":
                        extra = f" error={data.get('error', '')[:80]}"
                    elif msg_type == "chat_tool_complete":
                        extra = f" tool={data.get('tool')}"
                    elapsed_t = time.time() - start
                    print(f"    [{elapsed_t:.1f}s] {msg_type}{extra}")
                # Stop on terminal events
                if msg_type in ("chat_complete", "chat_error"):
                    break
            except asyncio.TimeoutError:
                # No event in 2s, keep waiting
                continue
    except Exception as e:
        print(f"    ERROR: {e}")

    # ── Step 4: Report ─────────────────────────────────────────
    print("\n[4] RESULT")
    print(f"    Total events received: {len(events)}")
    terminal = [e for e in events if e.get("type") in ("chat_complete", "chat_error")]
    if terminal:
        t = terminal[0]
        print(f"    Terminal event: {t.get('type')}")
        if t.get("type") == "chat_complete":
            print(f"    Response: {str(t.get('response', ''))[:120]}")
            print("\n    *** SUCCESS: Async chat flow works! ***")
        else:
            print(f"    Error: {t.get('error', '')[:200]}")
            print("\n    *** FAILURE: Chat ended in error ***")
    else:
        print("    *** FAILURE: No terminal event (chat_complete/chat_error) received ***")
        print("    The background task likely never completed.")

    await ws.close()
    return 0 if terminal and terminal[0].get("type") == "chat_complete" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
