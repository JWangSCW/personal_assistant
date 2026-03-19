from fastapi import FastAPI, HTTPException

from agent.parser import parse_user_request
from providers.geocode import geocode_city
# from providers.poi_provider import fetch_attractions, fetch_restaurants
from providers.weather import fetch_weather
# from agent.planner import build_candidate_pool
from llm.llm import format_itinerary_with_llm, generate_itinerary_with_llm
from utils.map import generate_map_html
from storage.memory import (
    REDIS_AVAILABLE,
    redis_client,
    create_job,
    get_job,
    save_session_preferences,
    get_session_preferences,
)


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

def _enrich_itinerary_with_coordinates(itinerary: dict, city_name: str) -> dict:
    from providers.geocode import geocode_place

    enriched = {}

    for day, places in itinerary.items():
        enriched_places = []

        for place in places:
            enriched_place = dict(place)

            if enriched_place.get("lat") is None or enriched_place.get("lon") is None:
                geo = geocode_place(enriched_place.get("name", ""), city_name)
                if geo:
                    enriched_place["lat"] = geo["lat"]
                    enriched_place["lon"] = geo["lon"]
                    if not enriched_place.get("address"):
                        enriched_place["address"] = geo["address"]

            enriched_places.append(enriched_place)

        enriched[day] = enriched_places

    return enriched

# def _build_itinerary_from_candidates(
#     candidate_pool: dict,
#     duration_days: int,
# ) -> dict:
#     itinerary = {}
#     combined = candidate_pool.get("restaurants", []) + candidate_pool.get("attractions", [])

#     index = 0
#     stops_per_day = 4

#     for day in range(1, duration_days + 1):
#         day_items = []
#         for _ in range(stops_per_day):
#             if index < len(combined):
#                 day_items.append(combined[index])
#                 index += 1

#         if day_items:
#             itinerary[f"Day {day}"] = day_items

#     return itinerary


def travel_agent_v2(user_query: str, session_preferences: dict | None = None):
    trace = ["Step 0 → analysing user request"]

    parsed = parse_user_request(user_query)
    trace.append("Step 1 → parsed city, duration and interests")
    session_preferences = session_preferences or {}

    if parsed.get("interests") == ["general"] and session_preferences.get("interests"):
        parsed["interests"] = session_preferences["interests"]

    if parsed.get("trip_style") == "general" and session_preferences.get("travel_style"):
        parsed["trip_style"] = session_preferences["travel_style"]

    trace.append("Step 1b → merged session preferences into parsed request")

    city_info = geocode_city(parsed["city"])
    trace.append("Step 2 → geocoded destination")

    # try:
    #     attractions = fetch_attractions(city_info["latitude"], city_info["longitude"])
    #     trace.append(f"Step 3 → fetched attractions ({len(attractions)})")
    # except Exception as e:
    #     print(f"fetch_attractions failed: {e}")
    #     attractions = []
    #     trace.append("Step 3 → attractions provider failed, using fallback")

    # try:
    #     restaurants = fetch_restaurants(
    #         city_info["latitude"],
    #         city_info["longitude"],
    #         parsed["interests"],
    #     )
    #     trace.append(f"Step 4 → fetched restaurants ({len(restaurants)})")
    # except Exception as e:
    #     print(f"fetch_restaurants failed: {e}")
    #     restaurants = []
    #     trace.append("Step 4 → restaurants provider failed, using fallback")
    trace.append("Step 3 → skipped external attractions provider")
    trace.append("Step 4 → skipped external restaurants provider")
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

    # try:
    #     if not attractions and not restaurants:
    #         itinerary = _build_fallback_itinerary(
    #             city_info=city_info,
    #             duration_days=parsed["duration_days"],
    #             interests=parsed["interests"],
    #         )
    #         trace.append("Step 6 → built fallback itinerary")
    #     else:
    #         candidate_pool = build_candidate_pool(
    #             attractions=attractions,
    #             restaurants=restaurants,
    #             trip_style=parsed["trip_style"],
    #         )

    #         itinerary = _build_itinerary_from_candidates(
    #             candidate_pool=candidate_pool,
    #             duration_days=parsed["duration_days"],
    #         )

    #         if not itinerary:
    #             itinerary = _build_fallback_itinerary(
    #                 city_info=city_info,
    #                 duration_days=parsed["duration_days"],
    #                 interests=parsed["interests"],
    #             )
    #             trace.append("Step 6 → candidate pool empty, fallback used")
    #         else:
    #             trace.append("Step 6 → built itinerary from candidate pool")
    # except Exception as e:
    #     print(f"candidate pool build failed: {e}")
    #     itinerary = _build_fallback_itinerary(
    #         city_info=city_info,
    #         duration_days=parsed["duration_days"],
    #         interests=parsed["interests"],
    #     )
    #     trace.append("Step 6 → candidate pool failed, fallback itinerary used")
    try:
        itinerary = generate_itinerary_with_llm(
            city=city_info["name"],
            duration_days=parsed["duration_days"],
            interests=parsed["interests"],
            trip_style=parsed["trip_style"],
            weather=weather,
            session_preferences=session_preferences,
        )
        trace.append("Step 6 → generated itinerary directly with LLM")
    except Exception as e:
        print(f"generate_itinerary_with_llm failed: {e}")
        itinerary = _build_fallback_itinerary(
            city_info=city_info,
            duration_days=parsed["duration_days"],
            interests=parsed["interests"],
        )
        trace.append("Step 6 → LLM itinerary generation failed, fallback used")

    itinerary = _enrich_itinerary_with_coordinates(
        itinerary=itinerary,
        city_name=city_info["name"],
    )
    trace.append("Step 6b → enriched itinerary with coordinates")

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

@app.get("/redis-test")
def redis_test():
    if not REDIS_AVAILABLE:
        return {"redis": "unavailable"}

    redis_client.set("healthcheck", "ok", ex=60)
    value = redis_client.get("healthcheck")

    return {"redis": value}

@app.post("/plan-trip")
def plan_trip_async(query: str, session_id: str | None = None):
    try:
        effective_session_id = session_id or "anonymous"
        job_id = create_job({
            "query": query,
            "session_id": effective_session_id,
        })
        return {
            "job_id": job_id,
            "status": "pending",
            "session_id": effective_session_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/preferences")
def set_session_preferences(session_id: str, preferences: dict):
    try:
        save_session_preferences(session_id, preferences)
        return {
            "session_id": session_id,
            "preferences": get_session_preferences(session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/preferences")
def read_session_preferences(session_id: str):
    try:
        return {
            "session_id": session_id,
            "preferences": get_session_preferences(session_id),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job

@app.get("/plan-trip")
def plan_trip(query: str):
    try:
        return travel_agent_v2(query)
    except Exception as e:
        print(f"plan_trip failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))