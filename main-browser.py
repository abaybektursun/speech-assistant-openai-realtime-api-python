import os
import json
import base64
import asyncio
import websockets
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse

# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.websocket("/browser-stream")
async def handle_browser_stream(websocket: WebSocket):
    """Handle WebSocket connections directly from the browser."""
    logger.info("Browser client attempting to connect")
    await websocket.accept()
    logger.info("Browser client connected")

    try:
        async with websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            extra_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1"
            }
        ) as openai_ws:
            logger.info("Connected to OpenAI WebSocket")

            # Initialize session specifically for browser PCM16
            session_update = {
                "type": "session.update",
                "session": {
                    "turn_detection": {"type": "server_vad"},
                    "input_audio_format": "pcm16",  # Native browser format
                    "output_audio_format": "pcm16",  # Native browser format
                    "voice": "alloy",
                    "instructions": SYSTEM_MESSAGE,
                    "modalities": ["text", "audio"],
                    "temperature": 0.8,
                }
            }
            logger.debug(f"Sending session update: {json.dumps(session_update)}")
            await openai_ws.send(json.dumps(session_update))

            async def receive_from_browser():
                """Receive audio data from browser and forward to OpenAI."""
                try:
                    async for message in websocket.iter_text():
                        data = json.loads(message)
                        if data['event'] == 'media' and openai_ws.open:
                            logger.debug("Received browser audio chunk")
                            audio_append = {
                                "type": "input_audio_buffer.append",
                                "audio": data['media']['payload']
                            }
                            await openai_ws.send(json.dumps(audio_append))
                except Exception as e:
                    logger.error(f"Error in receive_from_browser: {str(e)}")
                    raise

            async def send_to_browser():
                """Receive from OpenAI and send to browser."""
                try:
                    async for message in openai_ws:
                        response = json.loads(message)
                        logger.debug(f"OpenAI event type: {response.get('type')}")
                        
                        if response.get('type') == 'response.audio.delta':
                            logger.debug("Sending audio chunk to browser")
                            await websocket.send_json({
                                "event": "media",
                                "media": {
                                    "payload": response.get('delta', '')
                                }
                            })
                except Exception as e:
                    logger.error(f"Error in send_to_browser: {str(e)}")
                    raise

            await asyncio.gather(receive_from_browser(), send_to_browser())

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        raise
    finally:
        logger.info("Browser client disconnected")

# Test endpoint
@app.get("/test-browser-stream")
async def test_browser_stream():
    """Test the browser stream endpoint configuration."""
    test_config = {
        "endpoint": "/browser-stream",
        "input_format": "pcm16",
        "output_format": "pcm16",
        "websocket_status": "configured"
    }
    logger.info(f"Test endpoint accessed: {json.dumps(test_config)}")
    return JSONResponse(content=test_config)