import cmd
import subprocess
import uuid

from app.config import PIPER_EXE, PIPER_MODEL


def text_to_speech(text):

    output_file = f"temp/{uuid.uuid4()}.wav"

    cmd = [
        PIPER_EXE,
        "--model",
        PIPER_MODEL,
        "--output_file",
        output_file
    ]

    print("Command:", cmd)

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        text=True
    )

    process.communicate(text)

    return output_file