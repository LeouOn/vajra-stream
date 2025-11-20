import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8003/ws"
    print(f"Testing WebSocket connection to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully!")
            
            # Wait for initial message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received message: {message}")
                data = json.loads(message)
                print(f"Parsed data: {data}")
            except asyncio.TimeoutError:
                print("No message received within 5 seconds")
            
            # Send a ping message
            ping_msg = json.dumps({"type": "ping"})
            await websocket.send(ping_msg)
            print("Sent ping message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received response: {response}")
            except asyncio.TimeoutError:
                print("No response to ping within 5 seconds")
                
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_websocket())