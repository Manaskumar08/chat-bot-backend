from os import PathLike

import numpy as np
from faster_whisper import WhisperModel
import time

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)


def _prepare_audio(audio_input):
    """
    Accept either a numpy waveform or a path to an audio file.
    Faster-Whisper expects float32 audio in the [-1.0, 1.0] range for arrays.
    """
    if audio_input is None:
        return None

    if isinstance(audio_input, (str, bytes, PathLike)):
        return audio_input

    audio_np = np.asarray(audio_input)
    if audio_np.size == 0:
        return None

    if audio_np.dtype == np.int16:
        audio_np = audio_np.astype(np.float32) / 32768.0
    else:
        audio_np = audio_np.astype(np.float32, copy=False)

    return audio_np


def transcribe_from_array(audio_np):
    audio_input = _prepare_audio(audio_np)
    if audio_input is None:
        return ""

    start_time = time.perf_counter()
    segments, info  = model.transcribe(
        audio_input,
        beam_size=5,
        language="en",
        condition_on_previous_text=False
    )
    print(
        "duration:",
        info.duration,
        "language:",
        info.language,
        "prob:",
        info.language_probability
    )
    end_time = time.perf_counter()
    print(f"STT latency: {(end_time - start_time):.3f} seconds")

    text = ""

    for seg in segments:
        text += seg.text

    print(f"Transcribed text: {text.strip()}")
    return text.strip()

# Backward-compatible alias for the file-upload route.
speech_to_text = transcribe_from_array
