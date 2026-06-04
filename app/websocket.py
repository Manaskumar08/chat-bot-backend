import os
import json
import time
import traceback
import asyncio
import numpy as np

from fastapi import WebSocket, WebSocketDisconnect

from app.services.stt import transcribe_from_array
from app.services.llm import ask_llm
from app.services.tts import text_to_speech
from app.services.vad import is_speech


# ----------------------------
# PROCESS PROMPT (LLM + TTS)
# ----------------------------
async def process_prompt(websocket: WebSocket, prompt: str):

    total_start = time.perf_counter()

    await websocket.send_json({
        "type": "transcript",
        "text": prompt
    })

    # -------- LLM --------
    llm_start = time.perf_counter()

    full_response = ""

    for token in ask_llm(prompt):

        full_response += token

        await websocket.send_json({
            "type": "llm_token",
            "token": token
        })

    llm_end = time.perf_counter()
    print(f"LLM Latency: {llm_end - llm_start:.2f}s")

    # -------- TTS --------
    tts_start = time.perf_counter()

    speech_file = text_to_speech(full_response)

    tts_end = time.perf_counter()
    print(f"TTS Latency: {tts_end - tts_start:.2f}s")

    # -------- SEND AUDIO --------
    send_start = time.perf_counter()

    with open(speech_file, "rb") as f:
        await websocket.send_bytes(f.read())

    send_end = time.perf_counter()
    print(f"Audio Send Time: {send_end - send_start:.2f}s")

    print(f"TOTAL: {time.perf_counter() - total_start:.2f}s")


# ----------------------------
# VOICE HANDLER (STREAMING STT)
# ----------------------------
async def handle_voice(websocket: WebSocket):

    await websocket.accept()

    audio_buffer = bytearray()
    last_voice_time = time.time()

    try:

        while True:

            message = await websocket.receive()

            # ---------------- DISCONNECT ----------------
            if message["type"] == "websocket.disconnect":
                print("Client disconnected")
                break

            # =====================================================
            # TEXT INPUT
            # =====================================================
            if "text" in message:

                raw_text = message["text"]
                print("Received Text:", raw_text)

                try:
                    data = json.loads(raw_text)
                    prompt = data.get("prompt", raw_text)
                except Exception:
                    prompt = raw_text

                if not prompt.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty prompt"
                    })
                    continue

                await process_prompt(websocket, prompt)
                continue

            # =====================================================
            # AUDIO STREAMING INPUT
            # =====================================================
            if "bytes" in message:

                chunk = message["bytes"]

                audio_buffer.extend(chunk)

                # VAD check (update voice activity)
                try:
                    if is_speech(chunk):
                        last_voice_time = time.time()
                except Exception:
                    pass

                # -----------------------------
                # silence detection (800ms)
                # -----------------------------
                if time.time() - last_voice_time > 0.8:

                    if len(audio_buffer) > 0:

                        print("🟢 Speech segment detected")

                        audio_np = np.frombuffer(audio_buffer, dtype=np.int16)

                        audio_buffer.clear()

                        text = await asyncio.to_thread(
                            transcribe_from_array,
                            audio_np
                        )

                        print("Transcript:", text)

                        if text.strip():
                            await process_prompt(websocket, text)

                continue

            # =====================================================
            # UNKNOWN MESSAGE
            # =====================================================
            await websocket.send_json({
                "type": "error",
                "message": "Unsupported message type"
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")

    except Exception:
        traceback.print_exc()