from __future__ import annotations

import asyncio
import json
import traceback
from collections import deque

import numpy as np
import torch
from fastapi import WebSocket

from app.realtime import events
from app.services.stt import transcribe_from_array
from app.services.vad import StreamingVAD
from app.services.voice_pipeline import VoicePipeline


class VoiceStreamSession:
    def __init__(self, websocket: WebSocket, user_id: int | None = None):
        self.websocket = websocket
        self.user_id = user_id
        self.pipeline = VoicePipeline()
        self.send_lock = asyncio.Lock()
        self.prompt_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self.worker_task: asyncio.Task | None = None

        self.max_preroll_samples = 16000
        self.preroll = deque(maxlen=self.max_preroll_samples * 2)
        self.audio_buffer = bytearray()
        self.vad_buffer = np.array([], dtype=np.int16)
        self.speech_active = False

    async def start(self) -> None:
        await self.send_json_safe(events.session_started(self.user_id))
        self.worker_task = asyncio.create_task(self._prompt_worker())

    async def stop(self) -> None:
        try:
            await self.prompt_queue.put(None)
            await self.prompt_queue.join()
        except Exception:
            pass

        if self.worker_task is not None:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except Exception:
                pass

        try:
            await self.send_json_safe(events.session_ended())
        except Exception:
            pass

    async def send_json_safe(self, payload: dict) -> None:
        async with self.send_lock:
            await self.websocket.send_json(payload)

    async def send_bytes_safe(self, payload: bytes) -> None:
        async with self.send_lock:
            await self.websocket.send_bytes(payload)

    async def handle_message(self, message: dict) -> None:
        if "text" in message:
            await self._handle_text_message(message["text"])
            return

        if "bytes" in message:
            await self._handle_audio_bytes(message["bytes"])
            return

        await self.send_json_safe(events.error("Unsupported message type"))

    async def _prompt_worker(self) -> None:
        while True:
            prompt = await self.prompt_queue.get()
            try:
                if prompt is None:
                    return
                await self.pipeline.process_prompt(
                    prompt,
                    self.send_json_safe,
                    self.send_bytes_safe,
                )
            except Exception as exc:
                traceback.print_exc()
                try:
                    await self.send_json_safe(events.error(f"Server error: {exc}"))
                except Exception:
                    pass
            finally:
                self.prompt_queue.task_done()

    async def _enqueue_prompt(self, prompt: str) -> None:
        await self.prompt_queue.put(prompt)

    async def _handle_text_message(self, raw_text: str) -> None:
        try:
            data = json.loads(raw_text)
            prompt = data.get("prompt", raw_text)
        except Exception:
            prompt = raw_text

        if not prompt.strip():
            await self.send_json_safe(events.error("Empty prompt"))
            return

        await self._enqueue_prompt(prompt)

    async def _handle_audio_bytes(self, chunk: bytes) -> None:
        if self.speech_active:
            self.audio_buffer.extend(chunk)
        else:
            self.preroll.extend(chunk)

        audio_np_chunk = np.frombuffer(chunk, dtype=np.int16)
        self.vad_buffer = np.concatenate([self.vad_buffer, audio_np_chunk])

        while len(self.vad_buffer) >= 512:
            frame = self.vad_buffer[:512]
            self.vad_buffer = self.vad_buffer[512:]

            frame_float = frame.astype(np.float32) / 32768.0
            frame_tensor = torch.from_numpy(frame_float)
            speech_event = StreamingVAD().process(frame_tensor)

            if speech_event is None:
                continue

            if "start" in speech_event and not self.speech_active:
                self.speech_active = True
                self.audio_buffer = bytearray(self.preroll)
                self.preroll.clear()

            elif "end" in speech_event and self.speech_active:
                audio_np = np.frombuffer(bytes(self.audio_buffer), dtype=np.int16)
                self._reset_stream_state()

                if audio_np.size == 0:
                    continue

                try:
                    text = await asyncio.to_thread(transcribe_from_array, audio_np)
                except Exception as exc:
                    traceback.print_exc()
                    await self.send_json_safe(events.error(f"Transcription error: {exc}"))
                    continue

                if text.strip():
                    await self._enqueue_prompt(text)

    def _reset_stream_state(self) -> None:
        self.audio_buffer.clear()
        self.vad_buffer = np.array([], dtype=np.int16)
        self.preroll.clear()
        self.speech_active = False
        StreamingVAD().reset()

