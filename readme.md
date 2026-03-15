# AI Travel Agent (LangGraph + Scaleway)

An AI-powered travel planning agent capable of generating **personalized
travel itineraries** using LLM reasoning, geospatial data, and
interactive maps.

The system combines **AI agents, vector search, real-world location
data, and interactive visualization** to dynamically build travel plans
based on user intent.

Example prompt:

    Plan a 2-day romantic trip in Paris with museums and wine bars

The agent will automatically:

-   understand the request
-   discover points of interest
-   generate an itinerary
-   create an interactive travel map

------------------------------------------------------------------------

# Demo Preview

The AI agent can generate a complete travel plan including:

-   itinerary planning
-   attractions and restaurants
-   geospatial map visualization
-   contextual travel recommendations

Example output:

**Day 1** - Louvre Museum - Seine river walk - Wine bar in Le Marais

**Day 2** - Montmartre exploration - Musée d'Orsay - Romantic dinner
near Saint-Germain

All locations are automatically displayed on an interactive map.

------------------------------------------------------------------------

# Architecture Overview

This project demonstrates a **production-style AI agent architecture**.

The system integrates:

-   LLM reasoning
-   agent orchestration
-   real-world geospatial APIs
-   vector search
-   persistent memory

``` mermaid
flowchart TD

    USER[User Query]

    USER --> UI[Streamlit UI]

    UI --> API[FastAPI Backend]

    API --> AGENT[LangGraph Agent]

    AGENT --> PARSER[LLM Query Parser<br>Scaleway Generative API]

    AGENT --> GEO[Geocoding<br>Nominatim / OpenStreetMap]

    AGENT --> POI[POI Search<br>Overpass API]

    AGENT --> VEC[Vector Search<br>Scaleway Embeddings API]

    AGENT --> MEM[Trip Memory<br>Redis]

    AGENT --> LLM[Travel Guide Generator<br>Scaleway Generative API]

    AGENT --> MAP[Interactive Map Generator<br>Leaflet]

    MAP --> UI
```

------------------------------------------------------------------------

# Component Hosting

  Component       Technology                   Hosting
  --------------- ---------------------------- -----------------------
  UI              Streamlit                    Local
  API             FastAPI                      Local
  Agent           LangGraph                    Local
  LLM             Scaleway Generative API      Scaleway
  Embeddings      Scaleway Embeddings API      Scaleway
  POI search      OpenStreetMap Overpass API   External
  Geocoding       Nominatim                    External
  Memory          Redis                        Local / Managed Redis
  Map rendering   Leaflet                      Browser

------------------------------------------------------------------------

# Example Query Execution

Example query:

    Plan a 2-day romantic trip in Paris with museums and wine bars

Execution flow:

1.  User sends query via Streamlit UI
2.  FastAPI forwards the request to the LangGraph agent
3.  The agent parses the query using an LLM
4.  Geocoding service retrieves city coordinates
5.  OpenStreetMap APIs discover relevant attractions and restaurants
6.  The agent builds a structured itinerary
7.  Vector search retrieves contextual knowledge (RAG)
8.  Scaleway LLM generates the travel guide
9.  A map is generated with Leaflet
10. UI renders the itinerary and map

------------------------------------------------------------------------

# Features

## AI Trip Planning

The agent generates itineraries based on:

-   trip duration
-   travel style
-   interests
-   destination

Example prompts:

    Plan a 1-day food trip in Rome
    Plan a museum weekend in Madrid
    Plan a chill trip in Barcelona

------------------------------------------------------------------------

## Dynamic POI Discovery

Attractions and restaurants are discovered dynamically using
**OpenStreetMap APIs**.

Supported places include:

-   museums
-   historical sites
-   parks
-   restaurants
-   cafes
-   bakeries
-   wine bars
-   nightlife venues

------------------------------------------------------------------------

## RAG Knowledge Integration

The agent enriches the itinerary using **vector search**.

Knowledge examples:

    knowledge/paris.txt
    knowledge/rome.txt
    knowledge/barcelona.txt

Embeddings are generated using **Scaleway Embeddings API**.

------------------------------------------------------------------------

## Interactive Map Generation

Each itinerary includes an automatically generated map showing:

-   attractions
-   restaurants
-   itinerary points

Maps are rendered using **Leaflet.js**.

------------------------------------------------------------------------

## Trip Memory

Trips can optionally be stored using Redis.

Example:

``` python
save_trip("paris", itinerary)
load_trip("paris")
```

This enables future conversational improvements.

------------------------------------------------------------------------

# Local Setup

Clone the repository:

``` bash
git clone https://github.com/JWangSCW/personal_assistant.git
cd personal_assistant
```

Create a virtual environment:

``` bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

# Environment Variables

Create a `.env` file:

    SCW_SECRET_KEY=your_scaleway_secret_key
    SCW_MODEL=llama-3.1-8b-instruct
    SCW_EMBEDDING_MODEL=bge-multilingual-gemma2

    REDIS_HOST=
    REDIS_PORT=6379
    REDIS_PASSWORD=
    REDIS_DB=0

Redis is optional. If not configured, memory features will be disabled
automatically.

------------------------------------------------------------------------

# Target Deployment on Scaleway

The entire system can be deployed on **Scaleway cloud infrastructure**.

``` mermaid
flowchart TD

    USER[Internet User]

    USER --> LB[Scaleway Load Balancer]

    LB --> K8S[Kubernetes Kapsule]

    K8S --> API[Travel Agent API]

    K8S --> UI[Streamlit UI]

    API --> REDIS[Managed Redis]

    API --> GENAI[Scaleway Generative API]

    API --> OBJ[Object Storage]
```

------------------------------------------------------------------------

# Future Improvements

Planned improvements:

-   route optimization
-   weather-aware trip planning
-   budget estimation
-   conversational itinerary editing
-   persistent vector database
-   Kubernetes deployment automation

------------------------------------------------------------------------

# Tech Stack

Python\
LangGraph\
FastAPI\
Streamlit\
Redis\
OpenStreetMap APIs\
Leaflet\
Scaleway Generative APIs

------------------------------------------------------------------------

# Purpose of this Project

This project demonstrates how to build **production-ready AI agents**
combining:

-   LLM reasoning
-   geospatial APIs
-   vector search
-   memory
-   cloud-native deployment

It also showcases how **Scaleway Generative APIs** can power real-world
AI applications.
