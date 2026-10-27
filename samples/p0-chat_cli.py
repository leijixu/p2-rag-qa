import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

messages = []
while True:
    user_input = input("\n你: ").strip()
    if user_input == "exit":
        break
    if not user_input:
        continue

    messages.append({"role": "user", "content": user_input})

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True,
    )

    print("AI: ", end="")
    reply = ""
    for chunk in resp:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
            reply += content
    print()

    messages.append({"role": "assistant", "content": reply})

print("\n再见")
