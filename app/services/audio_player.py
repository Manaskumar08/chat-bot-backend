# app/services/audio_player.py

from os import path

from importlib.resources import path

import sounddevice as sd
import soundfile as sf


def play_audio(wav_path: str):
    data, samplerate = sf.read(wav_path)
    sd.play(data, samplerate)   # play audio

def stop_audio():
    sd.stop()