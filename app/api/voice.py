from pathlib import Path

from fastapi import APIRouter
from fastapi import File
from fastapi import UploadFile

from app.services.llm import generate_response
from app.services.stt import speech_to_text

router = APIRouter()

@router.post("/voice-chat")

async def voice_chat(
    audio: UploadFile = File(...)
):

    temp_dir = Path("uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / audio.filename

    try:
        with open(temp_file, "wb") as f:
            f.write(await audio.read())

        user_text = speech_to_text(str(temp_file))
        ai_text = generate_response(user_text)
    finally:
        temp_file.unlink(missing_ok=True)

    # audio_file = generate_audio(ai_text)

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        # "audio_file": audio_file
    }
