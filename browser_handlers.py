# browser_handlers.py
import os
import json
import base64
import asyncio
import websockets
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import audioop

class BrowserWebSocketManager:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = {
            'websocket': websocket,
            'openai_ws': None,
            'latest_timestamp': 0
        }

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            connection = self.active_connections[client_id]
            if connection['openai_ws'] and connection['openai_ws'].open:
                await connection['openai_ws'].close()
            del self.active_connections[client_id]

    async def initialize_openai_connection(self, client_id: str):
        """Initialize WebSocket connection to OpenAI for browser client."""
        connection = self.active_connections[client_id]
        
        openai_ws = await websockets.connect(
            'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
            extra_headers={
                "Authorization": f"Bearer {self.openai_api_key}",
                "OpenAI-Beta": "realtime=v1"
            }
        )
        
        connection['openai_ws'] = openai_ws
        
        # Initialize session with OpenAI
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": "alloy",
                "instructions": "You are a helpful AI assistant.",
                "modalities": ["text", "audio"],
                "temperature": 0.8,
            }
        }
        await openai_ws.send(json.dumps(session_update))

    async def handle_browser_audio(self, websocket: WebSocket, client_id: str):
        """Handle audio data from browser."""
        connection = self.active_connections[client_id]
        
        try:
            while True:
                message = await websocket.receive_json()
                
                if message['event'] == 'media':
                    # Convert WebM audio to PCM u-law
                    audio_data = base64.b64decode(message['media']['payload'])
                    pcm_data = self.convert_audio_to_ulaw(audio_data)
                    
                    # Send to OpenAI
                    if connection['openai_ws'] and connection['openai_ws'].open:
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(pcm_data).decode('utf-8')
                        }
                        await connection['openai_ws'].send(json.dumps(audio_append))
                        
                        connection['latest_timestamp'] = message['media']['timestamp']
        
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            print(f"Error in handle_browser_audio: {e}")
            await self.disconnect(client_id)

    async def handle_openai_messages(self, client_id: str):
        """Handle messages from OpenAI and send them to browser."""
        connection = self.active_connections[client_id]
        
        try:
            async for message in connection['openai_ws']:
                response = json.loads(message)
                websocket = connection['websocket']

                if response.get('type') == 'response.audio.delta' and 'delta' in response:
                    # Send audio back to browser
                    await websocket.send_json({
                        "event": "media",
                        "media": {
                            "payload": response['delta']
                        }
                    })
                
                elif response.get('type') == 'response.content.delta':
                    # Send transcribed text to browser
                    await websocket.send_json({
                        "event": "transcript",
                        "content": response.get('delta', {}).get('text', '')
                    })

        except Exception as e:
            print(f"Error in handle_openai_messages: {e}")
            await self.disconnect(client_id)

    @staticmethod
    def convert_audio_to_ulaw(webm_audio):
        """
        Convert WebM audio to PCM u-law.
        Note: This is a placeholder - you'll need to implement proper audio conversion
        using a library like pydub or similar.
        """
        # TODO: Implement proper audio conversion
        # For now, returning dummy u-law data
        return webm_audio

browser_manager = BrowserWebSocketManager()