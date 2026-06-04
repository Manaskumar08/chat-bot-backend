from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


def transcribe_from_array(audio_np):

    segments, _ = model.transcribe(
        audio_np,
        beam_size=1
    )

    text = ""

    for seg in segments:
        text += seg.text

    return text.strip()