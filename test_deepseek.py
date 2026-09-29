import os

from dotenv import load_dotenv
from openai import OpenAI


# =========================
# Load environment variables
# =========================

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise RuntimeError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件。"
    )


# =========================
# Create DeepSeek client
# =========================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


# =========================
# Send request
# =========================

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {
            "role": "system",
            "content": (
                "You are an English speaking coach. "
                "Talk naturally like a friendly native English speaker. "
                "Keep your response concise and conversational."
            )
        },
        {
            "role": "user",
            "content": "Hello, I'm Lily. Who are you? What's your name?"
        }
    ],
    stream=False,
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    }
)


# =========================
# Print response
# =========================

print()
print("================================")
print("       DeepSeek Response")
print("================================")
print()

print(response.choices[0].message.content)

print()
print("================================")
print("Model:", response.model)
print("================================")