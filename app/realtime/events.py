"""Helpers for producing websocket event payloads."""

from app.schemas.websocket import (
    AssistantTextEvent,
    AudioReadyEvent,
    ErrorEvent,
    LlmTokenEvent,
    SessionEndedEvent,
    SessionStartedEvent,
    TranscriptEvent,
)


def session_started(user_id: int | None = None) -> dict:
    return SessionStartedEvent(user_id=user_id).model_dump()


def session_ended() -> dict:
    return SessionEndedEvent().model_dump()


def transcript(text: str) -> dict:
    return TranscriptEvent(text=text).model_dump()


def llm_token(token: str) -> dict:
    return LlmTokenEvent(token=token).model_dump()


def assistant_text(text: str) -> dict:
    return AssistantTextEvent(text=text).model_dump()


def audio_ready(filename: str) -> dict:
    return AudioReadyEvent(filename=filename).model_dump()


def error(message: str) -> dict:
    return ErrorEvent(message=message).model_dump()

