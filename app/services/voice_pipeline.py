"""
Orchestration layer for prompt processing.

This keeps the websocket handler thin by centralizing prompt -> LLM -> TTS
behavior in one place.
"""

from __future__ import annotations
from app.services.audio_player import play_audio

import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional

from app.realtime import events
from app.services.llm import ask_llm
from app.services.tts import text_to_speech


def _next_item(stream):
    try:
        return next(stream)
    except StopIteration:
        return None


def _render_messages(messages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for message in messages:
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

    return "\n".join(lines)


class VoicePipeline:
    async def process_prompt(
        self,
        prompt: str,
        send_json: Optional[Callable[[dict], Awaitable[None]]] = None,
        send_bytes: Optional[Callable[[bytes], Awaitable[None]]] = None,
        audio_sink: Optional[Callable[[str], Awaitable[None]]] = None,
        messages: Optional[list[dict[str, str]]] = None,
    ) -> str:
        if send_json is not None:
            await send_json(events.transcript(prompt))

        full_response = ""
        llm_prompt = _render_messages(messages) if messages else prompt
        stream = ask_llm(llm_prompt)
        while True:
            token = await asyncio.to_thread(_next_item, stream)
            if token is None:
                break
            full_response += token
            if send_json is not None:
                await send_json(events.llm_token(token))

        if send_json is not None:
            await send_json(events.assistant_text(full_response))

        speech_file = await asyncio.to_thread(text_to_speech, full_response)
        try:
            if send_json is not None:
                await send_json(events.audio_ready(Path(speech_file).name))

            # Automatically play audio locally
            await asyncio.to_thread(play_audio, speech_file)

            # if audio_sink is not None:
            #     await audio_sink(speech_file)
            # elif send_bytes is not None:
            #     audio_bytes = await asyncio.to_thread(Path(speech_file).read_bytes)
            #     await send_bytes(audio_bytes)
        finally:
            pass
            # Path(speech_file).unlink(missing_ok=True)

        return full_response
