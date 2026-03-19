import os
import time
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "").rstrip("/")


def get_weather_icon(code: int) -> str:
    if code == 0:
        return "☀️"
    elif code in [1, 2]:
        return "🌤️"
    elif code == 3:
        return "☁️"
    elif code in [45, 48]:
        return "🌫️"
    elif code in [51, 53, 55]:
        return "🌦️"
    elif code in [61, 63, 65]:
        return "🌧️"
    elif code in [71, 73, 75]:
        return "❄️"
    elif code in [95]:
        return "⛈️"
    return "🌍"


st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="🌍",
    layout="wide",
)

# ---------- session state ----------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "latest_session_preferences" not in st.session_state:
    st.session_state.latest_session_preferences = {}

if "latest_parsed_request" not in st.session_state:
    st.session_state.latest_parsed_request = {}

if "latest_weather_summary" not in st.session_state:
    st.session_state.latest_weather_summary = {}

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "current_job_id" not in st.session_state:
    st.session_state.current_job_id = None

if "current_job_status" not in st.session_state:
    st.session_state.current_job_status = None

session_id = st.session_state.session_id

# ---------- header ----------
st.markdown(
    """
<div style="padding: 10px 0 20px 0">
    <h1 style="margin-bottom:0">🌍 AI Travel Planner</h1>
    <p style="color: #9aa0a6; font-size:14px; margin-top:8px;">
        Plan smarter trips with AI — personalized, contextual, and instant.
    </p>
    <p style="font-size:12px; color:#6b7280; margin-top:4px;">
        🚀 Powered by Scaleway — Generative AI • Kubernetes • Redis
    </p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("⚙️ How it works"):
    st.markdown(
        """
- User intent is parsed and normalized with LLM
- Session memory is stored in Redis
- Async orchestration runs on Kapsule
- Itineraries are generated with Scaleway Generative API
- Locations are geocoded for map rendering
"""
    )

st.divider()

# ---------- sidebar ----------
with st.sidebar:
    st.header("Trip Context")

    st.subheader("Session")
    st.code(session_id[:8], language=None)

    st.subheader("Session Memory")
    st.caption("Stored preferences from previous interactions.")

    if st.session_state.latest_session_preferences:
        prefs = st.session_state.latest_session_preferences
        prefs_style = prefs.get("travel_style", "—")
        prefs_interests = ", ".join(prefs.get("interests", [])) or "—"
        prefs_pace = prefs.get("pace", "—")

        st.markdown(
            f"""
**Style:** {prefs_style}  
**Interests:** {prefs_interests}  
**Pace:** {prefs_pace}
"""
        )
    else:
        st.info("No saved preferences for this session yet.")

    st.subheader("Trip Overview")
    if st.session_state.latest_parsed_request:
        parsed = st.session_state.latest_parsed_request
        req_city = parsed.get("city", "—")
        req_days = parsed.get("duration_days", "—")
        req_style = parsed.get("trip_style", "—")
        req_interests = ", ".join(parsed.get("interests", [])) or "—"

        st.markdown(
            f"""
**Destination:** {req_city}  
**Duration:** {req_days} days  
**Style:** {req_style}  
**Interests:** {req_interests}
"""
        )
    else:
        st.caption("Trip details will appear here after generation.")

    st.subheader("Weather Forecast")
    daily = st.session_state.latest_weather_summary.get("daily", [])

    if daily:
        weather_cols = st.columns(len(daily))
        for i, day in enumerate(daily):
            icon = get_weather_icon(day.get("weather_code", 0))
            temp_min = day.get("temp_min", "")
            temp_max = day.get("temp_max", "")
            date = day.get("date", "")

            with weather_cols[i]:
                st.markdown(
                    f"""
<div style="text-align:center; padding:8px 4px; border:1px solid rgba(250,250,250,0.08); border-radius:12px;">
    <div style="font-size:11px; color:#9aa0a6;">{date}</div>
    <div style="font-size:24px; margin:4px 0;">{icon}</div>
    <div style="font-size:12px;">{temp_min}° → {temp_max}°</div>
</div>
""",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Weather will appear here after generation.")

# ---------- input ----------
with st.container():
    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "Describe your trip",
            "Plan a 2-day food trip in Paris with local restaurants",
        )

    with col2:
        st.markdown("### Session")
        st.code(session_id[:8], language=None)

st.divider()

# ---------- submit ----------
if st.button("✨ Plan my trip", use_container_width=True):
    if not API_URL:
        st.error("API_URL is not configured.")
        st.stop()

    try:
        submit_response = requests.post(
            f"{API_URL}/plan-trip",
            params={
                "query": query,
                "session_id": session_id,
            },
            timeout=15,
        )
    except Exception:
        st.error("API server is not reachable. Start FastAPI first.")
        st.stop()

    if submit_response.status_code != 200:
        st.error(f"Agent failed to submit job: {submit_response.text}")
        st.stop()

    submit_data = submit_response.json()
    st.session_state.current_job_id = submit_data["job_id"]
    st.session_state.current_job_status = "pending"
    st.rerun()

# ---------- polling / result ----------
if st.session_state.current_job_id:
    job_id = st.session_state.current_job_id

    top_col1, top_col2, top_col3 = st.columns(3)
    top_col1.metric("Job Status", st.session_state.current_job_status or "pending")
    top_col2.metric("Job ID", job_id[:8])
    top_col3.metric("Session", session_id[:8])

    status_box = st.empty()

    try:
        job_response = requests.get(f"{API_URL}/jobs/{job_id}", timeout=15)
    except Exception as e:
        status_box.error(f"Failed to fetch job status: {e}")
        st.stop()

    if job_response.status_code != 200:
        status_box.error(f"Failed to fetch job status: {job_response.text}")
        st.stop()

    job_data = job_response.json()
    status = job_data.get("status", "unknown")
    st.session_state.current_job_status = status

    if status == "pending":
        status_box.info("⏳ Job submitted. Waiting for worker...")
        time.sleep(1)
        st.rerun()

    elif status == "running":
        status_box.info("⚙️ Worker is generating your itinerary...")
        time.sleep(1)
        st.rerun()

    elif status == "failed":
        status_box.error(f"❌ Job failed: {job_data.get('error', 'unknown error')}")
        st.session_state.current_job_id = None

    elif status == "completed":
        status_box.success("✅ Trip ready!")

        data = job_data.get("result", {})
        parsed_request = data.get("parsed_request", {})
        session_preferences = data.get("session_preferences", {})
        weather_summary = data.get("weather_summary", {})
        raw_plan = data.get("raw_plan", {})
        travel_guide = data.get("travel_guide", "")
        trace = data.get("trace", [])

        # persist for sidebar + main view
        st.session_state.latest_parsed_request = parsed_request
        st.session_state.latest_session_preferences = session_preferences
        st.session_state.latest_weather_summary = weather_summary
        st.session_state.latest_result = data
        st.session_state.current_job_id = None
        st.session_state.current_job_status = None

        st.rerun()

# ---------- render latest result ----------
if st.session_state.latest_result:
    data = st.session_state.latest_result
    parsed_request = data.get("parsed_request", {})
    raw_plan = data.get("raw_plan", {})
    travel_guide = data.get("travel_guide", "")
    trace = data.get("trace", [])

    req_city = parsed_request.get("city", "—")
    req_days = parsed_request.get("duration_days", "—")

    st.success(f"✨ Your {req_days}-day trip in {req_city} is ready!")

    tabs = st.tabs(["📍 Itinerary", "🗺️ Map", "📖 Guide", "🧠 Reasoning"])

    with tabs[0]:
        icon_map = {
            "food": "🍽️",
            "culture": "🎨",
            "party": "🍸",
            "romantic": "❤️",
            "chill": "🌿",
            "family": "👨‍👩‍👧‍👦",
            "llm": "📍",
        }

        for day, places in raw_plan.items():
            st.markdown(f"## {day}")

            for idx, place in enumerate(places, start=1):
                name = place.get("name", "Unknown place")
                address = place.get("address", "")
                tags = place.get("tags", {})
                theme = tags.get("theme") or tags.get("source", "llm")
                icon = icon_map.get(theme, "📍")

                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])

                    with c1:
                        st.markdown(f"### {idx}. {icon} {name}")
                        if address:
                            st.caption(f"📍 {address}")

                    with c2:
                        st.markdown(f"**#{idx}**")
                        st.caption(theme)

    with tabs[1]:
        st.subheader("🗺️ Travel Map")
        if data.get("map_html"):
            st.components.v1.html(data["map_html"], height=500)
        else:
            st.warning("Map is unavailable for this request.")

    with tabs[2]:
        st.markdown(travel_guide)

    with tabs[3]:
        for step in trace:
            st.write(f"• {step}")