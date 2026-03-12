from fastapi import FastAPI
from agent import travel_agent

app = FastAPI()


@app.get("/plan-trip")
def plan_trip(city: str):
    return travel_agent(city)