from gtts import gTTS
from pydub import AudioSegment
import os

# 1. The text you want in the audio file
text_content = "Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design."

# 2. Generate the initial speech (defaults to MP3)
tts = gTTS(text=text_content, lang='en', slow=False)
tts.save("temp.mp3")

# 3. Convert the MP3 file into your clean 'hello.wav' file
sound = AudioSegment.from_mp3("temp.mp3")
sound.export("hello.wav", format="wav")

# 4. Clean up the temporary file
os.remove("temp.mp3")

print("Success! 'hello.wav' has been generated and saved to your directory.")