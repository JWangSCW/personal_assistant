import folium


def generate_map(itinerary: dict) -> str:
    points = []

    for day, places in itinerary.items():
        for place in places:
            lat = place.get("lat")
            lon = place.get("lon")
            name = place.get("name")
            if lat is not None and lon is not None and name:
                points.append((day, name, lat, lon))

    if points:
        avg_lat = sum(p[2] for p in points) / len(points)
        avg_lon = sum(p[3] for p in points) / len(points)
        travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)
    else:
        travel_map = folium.Map(location=[48.8566, 2.3522], zoom_start=12)

    for day, name, lat, lon in points:
        folium.Marker(
            location=[lat, lon],
            popup=f"{day}: {name}"
        ).add_to(travel_map)

    output_file = "trip_map.html"
    travel_map.save(output_file)
    return output_file