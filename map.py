import json
from pathlib import Path
import folium

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def load_coordinates():
    with open(DATA_DIR / "coordinates.json", "r", encoding="utf-8") as f:
        return json.load(f)


def generate_map(itinerary: dict) -> str:
    locations = load_coordinates()
    points = []

    for day, places in itinerary.items():
        for place in places:
            if place in locations:
                lat, lon = locations[place]
                points.append((day, place, lat, lon))

    if points:
        avg_lat = sum(p[2] for p in points) / len(points)
        avg_lon = sum(p[3] for p in points) / len(points)
        travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
    else:
        travel_map = folium.Map(location=[48.8566, 2.3522], zoom_start=12)

    for day, place, lat, lon in points:
        folium.Marker(
            location=[lat, lon],
            popup=f"{day}: {place}"
        ).add_to(travel_map)

    output_file = "trip_map.html"
    travel_map.save(output_file)
    return output_file