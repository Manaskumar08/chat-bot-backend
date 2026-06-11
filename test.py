import sounddevice as sd
import soundfile as sf

from app.services.tts import text_to_speech


def play_audio(wav_path):
    data, samplerate = sf.read(wav_path)
    sd.play(data, samplerate)
    sd.wait()   # wait until playback finishes


wav_path = text_to_speech("Hello Manas")
play_audio(wav_path)