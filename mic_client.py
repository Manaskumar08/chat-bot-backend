import sounddevice as sd
import websocket
from websocket import ABNF
import numpy as np
import queue
import threading
import time

WS_URL = "ws://localhost:8001/voice-chat/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6Im1hbmFzQGdtYWlsLmNvbSIsImV4cCI6MTc4MTAwNTU2OSwiaWF0IjoxNzgxMDAzNzY5fQ.bbOOFRMRk-UQgoaSzC6PGT04JA2We-rs3KaRBqp2Rk0"

# -----------------------------
# CONFIG (VOICE AGENT v2)
# -----------------------------
SAMPLE_RATE = 16000
BLOCKSIZE = 512   # ⚡ MUST match Silero VAD requirement
CHANNELS = 1

frame_buffer = np.array([], dtype=np.int16)
TARGET = 512

# queue with backpressure control
audio_queue = queue.Queue(maxsize=50)

# -----------------------------
# WEBSOCKET CONNECT
# -----------------------------
ws = websocket.WebSocket()
ws.connect(WS_URL, timeout=10)
ws.settimeout(None)

print("Connected to server...")
print("WebSocket open:", ws.connected)


# -----------------------------
# AUDIO CAPTURE CALLBACK
# -----------------------------
def callback(indata, frames, time_info, status):
    if status:
        print("Audio status:", status)

    global frame_buffer

    chunk = np.frombuffer(indata.tobytes(), dtype=np.int16)
    frame_buffer = np.concatenate([frame_buffer, chunk])

    # send ONLY 512-sample frames
    while len(frame_buffer) >= TARGET:
        frame = frame_buffer[:TARGET]
        frame_buffer = frame_buffer[TARGET:]

        try:
            audio_queue.put(frame.tobytes(), block=False)
        except queue.Full:
            pass


# -----------------------------
# NETWORK SENDER THREAD
# -----------------------------
def sender():
    while True:
        try:
            data = audio_queue.get()

            if data is None:
                break

            if not ws.connected:
                print("WebSocket disconnected")
                break

            ws.send(data, opcode=ABNF.OPCODE_BINARY)

        except Exception as e:
            print("Send error:", e)
            if not ws.connected:
                break
            time.sleep(0.05)


# start sender thread
threading.Thread(target=sender, daemon=True).start()


# -----------------------------
# MIC STREAM
# -----------------------------
print("🎤 Streaming microphone... Ctrl+C to stop")

try:
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=BLOCKSIZE,  # ⚡ CRITICAL FIX (512 samples)
        callback=callback
    ):
        while True:
            time.sleep(1)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    audio_queue.put(None)
    ws.close()
