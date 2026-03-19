import os
import json
import requests
from dotenv import load_dotenv
from knowledge import load_city_knowledge
from llm.vector_store import search

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_MODEL = os.getenv("SCW_MODEL", "llama-3.1-8b-instruct")
SCW_API_URL = "https://api.scaleway.ai/v1/chat/completions"


def format_itinerary_with_llm(
    city: str,
    itinerary: dict,
    duration_days: int,
    interests: list[str] | None = None,
    trip_style: str = "general",
) -> str:
    if not SCW_SECRET_KEY:
        raise ValueError("SCW_SECRET_KEY missing in .env")

    interests = interests or ["general"]
    interests_str = ", ".join(interests)

    knowledge_chunks = search(city, top_k=3)
    knowledge = "\n".join(knowledge_chunks) if knowledge_chunks else load_city_knowledge(city)

    if trip_style == "food":
        style_instruction = """
- Emphasize local cuisine, signature dishes, cafes, bakeries, wine bars, and culinary atmosphere
- Keep the pace centered around eating and relaxing between food stops
"""
    elif trip_style == "chill":
        style_instruction = """
- Emphasize relaxed pace, scenic moments, parks, cafes, calm neighborhoods, and slow exploration
- Avoid sounding rushed or overly packed
"""
    elif trip_style == "romantic":
        style_instruction = """
- Emphasize atmosphere, scenic beauty, elegant moments, charming neighborhoods, and date-friendly places
- Make the tone warm, intimate, and memorable
"""
    elif trip_style == "party":
        style_instruction = """
- Emphasize nightlife, lively districts, bars, rooftops, music venues, and energetic evening atmosphere
- Keep the tone dynamic and exciting
"""
    elif trip_style == "family":
        style_instruction = """
- Emphasize family-friendly pacing, accessible attractions, open spaces, and practical comfort
- Avoid overly rushed or nightlife-oriented suggestions
"""
    elif trip_style == "culture":
        style_instruction = """
- Emphasize landmarks, museums, heritage, architecture, and the historical significance of each stop
- Keep the tone informative but still engaging
"""
    else:
        style_instruction = """
- Keep a balanced city-trip style with major highlights and practical pacing
"""

    prompt = f"""
You are a helpful travel assistant.

City knowledge:
{knowledge}

Trip context:
- City: {city}
- Duration: {duration_days} day(s)
- Interests: {interests_str}
- Trip style: {trip_style}

Itinerary:
{itinerary}

Write a friendly travel guide that matches EXACTLY the itinerary duration.

Requirements:
- Write for exactly {duration_days} day(s), no more, no less
- Organize the guide using the same day labels as the itinerary
- Do not invent extra days
- Explain why each place is interesting
- Mention food highlights when relevant
- End with one practical travel tip

Style requirements:
{style_instruction}
"""

    payload = {
        "model": SCW_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise and accurate travel planner."
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

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"Scaleway API returned non-JSON response: "
            f"status={response.status_code}, body={response.text}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Scaleway API error: status={response.status_code}, body={data}"
        )

    if "choices" in data and data["choices"]:
        return data["choices"][0]["message"]["content"]

    raise RuntimeError(f"Unexpected Scaleway API response format: {data}")


def generate_itinerary_with_llm(
    city: str,
    duration_days: int,
    interests: list[str] | None = None,
    trip_style: str = "general",
    weather: dict | None = None,
    session_preferences: dict | None = None,
) -> dict:
    if not SCW_SECRET_KEY:
        raise ValueError("SCW_SECRET_KEY missing in .env")

    interests = interests or ["general"]
    session_preferences = session_preferences or {}
    weather = weather or {}

    interests_str = ", ".join(interests)
    session_pref_str = json.dumps(session_preferences, ensure_ascii=False)
    weather_str = json.dumps(weather, ensure_ascii=False)

    prompt = f"""
You are a travel planning assistant.

Generate a realistic itinerary in valid JSON only.

Return ONLY valid JSON with this structure:
{{
  "Day 1": [
    {{
      "name": "Place name",
      "lat": null,
      "lon": null,
      "address": "",
      "tags": {{
        "source": "llm"
      }}
    }}
  ]
}}

Rules:
- Write exactly {duration_days} day(s): Day 1 to Day {duration_days}
- Each day should contain 4 places
- The itinerary must strongly match the user's theme and interests
- Prefer well-known, actually relevant places for the city
- Avoid random offices, service centers, tiny memorials, or generic map artifacts
- If trip_style is "food", prioritize neighborhoods, markets, restaurants, cafes, bakeries, food streets, and iconic local food spots
- If trip_style is "party", prioritize nightlife districts, bars, rooftops, clubs, live music, and lively evening areas
- If trip_style is "culture", prioritize museums, landmarks, architecture, heritage, and iconic sightseeing
- If trip_style is "romantic", prioritize scenic, elegant, atmospheric places and good date-night areas
- If trip_style is "family", prioritize family-friendly places
- Use lat and lon as null
- Keep address as empty string if unknown
- Keep tags simple, for example:
  {{
    "source": "llm",
    "theme": "food"
  }}
- Do not wrap the JSON in markdown
- Do not add any explanation before or after the JSON

Context:
- City: {city}
- Duration: {duration_days}
- Interests: {interests_str}
- Trip style: {trip_style}
- Session preferences: {session_pref_str}
- Weather summary: {weather_str}

Return JSON only.
"""

    payload = {
        "model": SCW_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You generate structured travel itineraries in strict JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.4
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

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"Scaleway API returned non-JSON response: "
            f"status={response.status_code}, body={response.text}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Scaleway API error: status={response.status_code}, body={data}"
        )

    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"Unexpected Scaleway API response format: {data}")

    content = data["choices"][0]["message"]["content"].strip()

    try:
        itinerary = json.loads(content)
    except json.JSONDecodeError:
        raise RuntimeError(f"Itinerary generator did not return valid JSON: {content}")

    return itinerary