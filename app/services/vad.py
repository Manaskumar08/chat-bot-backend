import torch
import numpy as np
from silero_vad import VADIterator


# Load model once
model, _ = torch.hub.load(
    repo_or_dir="snakers4/silero-vad",
    model="silero_vad",
    trust_repo=True
)

model.eval()
model.to("cpu")


class StreamingVAD:
    def __init__(
        self,
        threshold: float = 0.5,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 200,
    ):
        self.vad_iterator = VADIterator(
            model,
            threshold=threshold,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )

    def process(self, audio_bytes: bytes):
        """
        Returns:
            "start" -> speech started
            "end"   -> speech ended
            None    -> no event
        """

        try:
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

            if len(audio_np) == 0:
                return None

            # Normalize to [-1, 1]
            audio_float = audio_np.astype(np.float32) / 32768.0

            audio_tensor = torch.from_numpy(audio_float)

            event = self.vad_iterator(audio_tensor)

            if event is None:
                return None

            if "start" in event:
                print(f"VAD START: {event}")
                return "start"

            if "end" in event:
                print(f"VAD END: {event}")
                return "end"

            return None

        except Exception as e:
            print(f"VAD error: {e}")
            return None

    def reset(self):
        self.vad_iterator.reset_states()