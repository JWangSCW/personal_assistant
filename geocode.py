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