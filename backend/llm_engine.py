from openai import OpenAI
import os

from dotenv import load_dotenv

load_dotenv()


client = OpenAI(

    base_url="https://openrouter.ai/api/v1",

    api_key=os.getenv(
        "OPENAI_API_KEY"
    ),
)


def generate_response(prompt):

    completion = client.chat.completions.create(

        model="openai/gpt-oss-120b:free",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]

    )

    return completion.choices[0].message.content