import sounddevice as sd
import websocket
import numpy as np
import queue
import threading
import time

WS_URL = "ws://localhost:8001/voice-chat/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6Im1hbmFzQGdtYWlsLmNvbSIsImV4cCI6MTc4MDU1Mzg3NSwiaWF0IjoxNzgwNTUyMDc1fQ.7MahwSSOmeDH2fUCGYdOsUBzrYYInqotu6Olt2FU8DM"

audio_queue = queue.Queue()

ws = websocket.WebSocket()
ws.connect(WS_URL)

print("Connected to server...")


# -----------------------------
# AUDIO CAPTURE (FAST ONLY)
# -----------------------------
def callback(indata, frames, time_info, status):

    if status:
        print("Audio status:", status)

    # ONLY PUSH TO QUEUE (NO NETWORK HERE)
    audio_queue.put(indata.tobytes())


# -----------------------------
# NETWORK SENDER (SLOW SAFE LAYER)
# -----------------------------
def sender():

    while True:

        try:
            data = audio_queue.get()

            if data is None:
                break

            ws.send(data)

        except Exception as e:
            print("Send error:", e)
            break


# start sender thread
threading.Thread(target=sender, daemon=True).start()


# -----------------------------
# MIC STREAM
# -----------------------------
samplerate = 16000
channels = 1

with sd.InputStream(
    samplerate=samplerate,
    channels=channels,
    dtype="int16",
    blocksize=800,   # ~100ms chunk (better realtime)
    callback=callback
):

    print("🎤 Streaming microphone... Ctrl+C to stop")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
        audio_queue.put(None)
        ws.close()