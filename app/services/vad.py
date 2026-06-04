import torch
import numpy as np

model, utils = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    trust_repo=True
)

(get_speech_timestamps, _, _, _, _) = utils


def is_speech(audio_int16: bytes) -> bool:
    audio = np.frombuffer(audio_int16, dtype=np.int16)
    audio = torch.tensor(audio / 32768.0)

    speech = get_speech_timestamps(audio, model, sampling_rate=16000)

    return len(speech) > 0