import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_client = None
REDIS_AVAILABLE = False

if REDIS_HOST:
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        redis_client.ping()
        REDIS_AVAILABLE = True
    except Exception:
        redis_client = None
        REDIS_AVAILABLE = False


def save_trip(city, itinerary):
    if not REDIS_AVAILABLE:
        return

    redis_client.set(
        f"trip:{city.lower()}",
        json.dumps(itinerary),
        ex=3600
    )


def load_trip(city):
    if not REDIS_AVAILABLE:
        return None

    data = redis_client.get(f"trip:{city.lower()}")

    if data:
        return json.loads(data)

    return None


def cache_llm_response(key, value, ttl=3600):
    if not REDIS_AVAILABLE:
        return

    redis_client.set(
        f"llm:{key}",
        json.dumps(value),
        ex=ttl
    )


def get_llm_cache(key):
    if not REDIS_AVAILABLE:
        return None

    data = redis_client.get(f"llm:{key}")

    if data:
        return json.loads(data)

    return None
    