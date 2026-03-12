from workflow import create_workflow
from map import generate_map
from memory import save_trip

workflow = create_workflow()


def travel_agent(city: str):
    result = workflow.invoke({
        "city": city,
        "attractions": [],
        "restaurants": [],
        "itinerary": {},
        "travel_guide": "",
        "trace": ["Step 0 → analysing user request"]
    })

    itinerary = result["itinerary"]

    save_trip(city, itinerary)
    map_path = generate_map(itinerary)

    trace = result["trace"] + ["Step 5 → generating interactive map"]

    return {
        "city": city,
        "raw_plan": itinerary,
        "travel_guide": result["travel_guide"],
        "map": map_path,
        "trace": trace
    }