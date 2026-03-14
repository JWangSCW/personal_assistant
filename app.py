from fastapi import FastAPI, HTTPException

from agent.parser import parse_user_request
from providers.geocode import geocode_city
from providers.poi_provider import fetch_attractions, fetch_restaurants
from providers.weather import fetch_weather
from agent.planner import build_dynamic_itinerary
from llm.llm import format_itinerary_with_llm
from utils.map import generate_map_html

app = FastAPI()


def _build_fallback_itinerary(city_info: dict, duration_days: int, interests: list[str]) -> dict:
    duration_days = max(1, int(duration_days or 1))
    interests = interests or ["general"]

    plan = {}

    for day in range(1, duration_days + 1):
        plan[f"Day {day}"] = [
            {
                "name": f"Explore {city_info['name']} city center",
                "lat": city_info["latitude"],
                "lon": city_info["longitude"],
                "address": "",
                "tags": {"source": "fallback", "category": "city_center"},
            },
            {
                "name": f"Local discovery walk in {city_info['name']}",
                "lat": city_info["latitude"],
                "lon": city_info["longitude"],
                "address": "",
                "tags": {"source": "fallback", "interests": ",".join(interests)},
            },
        ]

    return plan


def travel_agent_v2(user_query: str):
    trace = ["Step 0 → analysing user request"]

    parsed = parse_user_request(user_query)
    trace.append("Step 1 → parsed city, duration and interests")

    city_info = geocode_city(parsed["city"])
    trace.append("Step 2 → geocoded destination")

    try:
        attractions = fetch_attractions(city_info["latitude"], city_info["longitude"])
        trace.append(f"Step 3 → fetched attractions ({len(attractions)})")
    except Exception as e:
        print(f"fetch_attractions failed: {e}")
        attractions = []
        trace.append("Step 3 → attractions provider failed, using fallback")

    try:
        restaurants = fetch_restaurants(
            city_info["latitude"],
            city_info["longitude"],
            parsed["interests"],
        )
        trace.append(f"Step 4 → fetched restaurants ({len(restaurants)})")
    except Exception as e:
        print(f"fetch_restaurants failed: {e}")
        restaurants = []
        trace.append("Step 4 → restaurants provider failed, using fallback")

    try:
        weather = fetch_weather(
            city_info["latitude"],
            city_info["longitude"],
            parsed["duration_days"],
        )
        trace.append("Step 5 → fetched weather forecast")
    except Exception as e:
        print(f"fetch_weather failed: {e}")
        weather = {"daily": []}
        trace.append("Step 5 → weather provider failed")

    try:
        if not attractions and not restaurants:
            itinerary = _build_fallback_itinerary(
                city_info=city_info,
                duration_days=parsed["duration_days"],
                interests=parsed["interests"],
            )
            trace.append("Step 6 → built fallback itinerary")
        else:
            itinerary = build_dynamic_itinerary(
                attractions=attractions,
                restaurants=restaurants,
                duration_days=parsed["duration_days"],
                trip_style=parsed["trip_style"],
            )
            if not itinerary:
                itinerary = _build_fallback_itinerary(
                    city_info=city_info,
                    duration_days=parsed["duration_days"],
                    interests=parsed["interests"],
                )
                trace.append("Step 6 → planner returned empty itinerary, fallback used")
            else:
                trace.append("Step 6 → built dynamic itinerary")
    except Exception as e:
        print(f"build_dynamic_itinerary failed: {e}")
        itinerary = _build_fallback_itinerary(
            city_info=city_info,
            duration_days=parsed["duration_days"],
            interests=parsed["interests"],
        )
        trace.append("Step 6 → planner failed, fallback itinerary used")

    try:
        travel_guide = format_itinerary_with_llm(
            city=city_info["name"],
            itinerary=itinerary,
            duration_days=parsed["duration_days"],
            interests=parsed["interests"],
            trip_style=parsed["trip_style"],
        )
        trace.append("Step 7 → generated travel guide")
    except Exception as e:
        print(f"format_itinerary_with_llm failed: {e}")
        travel_guide = (
            f"Here is a {parsed['duration_days']}-day trip suggestion for {city_info['name']}. "
            f"The itinerary was generated with fallback resilience because some upstream services were unavailable."
        )
        trace.append("Step 7 → LLM unavailable, fallback guide used")

    try:
        map_html = generate_map_html(itinerary, city_info=city_info)
        trace.append("Step 8 → generated interactive map")
    except Exception as e:
        print(f"generate_map_html failed: {e}")
        map_html = None
        trace.append("Step 8 → map generation failed")

    return {
        "parsed_request": parsed,
        "city_info": city_info,
        "weather_summary": weather,
        "raw_plan": itinerary,
        "travel_guide": travel_guide,
        "map_html": map_html,
        "trace": trace,
    }


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/plan-trip")
def plan_trip(query: str):
    try:
        return travel_agent_v2(query)
    except Exception as e:
        print(f"plan_trip failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))