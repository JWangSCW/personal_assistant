from agent.parser import parse_user_request
from providers.geocode import geocode_city
from providers.poi_provider import fetch_attractions, fetch_restaurants
from providers.weather import fetch_weather
from agent.planner import build_dynamic_itinerary
from llm.llm import format_itinerary_with_llm
from utils.map import generate_map




def travel_agent_v2(user_query: str):
    trace = ["Step 0 → analysing user request"]

    parsed = parse_user_request(user_query)
    trace.append("Step 1 → parsed city, duration and interests")

    city_info = geocode_city(parsed["city"])
    trace.append("Step 2 → geocoded destination")

    attractions = fetch_attractions(city_info["latitude"], city_info["longitude"])
    trace.append("Step 3 → fetched attractions")

    restaurants = fetch_restaurants(
        city_info["latitude"],
        city_info["longitude"],
        parsed["interests"],
    )
    trace.append("Step 4 → fetched restaurants")

    weather = fetch_weather(
        city_info["latitude"],
        city_info["longitude"],
        parsed["duration_days"],
    )
    trace.append("Step 5 → fetched weather forecast")

    itinerary = build_dynamic_itinerary(
        attractions=attractions,
        restaurants=restaurants,
        duration_days=parsed["duration_days"],
        trip_style=parsed["trip_style"],
    )
    trace.append("Step 6 → built dynamic itinerary")

    travel_guide = format_itinerary_with_llm(
        city=city_info["name"],
        itinerary=itinerary,
        duration_days=parsed["duration_days"],
        interests=parsed["interests"],
        trip_style=parsed["trip_style"],
    )
    trace.append("Step 7 → generated travel guide")

    map_path = generate_map(itinerary)
    trace.append("Step 8 → generated interactive map")

    return {
        "parsed_request": parsed,
        "city_info": city_info,
        "weather_summary": weather,
        "raw_plan": itinerary,
        "travel_guide": travel_guide,
        "map": map_path,
        "trace": trace,
    }
