from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent.parser import parse_user_request
from providers.geocode import geocode_city
from providers.weather import fetch_weather
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


ARCH_STEP_ORDER = [
    "ui",
    "api",
    "redis",
    "worker",
    "parser_llm",
    "itinerary_llm",
    "geocode",
    "map",
]

ARCH_STEP_LABELS = {
    "ui": "UI",
    "api": "FastAPI",
    "redis": "Redis",
    "worker": "Worker",
    "parser_llm": "Parser LLM",
    "itinerary_llm": "Itinerary LLM",
    "geocode": "Geocode",
    "map": "Map Render",
}


def build_initial_arch_steps() -> list[dict]:
    steps = []

    for step_id in ARCH_STEP_ORDER:
        status = "pending"
        if step_id in ["ui", "api", "redis"]:
            status = "done"

        steps.append(
            {
                "id": step_id,
                "label": ARCH_STEP_LABELS[step_id],
                "status": status,
                "started_at": None,
                "ended_at": None,
                "duration_s": 0.0,
            }
        )

    return steps


class PlanTripRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None


class RefineTripRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    instruction: str = Field(..., min_length=1)


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
def plan_trip_async(request: PlanTripRequest):
    try:
        effective_session_id = request.session_id or "anonymous"
        job_id = create_job(
            {
                "type": "plan_trip",
                "query": request.query,
                "session_id": effective_session_id,
                "status": "pending",
                "current_step": "redis",
                "steps": build_initial_arch_steps(),
            }
        )
        return {
            "job_id": job_id,
            "status": "pending",
            "session_id": effective_session_id,
            "job_type": "plan_trip",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refine-trip")
def refine_trip_async(request: RefineTripRequest):
    try:
        if request.session_id == "anonymous":
            raise HTTPException(
                status_code=400,
                detail="refine-trip requires a non-anonymous session_id",
            )

        job_id = create_job(
            {
                "type": "refine_trip",
                "session_id": request.session_id,
                "instruction": request.instruction,
                "status": "pending",
                "current_step": "redis",
                "steps": build_initial_arch_steps(),
            }
        )

        return {
            "job_id": job_id,
            "status": "pending",
            "session_id": request.session_id,
            "job_type": "refine_trip",
        }
    except HTTPException:
        raise
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