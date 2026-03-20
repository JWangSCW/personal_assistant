import folium


def generate_map_html(itinerary: dict, city_info: dict | None = None) -> str:
    all_points = []
    day_points = {}

    for day, places in itinerary.items():
        valid_places = []

        for idx, place in enumerate(places, start=1):
            lat = place.get("lat")
            lon = place.get("lon")
            name = place.get("name")

            if lat is None or lon is None or not name:
                continue

            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue

            point = {
                "day": day,
                "index": idx,
                "name": name,
                "lat": lat,
                "lon": lon,
            }
            valid_places.append(point)
            all_points.append(point)

        if valid_places:
            day_points[day] = valid_places

    print(f"[map] valid_points={len(all_points)}")

    day_colors = [
        "blue",
        "red",
        "green",
        "purple",
        "orange",
        "darkred",
        "cadetblue",
        "darkgreen",
    ]

    if len(all_points) >= 2:
        avg_lat = sum(p["lat"] for p in all_points) / len(all_points)
        avg_lon = sum(p["lon"] for p in all_points) / len(all_points)

        lats = [p["lat"] for p in all_points]
        lons = [p["lon"] for p in all_points]
        bounds = [[p["lat"], p["lon"]] for p in all_points]

        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)

        print(f"[map] lat_range={lat_range}, lon_range={lon_range}")

        # 点很密集：直接用城市中心视角，不按点自动缩放
        if lat_range < 0.03 and lon_range < 0.03:
            if city_info and city_info.get("latitude") is not None and city_info.get("longitude") is not None:
                center_lat = float(city_info["latitude"])
                center_lon = float(city_info["longitude"])
            else:
                center_lat = avg_lat
                center_lon = avg_lon

            travel_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=12,
            )

        # 点比较分散：允许 fit_bounds，但限制最大缩放
        else:
            travel_map = folium.Map(
                location=[avg_lat, avg_lon],
                zoom_start=12,
            )
            travel_map.fit_bounds(bounds, padding=(40, 40), max_zoom=13)

        for point in all_points:
            folium.Marker(
                location=[point["lat"], point["lon"]],
                popup=f"{point['day']} · Stop {point['index']}: {point['name']}",
                tooltip=f"{point['day']} · {point['index']}. {point['name']}",
            ).add_to(travel_map)

        for i, (day, points) in enumerate(day_points.items()):
            if len(points) < 2:
                continue

            color = day_colors[i % len(day_colors)]

            folium.PolyLine(
                locations=[[p["lat"], p["lon"]] for p in points],
                color=color,
                weight=4,
                opacity=0.75,
                tooltip=f"{day} route",
            ).add_to(travel_map)

    elif len(all_points) == 1:
        point = all_points[0]

        if city_info and city_info.get("latitude") is not None and city_info.get("longitude") is not None:
            travel_map = folium.Map(
                location=[float(city_info["latitude"]), float(city_info["longitude"])],
                zoom_start=12,
            )
        else:
            travel_map = folium.Map(
                location=[point["lat"], point["lon"]],
                zoom_start=13,
            )

        folium.Marker(
            location=[point["lat"], point["lon"]],
            popup=f"{point['day']} · Stop {point['index']}: {point['name']}",
            tooltip=f"{point['day']} · {point['index']}. {point['name']}",
        ).add_to(travel_map)

    elif city_info and city_info.get("latitude") is not None and city_info.get("longitude") is not None:
        city_lat = float(city_info["latitude"])
        city_lon = float(city_info["longitude"])

        travel_map = folium.Map(
            location=[city_lat, city_lon],
            zoom_start=12,
        )

        folium.Marker(
            location=[city_lat, city_lon],
            popup=f"City center: {city_info['name']}",
            tooltip=city_info["name"],
        ).add_to(travel_map)

    else:
        travel_map = folium.Map(
            location=[48.8566, 2.3522],
            zoom_start=12,
        )

    return travel_map.get_root().render()