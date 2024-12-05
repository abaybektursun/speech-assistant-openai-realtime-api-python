import asyncio
import websockets
import json
import requests

async def test_audio_stream():
    print("🧪 Starting WebSocket test")
    
    # Get test audio data from HTTP endpoint
    response = requests.get("http://localhost/test-audio-data")
    if response.status_code != 200:
        print(f"❌ Failed to get test audio data: {response.status_code}")
        return
        
    test_data = response.json()
    print(f"📦 Got test audio data: {len(test_data['audio'])} bytes")
    
    # Connect to browser stream
    async with websockets.connect('ws://localhost/browser-stream') as ws:
        print("🔌 Connected to WebSocket")
        
        # Send test audio
        await ws.send(json.dumps(test_data))
        print("📤 Sent test audio")
        
        # Wait for response
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            print(f"📥 Received response: {response[:100]}...")
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for response")
        
        print("✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_audio_stream())