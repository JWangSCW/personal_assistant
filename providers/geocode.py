import requests


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_city(city: str) -> dict:
    response = requests.get(
        GEOCODE_URL,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=20,
    )
    data = response.json()

    if response.status_code != 200:
        raise RuntimeError(f"Geocoding error: status={response.status_code}, body={data}")

    results = data.get("results", [])
    if not results:
        raise ValueError(f"City not found: {city}")

    item = results[0]
    return {
        "name": item["name"],
        "country": item.get("country", ""),
        "latitude": item["latitude"],
        "longitude": item["longitude"],
    }


def normalize_place_name(place_name: str) -> list[str]:
    base = (place_name or "").strip()
    if not base:
        return []

    variants = [base]

    if base.lower().startswith("the "):
        variants.append(base[4:])

    deduped = []
    for value in variants:
        value = value.strip()
        if value and value not in deduped:
            deduped.append(value)

    return deduped


def geocode_place(place_name: str, city: str) -> dict | None:
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "travel-agent-demo/1.0"}

    name_variants = normalize_place_name(place_name)

    queries = []
    for name in name_variants:
        queries.append(f"{name}, {city}")
    for name in name_variants:
        queries.append(name)

    seen = set()
    for query in queries:
        if query in seen:
            continue
        seen.add(query)

        try:
            response = requests.get(
                url,
                params={
                    "q": query,
                    "format": "json",
                    "limit": 1,
                },
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            if data:
                top = data[0]
                return {
                    "lat": float(top["lat"]),
                    "lon": float(top["lon"]),
                    "address": top.get("display_name", ""),
                }

        except Exception as e:
            print(f"geocode_place failed for {query}: {e}")
            continue

    return None