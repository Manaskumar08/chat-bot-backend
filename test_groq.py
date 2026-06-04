# test_groq.py

from app.services.llm import ask_llm

for token in ask_llm(input("Enter your prompt: ")):
    print(token, end="")