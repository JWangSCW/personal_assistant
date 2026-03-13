from llm import format_itinerary_with_llm
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_MODEL = os.getenv("SCW_MODEL", "llama-3.1-8b-instruct")
SCW_API_URL = "https://api.scaleway.ai/v1/chat/completions"


def parse_user_request(user_prompt):

    prompt = f"""
Extract the destination city from this travel request.

Return only the city name.

Request:
{user_prompt}
"""

    payload = {
        "model": SCW_MODEL,
        "messages": [
            {"role": "system", "content": "You extract structured travel information."},
            {"role": "user", "content": prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {SCW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(SCW_API_URL, headers=headers, json=payload)
    data = response.json()

    city = data["choices"][0]["message"]["content"].strip()

    return city