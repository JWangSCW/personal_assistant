from tools import search_attractions, search_restaurants, build_itinerary
from llm import format_itinerary_with_llm


def travel_agent(city: str):
    attractions = search_attractions(city)
    restaurants = search_restaurants(city)

    if len(attractions) < 5 or len(restaurants) < 3:
        return {
            "city": city,
            "error": "Not enough data available to build the itinerary."
        }

    itinerary = build_itinerary(attractions, restaurants)
    travel_guide = format_itinerary_with_llm(city, itinerary)

    return {
        "city": city,
        "raw_plan": itinerary,
        "travel_guide": travel_guide
    }