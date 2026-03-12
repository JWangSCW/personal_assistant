from tools import search_attractions, search_restaurants, build_itinerary

def travel_agent(city: str):

    attractions = search_attractions(city)
    restaurants = search_restaurants(city)

    itinerary = build_itinerary(attractions, restaurants)

    return {
        "city": city,
        "itinerary": itinerary
    }