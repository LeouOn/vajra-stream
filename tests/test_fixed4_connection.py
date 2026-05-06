import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8006/ws"
    print(f"Testing direct WebSocket connection to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully!")
            
            # Wait for initial message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received message: {message}")
            except asyncio.TimeoutError:
                print("No message received within 5 seconds")
            
            # Send a test message
            test_msg = "Hello from test client!"
            await websocket.send(test_msg)
            print(f"Sent message: {test_msg}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received response: {response}")
            except asyncio.TimeoutError:
                print("No response to test message within 5 seconds")
                
    except Exception as e:
        print(f"WebSocket connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_websocket())