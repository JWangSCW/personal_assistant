import time
from datetime import datetime, timezone

from storage.memory import (
    get_job,
    update_job,
    redis_client,
    get_session_preferences,
    save_session_trip_result,
    get_session_trip_result,
)
from agent.parser import parse_user_request
from providers.geocode import geocode_city
from providers.weather import fetch_weather
from llm.llm import (
    format_itinerary_with_llm,
    generate_itinerary_with_llm,
    refine_itinerary_with_llm,
)
from utils.map import generate_map_html


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


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


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


def get_steps_from_job(job: dict) -> list[dict]:
    steps = job.get("steps")
    if not steps:
        return build_initial_arch_steps()

    normalized = []
    for step in steps:
        step_id = step["id"]
        normalized.append(
            {
                "id": step_id,
                "label": step.get("label", ARCH_STEP_LABELS.get(step_id, step_id)),
                "status": step.get("status", "pending"),
                "started_at": step.get("started_at"),
                "ended_at": step.get("ended_at"),
                "duration_s": float(step.get("duration_s", 0) or 0),
            }
        )
    return normalized


def save_steps(job_id: str, steps: list[dict], current_step: str, **extra_fields):
    update_job(
        job_id,
        current_step=current_step,
        steps=steps,
        **extra_fields,
    )


def set_job_running(job_id: str):
    job = get_job(job_id)
    if not job:
        return
    update_job(
        job_id,
        status="running",
        current_step=job.get("current_step", "worker"),
        steps=get_steps_from_job(job),
    )


def mark_step_running(job_id: str, step_id: str):
    job = get_job(job_id)
    if not job:
        return

    steps = get_steps_from_job(job)
    now_iso = utc_now_iso()

    for step in steps:
        if step["id"] == step_id:
            if step["status"] != "done":
                step["status"] = "running"
            if not step.get("started_at"):
                step["started_at"] = now_iso
            step["ended_at"] = None
            break

    save_steps(job_id, steps, current_step=step_id)


def mark_step_done(job_id: str, step_id: str):
    job = get_job(job_id)
    if not job:
        return

    steps = get_steps_from_job(job)
    end_dt = utc_now()
    end_iso = end_dt.isoformat()

    for step in steps:
        if step["id"] == step_id:
            if not step.get("started_at"):
                step["started_at"] = end_iso

            start_dt = parse_iso_datetime(step.get("started_at"))
            duration_s = 0.0
            if start_dt:
                duration_s = round((end_dt - start_dt).total_seconds(), 3)

            step["status"] = "done"
            step["ended_at"] = end_iso
            step["duration_s"] = max(duration_s, 0.0)
            break

    save_steps(job_id, steps, current_step=step_id)


def mark_step_failed(job_id: str, step_id: str, error: str | None = None):
    job = get_job(job_id)
    if not job:
        return

    steps = get_steps_from_job(job)
    end_dt = utc_now()
    end_iso = end_dt.isoformat()

    for step in steps:
        if step["id"] == step_id:
            if not step.get("started_at"):
                step["started_at"] = end_iso

            start_dt = parse_iso_datetime(step.get("started_at"))
            duration_s = 0.0
            if start_dt:
                duration_s = round((end_dt - start_dt).total_seconds(), 3)

            step["status"] = "failed"
            step["ended_at"] = end_iso
            step["duration_s"] = max(duration_s, 0.0)
            break

    save_steps(job_id, steps, current_step=step_id, error=error)


def run_timed_step(job_id: str, step_id: str, fn, *args, **kwargs):
    mark_step_running(job_id, step_id)
    try:
        result = fn(*args, **kwargs)
        mark_step_done(job_id, step_id)
        return result
    except Exception as e:
        mark_step_failed(job_id, step_id, error=str(e))
        raise


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


def _fetch_weather_safe(city_info: dict, duration_days: int, trace: list[str]) -> dict:
    try:
        weather = fetch_weather(
            city_info["latitude"],
            city_info["longitude"],
            duration_days,
        )
        trace.append("Step 5 → fetched weather forecast")
        return weather
    except Exception as e:
        print(f"[worker][weather] fetch_weather failed: {e}")
        trace.append("Step 5 → weather provider failed")
        return {"daily": []}


