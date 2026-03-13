def _pick_by_keywords(items: list[dict], keywords: list[str]) -> list[dict]:
    picked = []

    for item in items:
        tags = item.get("tags", {})
        text = " ".join(
            [
                item.get("name", ""),
                tags.get("tourism", ""),
                tags.get("amenity", ""),
                tags.get("shop", ""),
                tags.get("leisure", ""),
                tags.get("historic", ""),
            ]
        ).lower()

        if any(k in text for k in keywords):
            picked.append(item)

    return picked


def _deduplicate_items(items: list[dict]) -> list[dict]:
    seen = set()
    result = []

    for item in items:
        key = (
            item.get("name", "").strip().lower(),
            round(item.get("lat", 0), 5),
            round(item.get("lon", 0), 5),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def build_dynamic_itinerary(
    attractions: list[dict],
    restaurants: list[dict],
    duration_days: int,
    trip_style: str = "general",
) -> dict:
    itinerary = {}

    if trip_style == "food":
        food_like = _pick_by_keywords(
            restaurants,
            ["restaurant", "cafe", "bakery", "bar", "pub"]
        )
        scenic_like = _pick_by_keywords(
            attractions,
            ["park", "viewpoint", "historic", "attraction", "museum"]
        )

        pool = _deduplicate_items(food_like + scenic_like + restaurants + attractions)
        stops_per_day = 4

    elif trip_style == "chill":
        chill_like = _pick_by_keywords(
            attractions,
            ["park", "garden", "viewpoint", "leisure", "river", "scenic"]
        )
        cafe_like = _pick_by_keywords(
            restaurants,
            ["cafe", "bakery", "bar", "restaurant"]
        )

        pool = _deduplicate_items(chill_like + cafe_like + attractions + restaurants)
        stops_per_day = 3

    else:
        pool = _deduplicate_items(attractions + restaurants)
        stops_per_day = 4

    index = 0

    for day in range(1, duration_days + 1):
        day_items = []

        for _ in range(stops_per_day):
            if index < len(pool):
                day_items.append(pool[index])
                index += 1

        if day_items:
            itinerary[f"Day {day}"] = day_items

    return itinerary