from typing import Optional
from fastapi import FastAPI, HTTPException
from agent import travel_agent
from parser import parse_user_request

app = FastAPI()


@app.get("/plan-trip")
def plan_trip(query: Optional[str] = None, city: Optional[str] = None):
    if query:
        parsed_city = parse_user_request(query)
        result = travel_agent(parsed_city)
        result["parsed_city"] = parsed_city
        result["user_query"] = query
        return result

    if city:
        result = travel_agent(city)
        result["parsed_city"] = city
        result["user_query"] = None
        return result

    raise HTTPException(status_code=400, detail="Please provide either 'query' or 'city'.")