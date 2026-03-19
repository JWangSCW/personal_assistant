import time
from storage.memory import get_job, update_job, redis_client, get_session_preferences
from app import travel_agent_v2

def find_pending_job():
    keys = redis_client.keys("job:*")
    for key in keys:
        job = get_job(key.split(":")[1])
        if job["status"] == "pending":
            return key.split(":")[1], job
    return None, None


def worker_loop():
    while True:
        job_id, job = find_pending_job()

        if not job_id:
            time.sleep(1)
            continue

        query = job["payload"]["query"]
        session_id = job["payload"].get("session_id", "anonymous")
        preferences = get_session_preferences(session_id)
        print(f"[worker] session_id={session_id}")
        print(f"[worker] preferences={preferences}")

        try:
            update_job(job_id, status="running")
            result = travel_agent_v2(query, session_preferences=preferences)
            result["session_preferences"] = preferences

            update_job(
                job_id,
                status="completed",
                result=result,
                session_id=session_id,
            )

        except Exception as e:
            update_job(job_id, status="failed", error=str(e))


if __name__ == "__main__":
    worker_loop()