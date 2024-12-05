import asyncio
import websockets
import json

async def test_browser_stream():
    """Test the browser stream WebSocket endpoint."""
    uri = "ws://localhost:8000/browser-stream"
    async with websockets.connect(uri) as websocket:
        # Send a test audio chunk
        test_data = {
            "event": "media",
            "media": {
                "payload": "AAAA"  # Minimal PCM16 test data
            }
        }
        await websocket.send(json.dumps(test_data))
        
        # Wait for response
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"Received response: {response}")
            return True
        except asyncio.TimeoutError:
            print("No response received within timeout")
            return False

if __name__ == "__main__":
    asyncio.run(test_browser_stream())