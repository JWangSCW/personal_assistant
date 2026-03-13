import json
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename: str):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def search_attractions(city: str) -> List[str]:
    attractions = load_json("attractions.json")
    return attractions.get(city.lower(), [])


def search_restaurants(city: str) -> List[str]:
    restaurants = load_json("restaurants.json")
    return restaurants.get(city.lower(), [])


def build_itinerary(attractions: List[str], restaurants: List[str]) -> dict:
    if len(attractions) < 5 or len(restaurants) < 3:
        return {
            "Day 1": attractions[:2] + restaurants[:1],
            "Day 2": attractions[2:4] + restaurants[1:2],
            "Day 3": attractions[4:5] + restaurants[2:3]
        }

    return {
        "Day 1": [attractions[0], attractions[1], restaurants[0]],
        "Day 2": [attractions[2], attractions[3], restaurants[1]],
        "Day 3": [attractions[4], restaurants[2]]
    }