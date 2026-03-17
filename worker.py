import time
from storage.memory import get_job, update_job, redis_client
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

        update_job(job_id, status="running")

        try:
            update_job(job_id, status="running")
            result = travel_agent_v2(query)
            update_job(job_id, status="completed", result=result)

        except Exception as e:
            update_job(job_id, status="failed", error=str(e))


if __name__ == "__main__":
    worker_loop()