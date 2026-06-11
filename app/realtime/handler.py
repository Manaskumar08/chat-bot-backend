from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status

from app.models.auth import decode_access_token
from app.realtime.session import VoiceStreamSession


async def handle_voice_connection(websocket: WebSocket, token: str | None) -> None:
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")

    token_data = decode_access_token(token)
    if not token_data:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")

    await websocket.accept()

    session = VoiceStreamSession(websocket=websocket, user_id=token_data.user_id)
    await session.start()

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            await session.handle_message(message)
    except WebSocketDisconnect:
        pass
    finally:
        await session.stop()
