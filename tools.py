from typing import List

def search_attractions(city: str) -> List[str]:
    attractions = {
        "rome": [
            "Colosseum",
            "Roman Forum",
            "Pantheon",
            "Trevi Fountain",
            "Vatican Museums"
        ],
        "paris": [
            "Eiffel Tower",
            "Louvre Museum",
            "Notre Dame",
            "Montmartre",
            "Seine River"
        ]
    }

    return attractions.get(city.lower(), [])


def search_restaurants(city: str) -> List[str]:
    restaurants = {
        "rome": [
            "Roscioli",
            "Armando al Pantheon",
            "Da Enzo",
            "Pizzarium"
        ],
        "paris": [
            "Le Comptoir",
            "Septime",
            "Frenchie",
            "Chez Janou"
        ]
    }

    return restaurants.get(city.lower(), [])


def build_itinerary(attractions, restaurants):

    itinerary = {
        "Day 1": [attractions[0], attractions[1], restaurants[0]],
        "Day 2": [attractions[2], attractions[3], restaurants[1]],
        "Day 3": [attractions[4], restaurants[2]]
    }

    return itinerary