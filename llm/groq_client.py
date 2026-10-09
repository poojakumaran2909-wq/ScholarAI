import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    timeout=30.0
)


def generate_answer(prompt):
    print("RAG: Sending request to Groq...")

    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="openai/gpt-oss-20b"
    )

    print("RAG: Groq response received.")

    return response.choices[0].message.content