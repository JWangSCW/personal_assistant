# AI Travel Agent (LangGraph + Scaleway)

An AI-powered travel planning agent capable of generating **personalized
travel itineraries** using LLM reasoning, real-world geospatial data,
and interactive maps.

This project demonstrates how to build a **production-style AI agent
architecture** combining:

-   LangGraph agents
-   Scaleway Generative APIs (LLM + Embeddings)
-   OpenStreetMap data (via Overpass API)
-   Open‑Meteo APIs for geocoding and weather
-   Wikipedia for contextual knowledge
-   Redis memory (optional)
-   Streamlit UI
-   FastAPI backend
-   Kubernetes deployment on **Scaleway Kapsule**

Example prompt:

    Plan a 2-day romantic trip in Paris with museums and wine bars

The agent will automatically:

-   understand the request
-   discover attractions and restaurants
-   consider weather conditions
-   retrieve city information
-   generate a day‑by‑day itinerary
-   render an interactive travel map

------------------------------------------------------------------------

# System Architecture

The application follows a **cloud‑native AI agent architecture deployed
on Scaleway Kubernetes (Kapsule)**.

``` mermaid
flowchart TD

    USER[Internet User]

    USER --> LB[Scaleway Load Balancer]

    LB --> UI[Streamlit UI Pod<br>Kubernetes]

    UI --> API[FastAPI Backend Pod<br>Kubernetes Service]

    API --> AGENT[LangGraph Agent]

    AGENT --> GEO[Geocoding<br>Open-Meteo Geocoding API]

    AGENT --> POI[POI Discovery<br>Overpass API]

    AGENT --> WEATHER[Weather Data<br>Open-Meteo Forecast API]

    AGENT --> WIKI[City Summary<br>Wikipedia API]

    AGENT --> EMB[Embeddings<br>Scaleway Embeddings API]

    AGENT --> MEM[Trip Memory<br>Redis optional]

    AGENT --> MAP[Map Generation<br>Folium]

    MAP --> UI
```

------------------------------------------------------------------------

# Deployment Architecture

The system is deployed on **Scaleway Kapsule Kubernetes**.

Architecture highlights:

-   **Streamlit UI** runs in a Kubernetes Pod
-   **FastAPI backend** runs in a separate Pod
-   UI exposed via **Scaleway Load Balancer**
-   Container images stored in **Scaleway Container Registry**
-   AI reasoning powered by **Scaleway Generative APIs**

This architecture enables:

-   independent scaling of UI and API
-   containerized microservices
-   clear service separation

------------------------------------------------------------------------

# Component Hosting

| Component        | Technology               | Hosting                     |
| ---------------- | ------------------------ | --------------------------- |
| UI               | Streamlit                | Kapsule Pod                 |
| API              | FastAPI                  | Kapsule Pod                 |
| Agent            | LangGraph                | Kapsule                     |
| Container Images | Docker                   | Scaleway Container Registry |
| LLM              | Scaleway Generative API  | Scaleway                    |
| Embeddings       | Scaleway Embeddings API  | Scaleway                    |
| Geocoding        | Open-Meteo Geocoding API | External                    |
| POI Discovery    | Overpass API             | External                    |
| Weather          | Open-Meteo Forecast API  | External                    |
| City Summary     | Wikipedia API            | External                    |
| Memory           | Redis optional           | Local / Managed             |
| Map Generation   | Folium (Leaflet)         | Backend                     |

------------------------------------------------------------------------

# Agent Tools

The LangGraph agent orchestrates several tools defined in the codebase.

  -----------------------------------------------------------------------
  Tool                                Purpose
  ----------------------------------- -----------------------------------
  `geocode_city`                      Convert a city name into
                                      coordinates using Open‑Meteo
                                      Geocoding

  `fetch_attractions`                 Retrieve attractions (museums,
                                      parks, historic sites) using
                                      Overpass

  `fetch_restaurants`                 Retrieve restaurants, cafes,
                                      bakeries, bars using Overpass

  `fetch_weather`                     Retrieve short‑term weather
                                      forecast from Open‑Meteo

  `get_city_summary`                  Retrieve a city overview from
                                      Wikipedia

  `generate_itinerary`                Use LLM reasoning to create a
                                      travel itinerary

  `generate_map`                      Render itinerary locations using
                                      Folium
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# Example Query Flow

Example prompt:

    Plan a 2-day romantic trip in Paris with museums and wine bars

Execution flow:

1.  User accesses the app via the **Load Balancer**
2.  Request reaches the **Streamlit UI pod**
3.  UI sends the query to the **FastAPI backend**
4.  FastAPI triggers the **LangGraph agent**
5.  The agent orchestrates tools:
    -   geocode the city
    -   fetch attractions and restaurants
    -   retrieve weather information
    -   fetch a city summary
6.  The LLM generates a structured travel itinerary
7.  Leaflet renders an interactive map
8.  Results are returned to the UI

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

Redis is optional.\
If not configured, memory features are disabled automatically.

------------------------------------------------------------------------

# Tech Stack

Python\
LangGraph\
FastAPI\
Streamlit\
Redis\
Open‑Meteo APIs\
OpenStreetMap (Overpass API)\
Wikipedia REST API\
Leaflet\
Scaleway Generative APIs

------------------------------------------------------------------------

# Project Goal

This project demonstrates how to build **real-world AI agents**
combining:

-   LLM reasoning
-   external APIs and tools
-   geospatial discovery
-   conversational memory
-   cloud-native deployment

It also showcases how **Scaleway Generative APIs** can power real AI
applications.
