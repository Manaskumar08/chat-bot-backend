from groq import Groq
from app.core.config import get_settings
import time
# from google import genai


settings = get_settings()


client = Groq(api_key=settings.GROQ_API_KEY)


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
    start_time = time.perf_counter()

    for chunk in stream:

        delta = chunk.choices[0].delta.content

        if delta:
            yield delta
    end_time = time.perf_counter()
    print(f"LLM latency: {(end_time - start_time):.3f} seconds")

# client = genai.Client(
#     api_key=settings.GEMINI_API_KEY
# )
# print("Gemini client initialized", flush=True)


# def ask_llm(prompt):

#     start_time = time.perf_counter()
#     stream = client.models.generate_content_stream(
#         model="gemini-2.5-flash",
#         contents=prompt
#     )

#     for chunk in stream:
#         if chunk.text:
#             yield chunk.text
#     end_time = time.perf_counter()
#     print(f"LLM latency: {(end_time - start_time):.3f} seconds")



def generate_response(prompt: str) -> str:
    return "".join(ask_llm(prompt))
