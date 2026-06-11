"""
Standalone WebRTC test client for the voice agent backend.

Usage examples:
  VAenv\\Scripts\\python.exe webrtc_test_client.py --token <JWT> --input sample.wav
  VAenv\\Scripts\\python.exe webrtc_test_client.py --token <JWT> --mic

This script:
  1. creates a WebRTC offer
  2. sends it to POST /api/webrtc/offer
  3. attaches either a WAV file track or live microphone track
  4. records the assistant audio response to a WAV file
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from fractions import Fraction
from typing import Optional

import av
import httpx
import numpy as np
import sounddevice as sd
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer, MediaRecorder

LOGGER = logging.getLogger("webrtc_test_client")
DEFAULT_URL = "http://127.0.0.1:8001/webrtc/offer"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_BLOCKSIZE = 512


class MicrophoneAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, samplerate: int = DEFAULT_SAMPLE_RATE, blocksize: int = DEFAULT_BLOCKSIZE) -> None:
        super().__init__()
        self.samplerate = samplerate
        self.blocksize = blocksize
        self._loop = asyncio.get_running_loop()
        self._queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=100)
        self._pts = 0
        self._time_base = Fraction(1, self.samplerate)
        self._chunks_captured = 0
        self._first_chunk_logged = False
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="int16",
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time_info, status) -> None:
        if status:
            LOGGER.warning("Microphone status: %s", status)

        data = bytes(indata)
        try:
            self._loop.call_soon_threadsafe(self._enqueue, data)
        except RuntimeError:
            pass

    def _enqueue(self, data: bytes) -> None:
        if not self._queue.full():
            self._queue.put_nowait(data)
            self._chunks_captured += 1
            if not self._first_chunk_logged:
                LOGGER.info("Microphone audio is flowing into the WebRTC track")
                self._first_chunk_logged = True
            elif self._chunks_captured % 50 == 0:
                LOGGER.info("Captured %d microphone chunks", self._chunks_captured)

    async def recv(self):
        data = await self._queue.get()
        if data is None:
            raise asyncio.CancelledError

        samples = np.frombuffer(data, dtype=np.int16)
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = self.samplerate
        frame.time_base = self._time_base
        frame.pts = self._pts
        self._pts += frame.samples
        return frame

    def stop(self) -> None:
        try:
            self._stream.stop()
        finally:
            self._stream.close()
            try:
                self._queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


class AssistantAudioMonitor(MediaStreamTrack):
    kind = "audio"

    def __init__(self, track: MediaStreamTrack, output: str) -> None:
        super().__init__()
        self._track = track
        self._output = output
        self._seen_non_silence = False
        self._frames_seen = 0

    async def recv(self):
        frame = await self._track.recv()
        self._frames_seen += 1

        samples = frame.to_ndarray()
        peak = int(np.max(np.abs(samples))) if samples.size else 0
        if peak > 0 and not self._seen_non_silence:
            self._seen_non_silence = True
            LOGGER.info("Assistant audio became audible (peak=%d). Recording to %s", peak, self._output)
        elif self._frames_seen % 50 == 0:
            LOGGER.info("Assistant audio frames received: %d (peak=%d)", self._frames_seen, peak)

        return frame


async def post_offer(url: str, token: str, sdp: str) -> dict:
    payload = {"token": token, "sdp": sdp, "type": "offer"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload)
        if response.is_error:
            raise RuntimeError(
                f"Offer request failed: status={response.status_code}, body={response.text}"
            )
        return response.json()


async def wait_for_ice_gathering_complete(pc: RTCPeerConnection, timeout: float = 10.0) -> None:
    if pc.iceGatheringState == "complete":
        return

    loop = asyncio.get_running_loop()
    future = loop.create_future()

    @pc.on("icegatheringstatechange")
    def on_icegatheringstatechange() -> None:
        if pc.iceGatheringState == "complete" and not future.done():
            future.set_result(None)

    try:
        await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        LOGGER.warning("Timed out waiting for ICE gathering to complete; continuing anyway")


async def run(args: argparse.Namespace) -> None:
    pc = RTCPeerConnection()
    recorder = MediaRecorder(args.output)
    recorder_started = asyncio.Event()
    assistant_received = asyncio.Event()
    input_track: Optional[MediaStreamTrack] = None

    if args.mic:
        input_track = MicrophoneAudioTrack()
        pc.addTrack(input_track)
        LOGGER.info(
            "Microphone input started at %d Hz, blocksize=%d",
            DEFAULT_SAMPLE_RATE,
            DEFAULT_BLOCKSIZE,
        )
    else:
        player = MediaPlayer(str(args.input))
        if player.audio is None:
            raise RuntimeError(f"No audio track found in input file: {args.input}")
        input_track = player.audio
        pc.addTrack(input_track)
        LOGGER.info("File input attached: %s", args.input)

    async def start_recorder() -> None:
        if recorder_started.is_set():
            return
        await recorder.start()
        recorder_started.set()

    @pc.on("track")
    def on_track(track):
        if track.kind != "audio":
            return
        monitored_track = AssistantAudioMonitor(track, args.output)
        recorder.addTrack(monitored_track)
        asyncio.create_task(start_recorder())
        assistant_received.set()
        LOGGER.info("Assistant audio track received; recording to %s", args.output)

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await wait_for_ice_gathering_complete(pc)

    answer_data = await post_offer(args.url, args.token, pc.localDescription.sdp)
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=answer_data["sdp"], type=answer_data.get("type", "answer"))
    )

    LOGGER.info("Connected. session_id=%s", answer_data.get("session_id"))
    LOGGER.info("Speak now%s", "" if args.mic else f" using {args.input}")
    LOGGER.info("If you see 'Microphone audio is flowing', the backend is receiving your voice.")
    LOGGER.info("If the assistant responds, audio will be written to %s", args.output)

    try:
        if not assistant_received.is_set():
            LOGGER.info("Waiting for assistant audio to arrive...")
        await asyncio.sleep(args.wait)
    finally:
        if recorder_started.is_set():
            await recorder.stop()
        await pc.close()
        if args.mic and isinstance(input_track, MicrophoneAudioTrack):
            input_track.stop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WebRTC test client for the voice agent backend")
    parser.add_argument("--token", required=True, help="JWT token for /api/webrtc/offer")
    parser.add_argument("--url", default=DEFAULT_URL, help="WebRTC offer endpoint URL")
    parser.add_argument("--output", default="webrtc_response.wav", help="Where to save the assistant audio response")
    parser.add_argument("--wait", type=float, default=25.0, help="How long to keep the session open after connecting")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", type=Path, help="Path to a WAV/MP4/etc. file to send as input")
    mode.add_argument("--mic", action="store_true", help="Use the live microphone as input")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
