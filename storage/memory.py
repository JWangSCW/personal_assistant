import os
import json
import redis
import tempfile
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_TLS = os.getenv("REDIS_TLS", "false").lower() == "true"
REDIS_CA_CERT = os.getenv("REDIS_CA_CERT", "")

redis_client = None
REDIS_AVAILABLE = False


def _build_redis_client():
    kwargs = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "username": REDIS_USERNAME or None,
        "password": REDIS_PASSWORD or None,
        "db": REDIS_DB,
        "decode_responses": True,
        "socket_connect_timeout": 2,
    }

    if REDIS_TLS:
        kwargs["ssl"] = True

        if REDIS_CA_CERT:
            cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
            cert_file.write(REDIS_CA_CERT.encode("utf-8"))
            cert_file.flush()
            cert_file.close()
            kwargs["ssl_ca_certs"] = cert_file.name

    return redis.Redis(**kwargs)


if REDIS_HOST:
    try:
        redis_client = _build_redis_client()
        redis_client.ping()
        REDIS_AVAILABLE = True
    except Exception as e:
        print(f"Redis unavailable: {e}")
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

def create_job(payload: dict) -> str:
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    job_id = str(uuid.uuid4())
    job_key = f"job:{job_id}"

    job_data = {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "payload": payload,
        "result": None,
        "error": None,
    }

    redis_client.set(job_key, json.dumps(job_data), ex=3600)
    return job_id


def get_job(job_id: str):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    data = redis_client.get(f"job:{job_id}")
    if not data:
        return None
    return json.loads(data)


def update_job(job_id: str, **fields):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    job_key = f"job:{job_id}"
    existing = redis_client.get(job_key)

    if not existing:
        return None

    job_data = json.loads(existing)
    job_data.update(fields)

    redis_client.set(job_key, json.dumps(job_data), ex=3600)
    return job_data

