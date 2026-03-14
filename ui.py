import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL")

st.title("🌍 AI Travel Planner Agent v2")

query = st.text_input(
    "Describe your trip",
    "Plan a 2-day romantic trip in Paris with museums and wine bars"
)

if st.button("Plan my trip"):
    with st.spinner("Agent is planning your trip..."):
        try:
            response = requests.get(API_URL, params={"query": query}, timeout=120)
        except Exception:
            st.error("API server is not reachable. Start FastAPI first.")
            st.stop()

        if response.status_code != 200:
            st.error(f"Agent failed: {response.text}")
        else:
            data = response.json()

            st.subheader("🧩 Parsed Request")
            st.json(data["parsed_request"])

            st.subheader("🌦 Weather Summary")
            st.json(data["weather_summary"])

            st.subheader("📍 Itinerary")
            for day, places in data["raw_plan"].items():
                st.write(f"**{day}**")
                for p in places:
                    st.write("-", p["name"])

            st.subheader("🧠 Travel Guide")
            st.write(data["travel_guide"])

            st.subheader("🧭 Agent Reasoning")
            for step in data["trace"]:
                st.write(step)

            st.subheader("🗺 Travel Map")
            if data.get("map_html"):
                st.components.v1.html(data["map_html"], height=500)
            else:
                st.warning("Map is unavailable for this request.")
