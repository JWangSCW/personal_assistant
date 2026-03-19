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


TRIP_STYLE_PROFILES = {
    "food": {
        "restaurant_keywords": ["restaurant", "cafe", "bakery", "bar", "pub", "food"],
        "attraction_keywords": ["market", "street", "historic", "garden", "waterfront"],
        "max_restaurants": 8,
        "max_attractions": 4,
    },
    "chill": {
        "restaurant_keywords": ["cafe", "bakery", "tea", "restaurant"],
        "attraction_keywords": ["park", "garden", "viewpoint", "leisure", "river", "scenic"],
        "max_restaurants": 4,
        "max_attractions": 6,
    },
    "party": {
        "restaurant_keywords": ["bar", "pub", "restaurant", "cafe"],
        "attraction_keywords": ["nightclub", "club", "nightlife", "music", "entertainment"],
        "max_restaurants": 6,
        "max_attractions": 4,
    },
    "romantic": {
        "restaurant_keywords": ["restaurant", "cafe", "wine", "bar"],
        "attraction_keywords": ["viewpoint", "garden", "park", "scenic", "historic"],
        "max_restaurants": 6,
        "max_attractions": 4,
    },
    "family": {
        "restaurant_keywords": ["restaurant", "cafe", "bakery"],
        "attraction_keywords": ["park", "zoo", "museum", "garden", "playground", "family"],
        "max_restaurants": 4,
        "max_attractions": 6,
    },
    "culture": {
        "restaurant_keywords": ["cafe", "restaurant"],
        "attraction_keywords": ["museum", "historic", "monument", "art", "heritage", "architecture"],
        "max_restaurants": 4,
        "max_attractions": 6,
    },
    "general": {
        "restaurant_keywords": ["restaurant", "cafe", "bakery"],
        "attraction_keywords": ["attraction", "historic", "park", "museum"],
        "max_restaurants": 5,
        "max_attractions": 5,
    },
}


def build_candidate_pool(
    attractions: list[dict],
    restaurants: list[dict],
    trip_style: str = "general",
) -> dict:
    profile = TRIP_STYLE_PROFILES.get(trip_style, TRIP_STYLE_PROFILES["general"])

    prioritized_restaurants = _deduplicate_items(
        _pick_by_keywords(restaurants, profile["restaurant_keywords"]) + restaurants
    )[: profile["max_restaurants"]]

    prioritized_attractions = _deduplicate_items(
        _pick_by_keywords(attractions, profile["attraction_keywords"]) + attractions
    )[: profile["max_attractions"]]

    return {
        "restaurants": prioritized_restaurants,
        "attractions": prioritized_attractions,
    }