import soundfile as sf


def save_audio(audio_bytes, filename):

    with open(filename, "wb") as f:
        f.write(audio_bytes)

    return filename