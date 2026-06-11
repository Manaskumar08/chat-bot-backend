from pathlib import Path


def save_audio(audio_bytes, filename):

    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return str(output_path)
