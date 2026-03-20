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

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "604800"))  # 7 days
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))  # 1 hour
TRIP_CACHE_TTL_SECONDS = int(os.getenv("TRIP_CACHE_TTL_SECONDS", "3600"))  # 1 hour
LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))  # 1 hour

redis_client = None
REDIS_AVAILABLE = False


def _safe_json_loads(data, default):
    if not data:
        return default

    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


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


# =========================
# LLM + Trip Cache
# =========================

def save_trip(city, itinerary):
    if not REDIS_AVAILABLE:
        return

    redis_client.set(
        f"trip:{city.lower()}",
        json.dumps(itinerary),
        ex=TRIP_CACHE_TTL_SECONDS,
    )


def load_trip(city):
    if not REDIS_AVAILABLE:
        return None

    data = redis_client.get(f"trip:{city.lower()}")
    return _safe_json_loads(data, None)


def cache_llm_response(key, value, ttl=LLM_CACHE_TTL_SECONDS):
    if not REDIS_AVAILABLE:
        return

    redis_client.set(
        f"llm:{key}",
        json.dumps(value),
        ex=ttl,
    )


def get_llm_cache(key):
    if not REDIS_AVAILABLE:
        return None

    data = redis_client.get(f"llm:{key}")
    return _safe_json_loads(data, None)


# =========================
# JOB SYSTEM (核心修改点)
# =========================

def create_job(payload: dict) -> str:
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    job_id = str(uuid.uuid4())
    job_key = f"job:{job_id}"

    job_data = {
        "status": payload.get("status", "pending"),
        "created_at": datetime.utcnow().isoformat(),
        "payload": payload,
        "result": None,
        "error": None,
        "current_step": payload.get("current_step"),
        "steps": payload.get("steps", []),
        "session_id": payload.get("session_id"),
    }

    redis_client.set(job_key, json.dumps(job_data), ex=JOB_TTL_SECONDS)
    return job_id


def get_job(job_id: str):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    data = redis_client.get(f"job:{job_id}")
    if not data:
        return None

    return _safe_json_loads(data, None)


def update_job(job_id: str, **fields):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    job_key = f"job:{job_id}"
    existing = redis_client.get(job_key)

    if not existing:
        return None

    job_data = _safe_json_loads(existing, None)
    if not job_data:
        return None

    job_data.update(fields)

    redis_client.set(job_key, json.dumps(job_data), ex=JOB_TTL_SECONDS)
    return job_data


# =========================
# SESSION MANAGEMENT
# =========================

def _session_preferences_key(session_id: str) -> str:
    return f"session:{session_id}:preferences"


def _session_trip_result_key(session_id: str) -> str:
    return f"session:{session_id}:trip_result"


def get_session_preferences(session_id: str) -> dict:
    if not REDIS_AVAILABLE:
        return {}

    data = redis_client.get(_session_preferences_key(session_id))
    return _safe_json_loads(data, {})


def save_session_preferences(session_id: str, preferences: dict):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    redis_client.set(
        _session_preferences_key(session_id),
        json.dumps(preferences),
        ex=SESSION_TTL_SECONDS,
    )


def merge_session_preferences(session_id: str, new_preferences: dict) -> dict:
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    current = get_session_preferences(session_id)
    merged = {**current, **new_preferences}

    redis_client.set(
        _session_preferences_key(session_id),
        json.dumps(merged),
        ex=SESSION_TTL_SECONDS,
    )
    return merged


def save_session_trip_result(session_id: str, result: dict):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    redis_client.set(
        _session_trip_result_key(session_id),
        json.dumps(result),
        ex=SESSION_TTL_SECONDS,
    )


def get_session_trip_result(session_id: str) -> dict | None:
    if not REDIS_AVAILABLE:
        return None

    data = redis_client.get(_session_trip_result_key(session_id))
    return _safe_json_loads(data, None)


def clear_session_trip_result(session_id: str):
    if not REDIS_AVAILABLE:
        raise RuntimeError("Redis unavailable")

    redis_client.delete(_session_trip_result_key(session_id))