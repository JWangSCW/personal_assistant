import folium

LOCATIONS = {
    "Colosseum": (41.8902, 12.4922),
    "Roman Forum": (41.8925, 12.4853),
    "Pantheon": (41.8986, 12.4769),
    "Trevi Fountain": (41.9009, 12.4833),
    "Vatican Museums": (41.9065, 12.4536),
}

def generate_map(itinerary: dict) -> str:
    travel_map = folium.Map(location=[41.9, 12.49], zoom_start=13)

    for day, places in itinerary.items():
        for place in places:
            if place in LOCATIONS:
                folium.Marker(
                    location=LOCATIONS[place],
                    popup=f"{day}: {place}"
                ).add_to(travel_map)

    output_file = "trip_map.html"
    travel_map.save(output_file)
    return output_file