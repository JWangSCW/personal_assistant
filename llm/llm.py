import os
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

    # RAG first, fallback to local knowledge
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