def process_plan_trip(job_id: str, job: dict):
    payload = job["payload"]
    query = payload["query"]
    session_id = payload.get("session_id", "anonymous")

    preferences = get_session_preferences(session_id)

    print(f"[worker][plan_trip] session_id={session_id}")
    print(f"[worker][plan_trip] preferences={preferences}")

    set_job_running(job_id)
    mark_step_running(job_id, "worker")

    try:
        trace = ["Step 0 → analysing user request"]

        parsed = run_timed_step(job_id, "parser_llm", parse_user_request, query)
        trace.append("Step 1 → parsed city, duration and interests")

        if parsed.get("interests") == ["general"] and preferences.get("interests"):
            parsed["interests"] = preferences["interests"]

        if parsed.get("trip_style") == "general" and preferences.get("travel_style"):
            parsed["trip_style"] = preferences["travel_style"]

        trace.append("Step 1b → merged session preferences into parsed request")

        city_info = run_timed_step(job_id, "geocode", geocode_city, parsed["city"])
        trace.append("Step 2 → geocoded destination")
        trace.append("Step 3 → skipped external attractions provider")
        trace.append("Step 4 → skipped external restaurants provider")

        weather = _fetch_weather_safe(city_info, parsed["duration_days"], trace)

        def _generate_itinerary_bundle():
            try:
                itinerary = generate_itinerary_with_llm(
                    city=city_info["name"],
                    duration_days=parsed["duration_days"],
                    interests=parsed["interests"],
                    trip_style=parsed["trip_style"],
                    weather=weather,
                    session_preferences=preferences,
                )
                itinerary_trace = "Step 6 → generated itinerary directly with LLM"
            except Exception as e:
                print(f"[worker][plan_trip] generate_itinerary_with_llm failed: {e}")
                itinerary = _build_fallback_itinerary(
                    city_info=city_info,
                    duration_days=parsed["duration_days"],
                    interests=parsed["interests"],
                )
                itinerary_trace = "Step 6 → LLM itinerary generation failed, fallback used"

            itinerary = _enrich_itinerary_with_coordinates(
                itinerary=itinerary,
                city_name=city_info["name"],
            )

            try:
                travel_guide = format_itinerary_with_llm(
                    city=city_info["name"],
                    itinerary=itinerary,
                    duration_days=parsed["duration_days"],
                    interests=parsed["interests"],
                    trip_style=parsed["trip_style"],
                )
                guide_trace = "Step 7 → generated travel guide"
            except Exception as e:
                print(f"[worker][plan_trip] format_itinerary_with_llm failed: {e}")
                travel_guide = (
                    f"Here is a {parsed['duration_days']}-day trip suggestion for {city_info['name']}. "
                    f"The itinerary was generated with fallback resilience because some upstream services were unavailable."
                )
                guide_trace = "Step 7 → LLM unavailable, fallback guide used"

            return itinerary, travel_guide, itinerary_trace, guide_trace

        itinerary, travel_guide, itinerary_trace, guide_trace = run_timed_step(
            job_id,
            "itinerary_llm",
            _generate_itinerary_bundle,
        )
        trace.append(itinerary_trace)
        trace.append("Step 6b → enriched itinerary with coordinates")
        trace.append(guide_trace)

        try:
            map_html = run_timed_step(job_id, "map", generate_map_html, itinerary, city_info=city_info)
            trace.append("Step 8 → generated interactive map")
        except Exception as e:
            print(f"[worker][plan_trip] generate_map_html failed: {e}")
            map_html = None
            trace.append("Step 8 → map generation failed")

        mark_step_done(job_id, "worker")

    except Exception as e:
        mark_step_failed(job_id, "worker", error=str(e))
        raise

    result = {
        "parsed_request": parsed,
        "city_info": city_info,
        "weather_summary": weather,
        "raw_plan": itinerary,
        "travel_guide": travel_guide,
        "map_html": map_html,
        "trace": trace,
        "session_preferences": preferences,
    }

    save_session_trip_result(session_id, result)

    final_job = get_job(job_id)
    final_steps = get_steps_from_job(final_job) if final_job else build_initial_arch_steps()

    update_job(
        job_id,
        status="completed",
        result=result,
        session_id=session_id,
        current_step="map",
        steps=final_steps,
        error=None,
    )


