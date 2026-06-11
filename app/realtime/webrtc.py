"""
WebRTC transport primitives for the voice agent.

This module only handles media transport and peer lifecycle. It does not own
the STT / LLM / TTS business logic; those hooks will be connected in the next
migration step.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction
from typing import Callable, Optional

import av
import numpy as np
import torch
from av.audio.resampler import AudioResampler

try:
    from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
except ImportError:  # pragma: no cover - dependency may be installed later
    MediaStreamTrack = object  # type: ignore[assignment]
    RTCPeerConnection = None  # type: ignore[assignment]
    RTCSessionDescription = None  # type: ignore[assignment]

from app.services.audio_player import stop_audio
from app.services.stt import transcribe_from_array
from app.services.vad import StreamingVAD
from app.services.voice_pipeline import VoicePipeline
from app.realtime.session_manager import VoiceSession, voice_session_manager

logger = logging.getLogger(__name__)


SILENCE_SAMPLE_RATE = 48000
SILENCE_FRAME_SAMPLES = 960  # 20 ms at 48 kHz
SILENCE_LAYOUT = "mono"
SILENCE_FORMAT = "s16"
STT_SAMPLE_RATE = 16000
VAD_FRAME_SIZE = 512
PREROLL_SECONDS = 1


def aiortc_available() -> bool:
    return RTCPeerConnection is not None and RTCSessionDescription is not None


class QueuedAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[Optional[av.AudioFrame]] = asyncio.Queue(maxsize=500)
        self._pts = 0

    async def recv(self):
        try:
            frame = await asyncio.wait_for(self._queue.get(), timeout=0.02)
        except asyncio.TimeoutError:
            frame = None

        if frame is None:
            await asyncio.sleep(SILENCE_FRAME_SAMPLES / SILENCE_SAMPLE_RATE)
            return self._silence_frame()

        return frame

    async def enqueue_audio_file(self, file_path: str) -> None:
        frames = await asyncio.to_thread(self._decode_audio_file, file_path)
        for frame in frames:
            await self._queue.put(frame)

    def clear(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def _decode_audio_file(self, file_path: str) -> list[av.AudioFrame]:
        container = av.open(file_path)
        resampler = AudioResampler(
            format=SILENCE_FORMAT,
            layout=SILENCE_LAYOUT,
            rate=SILENCE_SAMPLE_RATE,
        )
        frames: list[av.AudioFrame] = []
        try:
            for packet in container.demux(audio=0):
                for frame in packet.decode():
                    resampled_frames = resampler.resample(frame)
                    if not isinstance(resampled_frames, list):
                        resampled_frames = [resampled_frames]
                    for resampled in resampled_frames:
                        if resampled is None:
                            continue
                        resampled.sample_rate = SILENCE_SAMPLE_RATE
                        resampled.pts = self._pts
                        resampled.time_base = Fraction(1, SILENCE_SAMPLE_RATE)
                        self._pts += resampled.samples
                        frames.append(resampled)
        finally:
            container.close()

        return frames

    def _silence_frame(self) -> av.AudioFrame:
        frame = av.AudioFrame(format=SILENCE_FORMAT, layout=SILENCE_LAYOUT, samples=SILENCE_FRAME_SAMPLES)
        for plane in frame.planes:
            plane.update(b"\x00" * plane.buffer_size)
        frame.sample_rate = SILENCE_SAMPLE_RATE
        frame.pts = self._pts
        frame.time_base = Fraction(1, SILENCE_SAMPLE_RATE)
        self._pts += SILENCE_FRAME_SAMPLES
        return frame


@dataclass(slots=True)
class WebRTCVoiceTransport:
    token: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[int] = field(default=None, init=False, repr=False)
    peer_connection: Optional["RTCPeerConnection"] = None
    inbound_frames: asyncio.Queue[av.AudioFrame | None] = field(
        default_factory=lambda: asyncio.Queue(maxsize=200)
    )
    outbound_track: Optional[QueuedAudioTrack] = None
    transcript_callback: Optional[Callable[[str], object]] = None
    last_transcript: str = ""
    pipeline: VoicePipeline = field(default_factory=VoicePipeline)
    _track_tasks: set[asyncio.Task] = field(default_factory=set, init=False, repr=False)
    _audio_task: Optional[asyncio.Task] = field(default=None, init=False, repr=False)
    _response_task: Optional[asyncio.Task] = field(default=None, init=False, repr=False)
    voice_session: Optional[VoiceSession] = field(default=None, init=False, repr=False)
    vad: StreamingVAD = field(init=False, repr=False)

    def __post_init__(self) -> None:
        token_data = self._decode_token(self.token)
        if not token_data:
            raise ValueError("Invalid or expired token")

        if not aiortc_available():
            raise RuntimeError("aiortc is not installed")

        self.user_id = token_data.user_id
        self.voice_session = voice_session_manager.get_or_create(self.session_id, user_id=self.user_id)
        self.peer_connection = RTCPeerConnection()
        self.outbound_track = QueuedAudioTrack()
        self.peer_connection.addTrack(self.outbound_track)
        self.transcript_callback = self._handle_transcript
        self._register_events()
        self._audio_task = asyncio.create_task(self._process_inbound_audio())
        self.vad = StreamingVAD()


    def _decode_token(self, token: str):
        from app.models.auth import decode_access_token

        return decode_access_token(token)

    def _register_events(self) -> None:
        assert self.peer_connection is not None
        pc = self.peer_connection

        @pc.on("track")
        def on_track(track):
            if track.kind != "audio":
                logger.info("Ignoring non-audio track kind=%s for session=%s", track.kind, self.session_id)
                return

            logger.info("Audio track received for session=%s", self.session_id)
            task = asyncio.create_task(self._consume_audio_track(track))
            self._track_tasks.add(task)
            task.add_done_callback(self._track_tasks.discard)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(
                "Peer connection state=%s session=%s",
                pc.connectionState,
                self.session_id,
            )
            if pc.connectionState in {"failed", "closed", "disconnected"}:
                await self.close()

    async def _consume_audio_track(self, track) -> None:
        while True:
            try:
                frame = await track.recv()
            except Exception as exc:
                logger.info("Audio track ended for session=%s: %s", self.session_id, exc)
                break

            self.last_activity = datetime.utcnow()
            try:
                self.inbound_frames.put_nowait(frame)
            except asyncio.QueueFull:
                logger.warning("Inbound frame queue full for session=%s", self.session_id)

    async def _process_inbound_audio(self) -> None:
        resampler = AudioResampler(
            format=SILENCE_FORMAT,
            layout=SILENCE_LAYOUT,
            rate=STT_SAMPLE_RATE,
        )
        preroll = bytearray()
        audio_buffer = bytearray()
        vad_buffer = np.array([], dtype=np.int16)
        speech_active = False

        while True:
            frame = await self.inbound_frames.get()
            if frame is None:
                return

            try:
                for resampled in resampler.resample(frame):
                    chunk = resampled.to_ndarray()
                    audio_np_chunk = np.asarray(chunk, dtype=np.int16).reshape(-1)
                    if audio_np_chunk.size == 0:
                        continue

                    self.last_activity = datetime.utcnow()
                    if self.voice_session is not None:
                        self.voice_session.touch()

                    if speech_active:
                        audio_buffer.extend(audio_np_chunk.tobytes())
                    else:
                        preroll.extend(audio_np_chunk.tobytes())
                        max_preroll_bytes = STT_SAMPLE_RATE * PREROLL_SECONDS * 2
                        if len(preroll) > max_preroll_bytes:
                            del preroll[: len(preroll) - max_preroll_bytes]

                    vad_buffer = np.concatenate([vad_buffer, audio_np_chunk])

                    while len(vad_buffer) >= VAD_FRAME_SIZE:
                        frame_chunk = vad_buffer[:VAD_FRAME_SIZE]
                        vad_buffer = vad_buffer[VAD_FRAME_SIZE:]
                        
                        speech_event = self.vad.process(frame_chunk.tobytes())
                        if speech_event is None:
                            continue

                        if "start" in speech_event and not speech_active:
                            self._cancel_current_response()
                            speech_active = True
                            audio_buffer = bytearray(preroll)
                            preroll.clear()

                        elif "end" in speech_event and speech_active:
                            audio_np = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
                            print(f"VAD detected end of speech for session={self.session_id}, processing {audio_np.size} samples")

                            speech_active = False
                            audio_buffer.clear()
                            preroll.clear()
                            vad_buffer = np.array([], dtype=np.int16)
                            self.vad.reset()

                            if audio_np.size == 0:
                                continue

                            try:
                                text = await asyncio.to_thread(transcribe_from_array, audio_np)
                            except Exception as exc:
                                logger.exception("Transcription error for session=%s", self.session_id)
                                await self._emit_transcript_event(f"Transcription error: {exc}")
                                continue

                            if text.strip():
                                self.last_transcript = text.strip()
                                if self.voice_session is not None:
                                    self.voice_session.touch()
                                logger.info(
                                    "Transcribed audio for session=%s user_id=%s text=%s",
                                    self.session_id,
                                    self.user_id,
                                    self.last_transcript,
                                )
                                await self._emit_transcript_event(self.last_transcript)
            except Exception:
                logger.exception("Audio processing failed for session=%s", self.session_id)

    async def _emit_transcript_event(self, text: str) -> None:
        if self.transcript_callback is not None:
            result = self.transcript_callback(text)
            if inspect.isawaitable(result):
                await result
            return

        logger.info("Transcript event session=%s text=%s", self.session_id, text)

    async def _handle_transcript(self, text: str) -> None:
        session = voice_session_manager.get_or_create(self.session_id, user_id=self.user_id)
        session.add_user_message(text)
        self.voice_session = session
        self._cancel_current_response()
        self._response_task = asyncio.create_task(self._generate_response_audio(text, session))

    async def _generate_response_audio(self, prompt: str, session) -> None:
        try:
            if self.outbound_track is None:
                return

            full_response = await self.pipeline.process_prompt(
                prompt,
                audio_sink=self.outbound_track.enqueue_audio_file,
                messages=session.messages,
            )
            session.add_assistant_message(full_response)
        except asyncio.CancelledError:
            logger.info("Response generation cancelled for session=%s", self.session_id)
            raise
        except Exception:
            logger.exception("Failed to generate response audio for session=%s", self.session_id)

    def _cancel_current_response(self) -> Optional[asyncio.Task]:

        # stop local speaker immediately
        stop_audio()

        task = self._response_task

        if task is not None and not task.done():
            task.cancel()

        self._response_task = None

        if self.outbound_track is not None:
            self.outbound_track.clear()

        return task

    async def _interrupt_current_response(self) -> None:
        task = self._cancel_current_response()
        if task is not None and not task.done():
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

    async def create_answer(self, offer_sdp: str) -> str:
        if not aiortc_available():
            raise RuntimeError("aiortc is not installed")

        assert self.peer_connection is not None

        await self.peer_connection.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)
        await self._wait_for_ice_gathering_complete()
        return self.peer_connection.localDescription.sdp

    async def _wait_for_ice_gathering_complete(self) -> None:
        assert self.peer_connection is not None
        if self.peer_connection.iceGatheringState == "complete":
            return

        ice_complete = asyncio.get_running_loop().create_future()

        @self.peer_connection.on("icegatheringstatechange")
        def on_icegatheringstatechange():
            if self.peer_connection is not None and self.peer_connection.iceGatheringState == "complete":
                if not ice_complete.done():
                    ice_complete.set_result(None)

        await ice_complete

    async def close(self) -> None:
        await self._interrupt_current_response()

        if self._audio_task is not None:
            try:
                self.inbound_frames.put_nowait(None)
            except asyncio.QueueFull:
                pass
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._audio_task = None

        for task in list(self._track_tasks):
            task.cancel()

        if self._track_tasks:
            await asyncio.gather(*self._track_tasks, return_exceptions=True)
            self._track_tasks.clear()

        if self.peer_connection is not None:
            await self.peer_connection.close()
            self.peer_connection = None

        if self.voice_session is not None:
            self.voice_session.touch()


class WebRTCSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, WebRTCVoiceTransport] = {}

    def register(self, session: WebRTCVoiceTransport) -> None:
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> WebRTCVoiceTransport | None:
        return self._sessions.get(session_id)

    def discard(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_registry = WebRTCSessionRegistry()
