import asyncio
import aiohttp
import sys
import json

async def test_connection(url="http://localhost:8001"):
    print(f"Testing connection to {url}...")
    
    # Test HTTP
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health") as response:
                print(f"HTTP GET /health status: {response.status}")
                text = await response.text()
                print(f"HTTP GET /health response: {text}")
    except Exception as e:
        print(f"HTTP connection failed: {e}")

    # Test WebSocket
    ws_url = url.replace("http", "ws") + "/ws"
    print(f"Testing WebSocket connection to {ws_url}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                print("WebSocket connected!")
                
                # Wait for a message
                try:
                    msg = await ws.receive(timeout=5.0)
                    print(f"Received message: {msg.type} - {msg.data}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for message")
                
                await ws.close()
                print("WebSocket closed")
    except Exception as e:
        print(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    url = "http://localhost:8001"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    asyncio.run(test_connection(url))