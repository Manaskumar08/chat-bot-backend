import subprocess
import uuid
from pathlib import Path
import time
from app.core.config import get_settings

settings = get_settings()


def text_to_speech(text):
    start_time = time.perf_counter()

    output_dir = Path(settings.TEMP_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{uuid.uuid4()}.wav"

    command = [
        str(settings.PIPER_EXE),
        "--model",
        str(settings.PIPER_MODEL),
        "--output_file",
        str(output_file)
    ]

    print("Command:", command)

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(text)

    if process.returncode != 0:
        raise RuntimeError(stderr)

    end_time = time.perf_counter()

    print(f"TTS latency: {(end_time - start_time):.3f} seconds")

    return str(output_file)


def generate_audio(text: str) -> str:
    return text_to_speech(text)
