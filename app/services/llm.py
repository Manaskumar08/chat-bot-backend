from groq import Groq
from app.config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def ask_llm(prompt):

    prompt = prompt[:4000]

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=500,
        stream=True,
    )

    for chunk in stream:

        delta = chunk.choices[0].delta.content

        if delta:
            yield delta