import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/plan-trip"

st.title("🌍 AI Travel Planner Agent")

query = st.text_input(
    "Describe your trip",
    "Plan a 3-day trip to Rome with food and history"
)

if st.button("Plan my trip"):

    with st.spinner("Agent is planning your trip..."):

        response = requests.get(API_URL, params={"query": query})

        if response.status_code != 200:
            st.error("Agent failed to generate trip")
        else:
            data = response.json()

            st.subheader("📍 Itinerary")

            for day, places in data["raw_plan"].items():
                st.write(f"**{day}**")
                for p in places:
                    st.write("-", p)

            st.subheader("🧠 Travel Guide")

            st.write(data["travel_guide"])

            st.subheader("🧭 Agent Reasoning")

            for step in data["trace"]:
                st.write(step)

            st.subheader("🗺 Travel Map")

            with open(data["map"], "r") as f:
                html_map = f.read()

            st.components.v1.html(html_map, height=500)