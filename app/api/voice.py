from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File

from app.services.stt import speech_to_text
from app.services.llm import generate_response
from app.services.tts import generate_audio

router = APIRouter()

@router.post("/voice-chat")

async def voice_chat(
    audio: UploadFile = File(...)
):

    temp_file = f"uploads/{audio.filename}"

    with open(temp_file, "wb") as f:
        f.write(await audio.read())

    user_text = speech_to_text(temp_file)

    ai_text = generate_response(user_text)

    # audio_file = generate_audio(ai_text)

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        # "audio_file": audio_file
    }