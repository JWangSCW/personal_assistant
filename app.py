from typing import Optional
from fastapi import FastAPI, HTTPException
from agent import travel_agent_v2

app = FastAPI()


@app.get("/plan-trip")
def plan_trip(query: Optional[str] = None):
    if not query:
        raise HTTPException(status_code=400, detail="Please provide 'query'.")

    return travel_agent_v2(query)