def process_refine_trip(job_id: str, job: dict):
    payload = job["payload"]
    session_id = payload["session_id"]
    instruction = payload["instruction"]

    print(f"[worker][refine_trip] session_id={session_id}")
    print(f"[worker][refine_trip] instruction={instruction}")

    set_job_running(job_id)
    mark_step_running(job_id, "worker")

    try:
        current_trip = get_session_trip_result(session_id)
        if not current_trip:
            raise ValueError(f"No existing trip found for session_id={session_id}")

        parsed_request = current_trip.get("parsed_request", {})
        city_info = current_trip.get("city_info", {})
        weather_summary = current_trip.get("weather_summary", {})
        current_itinerary = current_trip.get("raw_plan", {})
        session_preferences = current_trip.get("session_preferences", {}) or get_session_preferences(session_id)

        if not current_itinerary:
            raise ValueError(f"No itinerary found for session_id={session_id}")

        refined_itinerary = run_timed_step(
            job_id,
            "parser_llm",
            refine_itinerary_with_llm,
            city=city_info.get("name", parsed_request.get("city", "")),
            duration_days=parsed_request.get("duration_days", 1),
            interests=parsed_request.get("interests", ["general"]),
            trip_style=parsed_request.get("trip_style", "general"),
            weather=weather_summary,
            session_preferences=session_preferences,
            current_itinerary=current_itinerary,
            instruction=instruction,
        )

        refined_itinerary = run_timed_step(
            job_id,
            "geocode",
            _enrich_itinerary_with_coordinates,
            itinerary=refined_itinerary,
            city_name=city_info.get("name", parsed_request.get("city", "")),
        )

        travel_guide = run_timed_step(
            job_id,
            "itinerary_llm",
            format_itinerary_with_llm,
            city=city_info.get("name", parsed_request.get("city", "")),
            itinerary=refined_itinerary,
            duration_days=parsed_request.get("duration_days", 1),
            interests=parsed_request.get("interests", ["general"]),
            trip_style=parsed_request.get("trip_style", "general"),
        )

        try:
            map_html = run_timed_step(
                job_id,
                "map",
                generate_map_html,
                refined_itinerary,
                city_info=city_info,
            )
        except Exception as e:
            print(f"[worker][refine_trip] generate_map_html failed: {e}")
            map_html = None

        mark_step_done(job_id, "worker")

    except Exception as e:
        mark_step_failed(job_id, "worker", error=str(e))
        raise

    previous_trace = current_trip.get("trace", [])
    trace = list(previous_trace) + [
        "Step 9 → refined itinerary with LLM",
        "Step 10 → regenerated travel guide after refinement",
    ]

    previous_history = current_trip.get("refinement_history", [])
    refinement_history = previous_history + [instruction]

    result = {
        "parsed_request": parsed_request,
        "city_info": city_info,
        "weather_summary": weather_summary,
        "raw_plan": refined_itinerary,
        "travel_guide": travel_guide,
        "map_html": map_html,
        "trace": trace,
        "session_preferences": session_preferences,
        "last_instruction": instruction,
        "refinement_history": refinement_history,
    }

    save_session_trip_result(session_id, result)

    final_job = get_job(job_id)
    final_steps = get_steps_from_job(final_job) if final_job else build_initial_arch_steps()

    update_job(
        job_id,
        status="completed",
        result=result,
        session_id=session_id,
        current_step="map",
        steps=final_steps,
        error=None,
    )


def find_pending_job():
    for key in redis_client.scan_iter("job:*"):
        job_id = key.split(":", 1)[1]
        job = get_job(job_id)
        if job and job.get("status") == "pending":
            return job_id, job
    return None, None


def worker_loop():
    while True:
        job_id, job = find_pending_job()

        if not job_id:
            time.sleep(1)
            continue

        try:
            payload = job.get("payload", {})
            job_type = payload.get("type", "plan_trip")

            if job_type == "plan_trip":
                process_plan_trip(job_id, job)
            elif job_type == "refine_trip":
                process_refine_trip(job_id, job)
            else:
                raise ValueError(f"Unsupported job type: {job_type}")

        except Exception as e:
            print(f"[worker] job failed: {e}")
            update_job(
                job_id,
                status="failed",
                error=str(e),
            )


if __name__ == "__main__":
    worker_loop()