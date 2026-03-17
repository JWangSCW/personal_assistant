import os
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "").rstrip("/")

st.set_page_config(page_title="AI Travel Planner Agent v2", layout="wide")
st.title("🌍 AI Travel Planner Agent")

query = st.text_input(
    "Describe your trip",
    "Plan a 2-day romantic trip in Paris with museums and wine bars"
)

if st.button("Plan my trip"):
    if not API_URL:
        st.error("API_URL is not configured.")
        st.stop()

    job_submit_url = f"{API_URL}/plan-trip"

    try:
        submit_response = requests.post(
            job_submit_url,
            params={"query": query},
            timeout=15,
        )
    except Exception:
        st.error("API server is not reachable. Start FastAPI first.")
        st.stop()

    if submit_response.status_code != 200:
        st.error(f"Agent failed to submit job: {submit_response.text}")
        st.stop()

    submit_data = submit_response.json()
    job_id = submit_data["job_id"]

    st.success(f"Trip request submitted. Job ID: {job_id}")

    status_box = st.empty()
    result_box = st.empty()

    job_status_url = f"{API_URL}/jobs/{job_id}"

    with st.spinner("Agent is planning your trip...", show_time=True):
        max_polls = 90

        for _ in range(max_polls):
            try:
                job_response = requests.get(job_status_url, timeout=15)
            except Exception as e:
                status_box.error(f"Failed to fetch job status: {e}")
                st.stop()

            if job_response.status_code != 200:
                status_box.error(f"Failed to fetch job status: {job_response.text}")
                st.stop()

            job_data = job_response.json()
            status = job_data.get("status", "unknown")

            if status == "pending":
                status_box.info("Job submitted. Waiting for worker...")
            elif status == "running":
                status_box.info("Worker is generating your itinerary...")
            elif status == "failed":
                status_box.error(f"❌ Job failed: {job_data.get('error', 'unknown error')}")
                st.stop()
            elif status == "completed":
                status_box.success("✅ Trip ready!")

                data = job_data.get("result", {})

                with result_box.container():
                    st.subheader("Parsed Request")
                    st.json(data.get("parsed_request", {}))

                    st.subheader("Weather Summary")
                    st.json(data.get("weather_summary", {}))

                    st.subheader("Itinerary")
                    for day, places in data.get("raw_plan", {}).items():
                        st.write(f"**{day}**")
                        for p in places:
                            st.write("-", p["name"])

                    st.subheader("Travel Guide")
                    st.write(data.get("travel_guide", ""))

                    st.subheader("Agent Reasoning")
                    for step in data.get("trace", []):
                        st.write(step)

                    st.subheader("Travel Map")
                    if data.get("map_html"):
                        st.components.v1.html(data["map_html"], height=500)
                    else:
                        st.warning("Map is unavailable for this request.")

                break

            time.sleep(1)
        else:
            status_box.warning("⌛ Job is still running. Please try again in a moment.")