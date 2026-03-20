import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_MODEL = os.getenv("SCW_MODEL", "gpt-oss-120b")
SCW_PROJECT_ID = os.getenv("SCW_PROJECT_ID")

SCW_API_URL = f"https://api.scaleway.ai/{SCW_PROJECT_ID}/v1/chat/completions"


def detect_keywords(user_prompt: str) -> dict:
    text = user_prompt.lower()

    interests = []
    trip_style = None

    if any(k in text for k in ["night club", "nightclub", "club", "bar", "beer", "party", "crazy"]):
        interests.extend(["nightlife", "bars"])
        trip_style = "party"

    if any(k in text for k in ["romantic", "date", "couple", "honeymoon"]):
        if "romantic" not in interests:
            interests.append("romantic")
        if trip_style is None:
            trip_style = "romantic"

    if any(k in text for k in ["museum", "museums", "history", "historic", "art", "monument", "heritage"]):
        interests.extend(["museums", "history"])
        if trip_style is None:
            trip_style = "culture"

    deduped_interests = []
    for item in interests:
        if item not in deduped_interests:
            deduped_interests.append(item)

    return {
        "interests": deduped_interests,
        "trip_style": trip_style,
    }


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
- interests should be short tags like food, history, museums, romantic, nightlife, bars, family, shopping, art, parks, cafes, architecture
- if no interest is given, return ["general"]
- trip_style must be one of: general, food, chill, romantic, party, family, culture
- use "food" for requests focused on restaurants, cafes, bakeries, wine, local cuisine, bars
- use "chill" for requests focused on relaxing, slow pace, parks, scenic walks, cafes, quiet atmosphere
- use "romantic" for requests focused on couples, dates, honeymoon, romantic atmosphere
- use "party" for requests focused on nightlife, clubs, bars, drinks, beer, party, crazy vibes
- use "family" for requests focused on kids, children, parents, family-friendly activities
- use "culture" for requests focused on museums, history, monuments, heritage, art
- otherwise use "general"
- do not infer extra interests only from the city's reputation
- only include interests that are explicitly stated or strongly implied by the request

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
    allowed_trip_styles = ["general", "food", "chill", "romantic", "party", "family", "culture"]
    if trip_style not in allowed_trip_styles:
        trip_style = "general"
    parsed["trip_style"] = trip_style

    keywords = detect_keywords(user_prompt)

    if parsed["interests"] == ["general"] and keywords["interests"]:
        parsed["interests"] = keywords["interests"]

    if parsed["trip_style"] == "general" and keywords["trip_style"]:
        parsed["trip_style"] = keywords["trip_style"]

    text = user_prompt.lower()

    explicitly_cultural = any(
        keyword in text
        for keyword in [
            "museum",
            "museums",
            "art",
            "gallery",
            "history",
            "historic",
            "heritage",
            "monument",
        ]
    )

    if parsed["trip_style"] == "food" and not explicitly_cultural:
        allowed_food_interests = {"food", "cafes", "bars"}
        parsed["interests"] = [i for i in parsed["interests"] if i in allowed_food_interests]

        if not parsed["interests"]:
            parsed["interests"] = ["food"]

    deduped_interests = []
    for item in parsed["interests"]:
        if item not in deduped_interests:
            deduped_interests.append(item)
    parsed["interests"] = deduped_interests

    return parsed