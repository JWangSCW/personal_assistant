from langgraph.graph import StateGraph
from typing import TypedDict

from tools import search_attractions, search_restaurants, build_itinerary
from llm import format_itinerary_with_llm


class TravelState(TypedDict):
    city: str
    attractions: list
    restaurants: list
    itinerary: dict
    travel_guide: str
    trace: list


def search_attractions_node(state: TravelState):
    attractions = search_attractions(state["city"])
    trace = state["trace"] + ["Step 1 → searching attractions"]
    return {"attractions": attractions, "trace": trace}


def search_restaurants_node(state: TravelState):
    restaurants = search_restaurants(state["city"])
    trace = state["trace"] + ["Step 2 → searching restaurants"]
    return {"restaurants": restaurants, "trace": trace}


def build_itinerary_node(state: TravelState):
    itinerary = build_itinerary(state["attractions"], state["restaurants"])
    trace = state["trace"] + ["Step 3 → building itinerary"]
    return {"itinerary": itinerary, "trace": trace}


def generate_guide_node(state: TravelState):
    guide = format_itinerary_with_llm(state["city"], state["itinerary"])
    trace = state["trace"] + ["Step 4 → generating travel guide"]
    return {"travel_guide": guide, "trace": trace}


def create_workflow():
    workflow = StateGraph(TravelState)

    workflow.add_node("search_attractions", search_attractions_node)
    workflow.add_node("search_restaurants", search_restaurants_node)
    workflow.add_node("build_itinerary", build_itinerary_node)
    workflow.add_node("generate_guide", generate_guide_node)

    workflow.set_entry_point("search_attractions")
    workflow.add_edge("search_attractions", "search_restaurants")
    workflow.add_edge("search_restaurants", "build_itinerary")
    workflow.add_edge("build_itinerary", "generate_guide")
    workflow.set_finish_point("generate_guide")

    return workflow.compile()