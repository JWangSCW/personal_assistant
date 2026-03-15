# AI Travel Agent (LangGraph + Scaleway)

An AI-powered travel planning agent capable of generating **personalized
travel itineraries** using LLM reasoning, geospatial data, and
interactive maps.

This project demonstrates how to build a **production‑style AI agent
architecture** using:

-   LangGraph agents
-   Scaleway Generative APIs (LLM + Embeddings)
-   OpenStreetMap geospatial data
-   Redis memory
-   Streamlit UI
-   FastAPI backend
-   Kubernetes deployment on **Scaleway Kapsule**

Example prompt:

    Plan a 2-day romantic trip in Paris with museums and wine bars

The agent will automatically:

-   understand the request
-   discover relevant attractions
-   build a day‑by‑day itinerary
-   generate an interactive map

------------------------------------------------------------------------

# Demo Capabilities

The AI agent dynamically generates travel plans including:

-   itinerary planning
-   discovery of attractions and restaurants
-   contextual travel recommendations
-   geospatial visualization on an interactive map

Example output:

**Day 1** - Louvre Museum - Walk along the Seine - Wine bar in Le Marais

**Day 2** - Montmartre exploration - Musée d'Orsay - Dinner near
Saint‑Germain

All locations are displayed automatically on a map.

------------------------------------------------------------------------

# System Architecture

The application follows a **cloud‑native AI agent architecture**
deployed on **Scaleway Kubernetes (Kapsule)**.

``` mermaid
flowchart TD

    USER[Internet User]

    USER --> LB[Scaleway Load Balancer]

    LB --> UI[Streamlit UI Pod<br>Kubernetes]

    UI --> API[FastAPI Backend Pod<br>Kubernetes]

    API --> AGENT[LangGraph Agent]

    AGENT --> PARSER[LLM Query Parser<br>Scaleway Generative API]

    AGENT --> GEO[Geocoding<br>Nominatim]

    AGENT --> POI[POI Search<br>OpenStreetMap Overpass]

    AGENT --> VEC[Vector Search<br>Scaleway Embeddings API]

    AGENT --> MEM[Redis Memory]

    AGENT --> LLM[Travel Guide Generator<br>Scaleway Generative API]

    AGENT --> MAP[Interactive Map Generator<br>Leaflet]

    MAP --> UI
```

------------------------------------------------------------------------

# Deployment Architecture

The application is deployed using **Scaleway Kapsule Kubernetes**.

Key design elements:

-   **Streamlit UI** deployed as a Kubernetes pod
-   **FastAPI backend** deployed as a separate Kubernetes pod
-   UI exposed through a **Scaleway Load Balancer**
-   Docker images stored in **Scaleway Container Registry**
-   AI inference provided by **Scaleway Generative APIs**

This separation enables:

-   independent scaling of UI and API
-   containerized microservices
-   easier CI/CD workflows

------------------------------------------------------------------------

# Component Hosting

  Component          Technology               Hosting
  ------------------ ------------------------ -----------------------------
  UI                 Streamlit                Scaleway Kapsule
  API                FastAPI                  Scaleway Kapsule
  Agent              LangGraph                Scaleway Kapsule
  Container Images   Docker                   Scaleway Container Registry
  LLM                Generative API           Scaleway Model Library
  Embeddings         Embeddings API           Scaleway Model Library
  POI Search         OpenStreetMap Overpass   External
  Geocoding          Nominatim                External
  Memory             Redis                    Local or Managed Redis
  Map Rendering      Leaflet                  Browser

------------------------------------------------------------------------

# Request Flow

Example query:

    Plan a 2-day romantic trip in Paris with museums and wine bars

Execution flow:

1.  User accesses the application via the **Load Balancer**
2.  Request reaches the **Streamlit UI pod**
3.  UI sends the request to the **FastAPI backend**
4.  FastAPI triggers the **LangGraph agent**
5.  The agent orchestrates multiple tools:
    -   geocoding
    -   POI discovery
    -   vector retrieval (RAG)
    -   LLM reasoning
6.  A travel itinerary is generated
7.  Map data is produced using Leaflet
8.  Results are returned to the UI

------------------------------------------------------------------------

# Features

## AI Trip Planning

The system generates itineraries based on:

-   destination
-   trip duration
-   travel style
-   interests

Example prompts:

    Plan a 1-day food trip in Rome
    Plan a museum weekend in Madrid
    Plan a chill trip in Barcelona

------------------------------------------------------------------------

## Dynamic POI Discovery

Points of interest are discovered dynamically using **OpenStreetMap
APIs**.

Supported places include:

-   museums
-   historical landmarks
-   parks
-   restaurants
-   cafes
-   bakeries
-   wine bars
-   nightlife venues

------------------------------------------------------------------------

## RAG Knowledge Integration

The agent can enrich itineraries using **vector search**.

Example knowledge files:

    knowledge/paris.txt
    knowledge/rome.txt
    knowledge/barcelona.txt

Embeddings are generated using **Scaleway Embeddings API**.

------------------------------------------------------------------------

## Interactive Map Generation

Each itinerary automatically generates a map displaying:

-   attractions
-   restaurants
-   itinerary locations

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

# Local Development

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

Redis configuration is optional.

If not configured, memory features will be disabled automatically.

------------------------------------------------------------------------

# Future Improvements

Planned enhancements:

-   route optimization
-   weather-aware travel planning
-   travel budget estimation
-   conversational itinerary editing
-   persistent vector database
-   automated Kubernetes deployment

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

# Project Goal

This project demonstrates how to build **real-world AI agents**
combining:

-   LLM reasoning
-   external tools and APIs
-   vector search (RAG)
-   conversational memory
-   cloud-native infrastructure

It also showcases how **Scaleway Generative APIs** can power practical
AI applications.
