import time
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _build_address(tags: dict) -> str:
    parts = [
        tags.get("addr:housenumber", ""),
        tags.get("addr:street", ""),
        tags.get("addr:city", ""),
    ]
    return " ".join([p for p in parts if p]).strip()


def _deduplicate_places(places: list[dict]) -> list[dict]:
    seen = set()
    deduped = []

    for place in places:
        key = (
            place["name"].strip().lower(),
            round(place["lat"], 5),
            round(place["lon"], 5),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(place)

    return deduped


def _normalize_overpass_elements(elements: list[dict]) -> list[dict]:
    normalized = []

    for item in elements:
        tags = item.get("tags", {})
        name = tags.get("name")

        if item.get("type") == "node":
            lat = item.get("lat")
            lon = item.get("lon")
        else:
            center = item.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")

        if not name or lat is None or lon is None:
            continue

        normalized.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "address": _build_address(tags),
            "tags": tags,
        })

    return _deduplicate_places(normalized)


def _run_overpass_query(query: str) -> list[dict]:
    headers = {"User-Agent": "travel-agent-demo/1.0"}
    backoffs = [1, 3, 5]

    for attempt, wait_s in enumerate(backoffs, start=1):
        try:
            response = requests.post(
                OVERPASS_URL,
                data=query.encode("utf-8"),
                timeout=60,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                elements = data.get("elements", [])
                return _normalize_overpass_elements(elements)

            if response.status_code in (429, 504):
                print(
                    f"Overpass transient error on attempt {attempt}: "
                    f"status={response.status_code}, body={response.text[:300]}"
                )
                time.sleep(wait_s)
                continue

            print(
                f"Overpass non-retryable error: "
                f"status={response.status_code}, body={response.text[:300]}"
            )
            return []

        except requests.RequestException as e:
            print(f"Overpass request exception on attempt {attempt}: {e}")
            time.sleep(wait_s)
            continue
        except ValueError as e:
            print(f"Overpass JSON decode error on attempt {attempt}: {e}")
            return []

    print("Overpass query failed after retries, returning empty POI list.")
    return []


def score_poi(poi: dict) -> int:
    tags = poi.get("tags", {})
    score = 0

    if "tourism" in tags:
        score += 3

    if tags.get("amenity") == "restaurant":
        score += 2

    if tags.get("amenity") == "cafe":
        score += 2

    if tags.get("amenity") in ["bar", "pub"]:
        score += 2

    if tags.get("shop") == "bakery":
        score += 2

    if tags.get("historic"):
        score += 2

    if tags.get("leisure") == "park":
        score += 2

    return score


def _build_attractions_query(lat: float, lon: float, radius_m: int = 3000) -> str:
    return f"""
[out:json][timeout:25];
(
  node["tourism"="attraction"](around:{radius_m},{lat},{lon});
  node["tourism"="museum"](around:{radius_m},{lat},{lon});
  node["historic"](around:{radius_m},{lat},{lon});
  node["leisure"="park"](around:{radius_m},{lat},{lon});
  way["tourism"="attraction"](around:{radius_m},{lat},{lon});
  way["tourism"="museum"](around:{radius_m},{lat},{lon});
  way["historic"](around:{radius_m},{lat},{lon});
  way["leisure"="park"](around:{radius_m},{lat},{lon});
);
out center;
"""


def _build_restaurants_query(lat: float, lon: float, interests: list[str], radius_m: int = 2500) -> str:
    interests_lower = [x.lower() for x in interests]

    parts = [
        f'node["amenity"="restaurant"](around:{radius_m},{lat},{lon});',
        f'way["amenity"="restaurant"](around:{radius_m},{lat},{lon});',
    ]

    if any(x in interests_lower for x in ["food", "bakery", "cafes", "cafe", "coffee"]):
        parts.extend([
            f'node["amenity"="cafe"](around:{radius_m},{lat},{lon});',
            f'way["amenity"="cafe"](around:{radius_m},{lat},{lon});',
            f'node["shop"="bakery"](around:{radius_m},{lat},{lon});',
            f'way["shop"="bakery"](around:{radius_m},{lat},{lon});',
        ])

    if any(x in interests_lower for x in ["wine bars", "nightlife", "romantic", "bars", "wine", "party", "hangover"]):
        parts.extend([
            f'node["amenity"="bar"](around:{radius_m},{lat},{lon});',
            f'way["amenity"="bar"](around:{radius_m},{lat},{lon});',
            f'node["amenity"="pub"](around:{radius_m},{lat},{lon});',
            f'way["amenity"="pub"](around:{radius_m},{lat},{lon});',
        ])

    parts_str = "\n  ".join(parts)

    return f"""
[out:json][timeout:25];
(
  {parts_str}
);
out center;
"""


def fetch_attractions(lat: float, lon: float) -> list[dict]:
    query = _build_attractions_query(lat, lon)
    pois = _run_overpass_query(query)
    pois.sort(key=score_poi, reverse=True)
    return pois[:25]


def fetch_restaurants(lat: float, lon: float, interests: list[str] | None = None) -> list[dict]:
    interests = interests or []
    query = _build_restaurants_query(lat, lon, interests)
    pois = _run_overpass_query(query)

    interests_lower = [i.lower() for i in interests]

    if any(x in interests_lower for x in ["food", "bakery", "cafe", "coffee"]):
        preferred = []
        others = []

        for poi in pois:
            tags = poi.get("tags", {})
            if tags.get("amenity") in ["restaurant", "cafe"] or tags.get("shop") == "bakery":
                preferred.append(poi)
            else:
                others.append(poi)

        pois = preferred + others

    elif any(x in interests_lower for x in ["nightlife", "wine", "wine bars", "bars", "party", "hangover"]):
        preferred = []
        others = []

        for poi in pois:
            tags = poi.get("tags", {})
            if tags.get("amenity") in ["bar", "pub"]:
                preferred.append(poi)
            else:
                others.append(poi)

        pois = preferred + others

    pois.sort(key=score_poi, reverse=True)
    return pois[:25]