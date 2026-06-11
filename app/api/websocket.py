from fastapi import APIRouter, WebSocket

from app.realtime.handler import handle_voice_connection

router = APIRouter()


@router.websocket("/voice-chat/{token}")
async def voice_chat(websocket: WebSocket, token: str):
    await handle_voice_connection(websocket, token)

