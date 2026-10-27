import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASETEN_BASE_URL"),
    api_key=os.getenv("BASETEN_API_KEY"),
)

response = client.chat.completions.create(
    model=os.getenv("BASETEN_MODEL"),
    messages=[
        {
            "role": "user",
            "content": "Hello! Introduce yourself in one sentence.",
        }
    ],
    max_tokens=150,
)

print(response.choices[0].message.content)