import os
import requests
from dotenv import load_dotenv

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_MODEL = os.getenv("SCW_MODEL", "llama-3.1-8b-instruct")
SCW_API_URL = "https://api.scaleway.ai/v1/chat/completions"


def format_itinerary_with_llm(city: str, itinerary: dict) -> str:
    if not SCW_SECRET_KEY:
        raise ValueError("SCW_SECRET_KEY is missing. Please set it in your .env file.")

    prompt = f"""
You are a helpful travel assistant.

Write a friendly 3-day travel guide for {city}.
The audience is a couple who loves food and history.

Use the itinerary below:
{itinerary}

Requirements:
- Keep it concise but natural
- Organize by Day 1, Day 2, Day 3
- Explain why each day is interesting
- Mention food and cultural highlights
- End with one practical travel tip
"""

    payload = {
        "model": SCW_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful and concise travel planner."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {SCW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        SCW_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]