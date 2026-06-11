"""
WebSocket event schemas.

These keep the realtime protocol explicit and easy to evolve without coupling
the websocket transport to raw dictionaries.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class WebSocketEvent(BaseModel):
    type: str


class SessionStartedEvent(WebSocketEvent):
    type: Literal["session_started"] = "session_started"
    user_id: Optional[int] = None


class SessionEndedEvent(WebSocketEvent):
    type: Literal["session_ended"] = "session_ended"


class TranscriptEvent(WebSocketEvent):
    type: Literal["transcript"] = "transcript"
    text: str = Field(..., min_length=1)


class LlmTokenEvent(WebSocketEvent):
    type: Literal["llm_token"] = "llm_token"
    token: str = Field(..., min_length=1)


class AssistantTextEvent(WebSocketEvent):
    type: Literal["assistant_text"] = "assistant_text"
    text: str = Field(..., min_length=1)


class AudioReadyEvent(WebSocketEvent):
    type: Literal["audio_ready"] = "audio_ready"
    filename: str = Field(..., min_length=1)


class ErrorEvent(WebSocketEvent):
    type: Literal["error"] = "error"
    message: str = Field(..., min_length=1)

