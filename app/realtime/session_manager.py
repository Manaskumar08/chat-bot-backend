"""
In-memory voice session manager.

This keeps ChatGPT-style conversation state for each voice session while
preserving backward compatibility with the existing transport and services.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful, concise voice assistant. "
    "Keep responses natural, clear, and spoken-word friendly."
)


@dataclass(slots=True)
class VoiceSession:
    session_id: str
    user_id: Optional[int] = None
    messages: list[dict[str, str]] = field(
        default_factory=lambda: [{"role": "system", "content": SYSTEM_PROMPT}]
    )
    last_activity: datetime = field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        self.last_activity = datetime.utcnow()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return datetime.utcnow() - self.last_activity > timedelta(minutes=timeout_minutes)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self.touch()

    def add_user_message(self, content: str) -> None:
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        self.add_message("assistant", content)

    def build_prompt(self) -> str:
        lines: list[str] = []
        for message in self.messages:
            role = message.get("role", "").strip().lower()
            content = message.get("content", "").strip()
            if not content:
                continue
            if role == "system":
                lines.append(f"System: {content}")
            elif role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content}")
            else:
                lines.append(f"{role.title()}: {content}")

        return "\n".join(lines) if lines else SYSTEM_PROMPT


class VoiceSessionManager:
    def __init__(self, timeout_minutes: int = 30, cleanup_interval_seconds: int = 60) -> None:
        self.timeout_minutes = timeout_minutes
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self._sessions: dict[str, VoiceSession] = {}
        self._cleanup_task: asyncio.Task | None = None

    def get_or_create(self, session_id: str, user_id: Optional[int] = None) -> VoiceSession:
        session = self._sessions.get(session_id)
        if session is None or session.is_expired(self.timeout_minutes):
            if session is not None:
                logger.info("Expiring voice session session_id=%s", session_id)
            session = VoiceSession(session_id=session_id, user_id=user_id)
            self._sessions[session_id] = session
        elif user_id is not None and session.user_id is None:
            session.user_id = user_id

        session.touch()
        return session

    def get(self, session_id: str) -> VoiceSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.is_expired(self.timeout_minutes):
            self._sessions.pop(session_id, None)
            return None
        return session

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def prune_expired(self) -> None:
        expired_ids = [
            session_id
            for session_id, session in self._sessions.items()
            if session.is_expired(self.timeout_minutes)
        ]
        for session_id in expired_ids:
            self._sessions.pop(session_id, None)

        if expired_ids:
            logger.info("Pruned %d expired voice sessions", len(expired_ids))

    async def start_cleanup_loop(self) -> None:
        if self._cleanup_task is not None and not self._cleanup_task.done():
            return

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup_loop(self) -> None:
        if self._cleanup_task is None:
            return

        self._cleanup_task.cancel()
        try:
            await self._cleanup_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval_seconds)
                self.prune_expired()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Voice session cleanup loop crashed")


voice_session_manager = VoiceSessionManager()
