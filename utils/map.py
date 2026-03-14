import folium


def generate_map_html(itinerary: dict, city_info: dict | None = None) -> str:
    points = []

    for day, places in itinerary.items():
        for place in places:
            lat = place.get("lat")
            lon = place.get("lon")
            name = place.get("name")
            if lat is not None and lon is not None and name:
                points.append((day, name, lat, lon))

    # 优先根据景点坐标生成地图
    if points:
        avg_lat = sum(p[2] for p in points) / len(points)
        avg_lon = sum(p[3] for p in points) / len(points)
        travel_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

        bounds = []

        for day, name, lat, lon in points:
            folium.Marker(
                location=[lat, lon],
                popup=f"{day}: {name}",
                tooltip=name,
            ).add_to(travel_map)
            bounds.append([lat, lon])

        if bounds:
            travel_map.fit_bounds(bounds)

    # 如果 itinerary 里没有点，就退回到城市中心
    elif city_info and city_info.get("latitude") is not None and city_info.get("longitude") is not None:
        travel_map = folium.Map(
            location=[city_info["latitude"], city_info["longitude"]],
            zoom_start=12,
        )

        folium.Marker(
            location=[city_info["latitude"], city_info["longitude"]],
            popup=f"City center: {city_info['name']}",
            tooltip=city_info["name"],
        ).add_to(travel_map)

    # 最后兜底
    else:
        travel_map = folium.Map(location=[48.8566, 2.3522], zoom_start=12)

    return travel_map.get_root().render()