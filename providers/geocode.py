import hashlib
import time
import requests

from storage.memory import redis_client, REDIS_AVAILABLE


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GEOCODE_PLACE_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days
GEOCODE_MIN_INTERVAL_SECONDS = 1.1


_last_geocode_request_ts = 0.0


def _rate_limit_geocode():
    global _last_geocode_request_ts

    now = time.time()
    elapsed = now - _last_geocode_request_ts

    if elapsed < GEOCODE_MIN_INTERVAL_SECONDS:
        time.sleep(GEOCODE_MIN_INTERVAL_SECONDS - elapsed)

    _last_geocode_request_ts = time.time()


def _place_cache_key(place_name: str, city: str) -> str:
    raw = f"{(place_name or '').strip().lower()}::{(city or '').strip().lower()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"geocode:place:{digest}"


def _get_cached_place(place_name: str, city: str) -> dict | None:
    if not REDIS_AVAILABLE:
        return None

    key = _place_cache_key(place_name, city)
    data = redis_client.get(key)
    if not data:
        return None

    try:
        import json
        return json.loads(data)
    except Exception:
        return None


def _set_cached_place(place_name: str, city: str, value: dict):
    if not REDIS_AVAILABLE:
        return

    key = _place_cache_key(place_name, city)

    try:
        import json
        redis_client.set(
            key,
            json.dumps(value),
            ex=GEOCODE_PLACE_CACHE_TTL_SECONDS,
        )
    except Exception:
        pass


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
    headers = {"User-Agent": "travel-agent-demo/1.0"}

    cached = _get_cached_place(place_name, city)
    if cached:
        return cached

    name_variants = normalize_place_name(place_name)

    if not name_variants:
        return None

    # 先只保留最稳的一轮查询，避免请求量翻倍
    queries = [f"{name}, {city}" for name in name_variants]

    seen = set()

    for query in queries:
        if query in seen:
            continue
        seen.add(query)

        try:
            _rate_limit_geocode()

            response = requests.get(
                NOMINATIM_URL,
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
                result = {
                    "lat": float(top["lat"]),
                    "lon": float(top["lon"]),
                    "address": top.get("display_name", ""),
                }
                _set_cached_place(place_name, city, result)
                return result

        except Exception as e:
            print(f"geocode_place failed for {query}: {e}")
            continue

    return None