import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_MODEL = os.getenv("SCW_MODEL", "llama-3.1-8b-instruct")
SCW_API_URL = "https://api.scaleway.ai/v1/chat/completions"


def parse_user_request(user_prompt: str) -> dict:
    prompt = f"""
Extract structured travel parameters from the request.

Return ONLY valid JSON with this schema:
{{
  "city": "string",
  "duration_days": 1,
  "interests": ["string", "string"],
  "trip_style": "general"
}}

Rules:
- duration_days must be an integer between 1 and 7
- if missing, default to 2
- interests should be short tags like food, history, museums, romantic, nightlife, family, shopping, art, parks, cafes
- if no interest is given, return ["general"]
- trip_style must be one of: general, food, chill
- use "food" for requests focused on restaurants, cafes, bakeries, wine, local cuisine
- use "chill" for requests focused on relaxing, slow pace, parks, scenic walks, cafes, quiet atmosphere
- otherwise use "general"

Request:
{user_prompt}
"""

    payload = {
        "model": SCW_MODEL,
        "messages": [
            {"role": "system", "content": "You extract structured travel parameters."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {SCW_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(SCW_API_URL, headers=headers, json=payload, timeout=60)
    data = response.json()

    if response.status_code != 200:
        raise RuntimeError(f"Parser API error: status={response.status_code}, body={data}")

    if "choices" not in data:
        raise RuntimeError(f"Unexpected parser response: {data}")

    content = data["choices"][0]["message"]["content"].strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        raise RuntimeError(f"Parser did not return valid JSON: {content}")

    parsed["duration_days"] = max(1, min(7, int(parsed.get("duration_days", 2))))
    parsed["interests"] = parsed.get("interests", ["general"]) or ["general"]

    trip_style = (parsed.get("trip_style") or "general").lower()
    if trip_style not in ["general", "food", "chill"]:
        trip_style = "general"
    parsed["trip_style"] = trip_style

    return parsed