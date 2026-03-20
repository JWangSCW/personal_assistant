import os
import time
import uuid
import html
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "").rstrip("/")


ARCH_STEP_META = {
    "ui": {
        "title": "User Interface",
        "short": "UI",
        "desc": "Trip request input",
        "service": "Streamlit on Scaleway Kapsule",
        "service_detail": "Frontend runtime",
        "lane": "Input",
        "icon": "🖥️",
    },
    "api": {
        "title": "API Gateway",
        "short": "API",
        "desc": "Async job submission",
        "service": "FastAPI on Scaleway Kapsule",
        "service_detail": "Backend API service",
        "lane": "Input",
        "icon": "⚙️",
    },
    "redis": {
        "title": "Job State & Queue",
        "short": "Redis",
        "desc": "Async coordination and polling",
        "service": "Scaleway Managed Redis",
        "service_detail": "Queue and state backend",
        "lane": "Input",
        "icon": "🧠",
    },
    "worker": {
        "title": "Agent Runtime",
        "short": "Agent",
        "desc": "Mission orchestration runtime",
        "service": "Python worker on Scaleway Kapsule",
        "service_detail": "Background orchestration runtime",
        "lane": "Core",
        "icon": "🔄",
    },
    "parser_llm": {
        "title": "Intent Parsing",
        "short": "Parsing",
        "desc": "Extracts constraints and trip goals",
        "service": "Scaleway Generative APIs",
        "service_detail": "LLM understanding layer",
        "lane": "Tasks",
        "icon": "🧩",
    },
    "itinerary_llm": {
        "title": "Itinerary Planning",
        "short": "Planning",
        "desc": "Generates the travel plan",
        "service": "Scaleway Generative APIs",
        "service_detail": "LLM planning layer",
        "lane": "Tasks",
        "icon": "✨",
    },
    "geocode": {
        "title": "Place Enrichment",
        "short": "Enrichment",
        "desc": "Geocoding and place coordinates",
        "service": "External Geocoding API",
        "service_detail": "Location enrichment provider",
        "lane": "Tasks",
        "icon": "📍",
    },
    "map": {
        "title": "Map Rendering",
        "short": "Rendering",
        "desc": "Interactive itinerary map",
        "service": "Folium rendered in Streamlit",
        "service_detail": "Visualization layer",
        "lane": "Tasks",
        "icon": "🗺️",
    },
}


def get_weather_icon(code: int) -> str:
    if code == 0:
        return "☀️"
    elif code in [1, 2]:
        return "🌤️"
    elif code == 3:
        return "☁️"
    elif code in [45, 48]:
        return "🌫️"
    elif code in [51, 53, 55]:
        return "🌦️"
    elif code in [61, 63, 65]:
        return "🌧️"
    elif code in [71, 73, 75]:
        return "❄️"
    elif code in [95]:
        return "⛈️"
    return "🌍"


def submit_plan_trip(api_url: str, query: str, session_id: str):
    return requests.post(
        f"{api_url}/plan-trip",
        json={
            "query": query,
            "session_id": session_id,
        },
        timeout=15,
    )


def submit_refine_trip(api_url: str, session_id: str, instruction: str):
    return requests.post(
        f"{api_url}/refine-trip",
        json={
            "session_id": session_id,
            "instruction": instruction,
        },
        timeout=15,
    )


def normalize_steps_with_meta(steps: list[dict]) -> list[dict]:
    normalized = []

    for idx, step in enumerate(steps):
        step_id = step.get("id")
        meta = ARCH_STEP_META.get(step_id, {})

        duration = (
            step.get("duration_s")
            or step.get("elapsed_s")
            or step.get("elapsed")
            or step.get("duration")
            or 0
        )

        try:
            duration = float(duration)
        except Exception:
            duration = 0.0

        normalized.append(
            {
                "id": step_id,
                "label": step.get("label") or meta.get("title") or step_id,
                "status": step.get("status", "pending"),
                "title": meta.get("title", step.get("label", step_id)),
                "short": meta.get("short", step.get("label", step_id)),
                "desc": meta.get("desc", ""),
                "service": meta.get("service", "Unknown"),
                "service_detail": meta.get("service_detail", ""),
                "lane": meta.get("lane", "Other"),
                "icon": meta.get("icon", "•"),
                "is_bottleneck": meta.get("is_bottleneck", False),
                "duration": duration,
                "order": idx,
            }
        )

    return normalized


def get_step_duration_label(step: dict) -> str:
    duration = step.get("duration", 0)
    if duration <= 0:
        return "—"
    if duration < 0.1:
        return "<0.1s"
    return f"{duration:.1f}s"


def get_current_running_step(steps: list[dict]) -> dict | None:
    for step in steps:
        if step.get("status") == "running":
            return step
    return None


def get_total_elapsed(steps: list[dict]) -> float:
    return round(sum(step.get("duration", 0) for step in steps), 3)


def render_architecture_summary(steps: list[dict], current_step: str | None = None):
    steps = normalize_steps_with_meta(steps)
    running_step = get_current_running_step(steps)
    total_elapsed = get_total_elapsed(steps)
    completed_count = len([s for s in steps if s["status"] == "done"])
    running_count = len([s for s in steps if s["status"] == "running"])

    current_label = "Idle"
    if running_step:
        current_label = running_step["title"]
    elif current_step:
        meta = ARCH_STEP_META.get(current_step, {})
        current_label = meta.get("title", current_step)

    runtime_status = "Running" if running_count > 0 else "Completed"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mission stage", current_label)
    col2.metric("Completed tasks", completed_count)
    col3.metric("Total elapsed", f"{total_elapsed:.1f}s" if total_elapsed else "—")
    col4.metric("Runtime status", runtime_status)


def render_architecture_svg(steps: list[dict], height: int = 720):
    steps = normalize_steps_with_meta(steps)
    status_by_id = {step["id"]: step["status"] for step in steps}
    step_by_id = {step["id"]: step for step in steps}
    current_running = get_current_running_step(steps)
    current_running_id = current_running["id"] if current_running else None
    total_elapsed = get_total_elapsed(steps)

    # -----------------------------
    # Scaleway-like soft purple palette
    # -----------------------------
    PURPLE = "#7C3AED"
    PURPLE_MID = "#8B5CF6"
    PURPLE_SOFT = "#C4B5FD"
    PURPLE_PALE = "#DDD6FE"
    PURPLE_BG = "#F5F3FF"
    PURPLE_BG_ACTIVE = "#EDE9FE"
    PURPLE_TEXT = "#4C1D95"

    SLATE_TEXT = "#334155"
    SLATE_MUTED = "#64748B"
    BORDER_LIGHT = "#E2E8F0"
    PANEL_BG = "#FFFFFF"
    HEADER_BG = "#FAF5FF"

    def colors(step_id: str):
        status = status_by_id.get(step_id, "pending")
        if status == "done":
            return {"fill": PURPLE_BG_ACTIVE, "stroke": PURPLE, "text": PURPLE_TEXT}
        elif status == "running":
            return {"fill": "#E9D5FF", "stroke": PURPLE_MID, "text": PURPLE_TEXT}
        elif status == "failed":
            return {"fill": "#FEE2E2", "stroke": "#DC2626", "text": "#7F1D1D"}
        return {"fill": PURPLE_BG, "stroke": PURPLE_PALE, "text": "#6D28D9"}

    def service_style(service_name: str):
        if "External" in service_name or "Geocoding" in service_name:
            return {"fill": "#FFFFFF", "stroke": "#A78BFA", "text": "#5B21B6"}
        return {"fill": "#FFFFFF", "stroke": PURPLE_MID, "text": PURPLE_TEXT}

    def left_center(n):
        return n["x"], n["y"] + n["h"] / 2

    def right_center(n):
        return n["x"] + n["w"], n["y"] + n["h"] / 2

    def top_center(n):
        return n["x"] + n["w"] / 2, n["y"]

    def bottom_center(n):
        return n["x"] + n["w"] / 2, n["y"] + n["h"]

    mission_state = "Completed" if current_running is None else "Running"
    mission_current = current_running["title"] if current_running else "Idle"

    # -------------------------------------------------
    # Layout
    # -------------------------------------------------
    input_nodes = [
        {"id": "ui", "x": 78, "y": 255, "w": 205, "h": 84},
        {"id": "api", "x": 78, "y": 360, "w": 205, "h": 84},
        {"id": "redis", "x": 78, "y": 465, "w": 205, "h": 84},
    ]

    core_node = {"id": "worker", "x": 410, "y": 315, "w": 370, "h": 152}

    task_nodes = {
        "parser_llm": {"id": "parser_llm", "x": 470, "y": 150, "w": 250, "h": 92},
        "itinerary_llm": {"id": "itinerary_llm", "x": 860, "y": 255, "w": 250, "h": 92},
        "geocode": {"id": "geocode", "x": 860, "y": 470, "w": 250, "h": 92},
        "map": {"id": "map", "x": 470, "y": 545, "w": 250, "h": 92},
    }

    output_nodes = [
        {
            "id": "output_itinerary",
            "title": "Day-by-day Itinerary",
            "desc": "Structured trip plan",
            "x": 1165,
            "y": 255,
            "w": 175,
            "h": 68,
        },
        {
            "id": "output_guide",
            "title": "Travel Guide",
            "desc": "Narrative recommendations",
            "x": 1165,
            "y": 345,
            "w": 175,
            "h": 68,
        },
        {
            "id": "output_map",
            "title": "Interactive Map",
            "desc": "Route and places view",
            "x": 1165,
            "y": 470,
            "w": 175,
            "h": 68,
        },
    ]

    all_nodes = {n["id"]: n for n in input_nodes + [core_node] + list(task_nodes.values())}

    # -------------------------------------------------
    # Lines
    # -------------------------------------------------
    line_parts = []

    def add_elbow(points, active=False, width="2.4", base=None, opacity="0.9", arrow=True):
        if base is None:
            base = PURPLE_SOFT
        d = " ".join(
            [f"M {points[0][0]} {points[0][1]}"] +
            [f"L {x} {y}" for x, y in points[1:]]
        )
        marker = 'marker-end="url(#arrow)"' if arrow else ""

        overlay = ""
        if active:
            overlay = f'''
            <path d="{d}" fill="none" stroke="{PURPLE_MID}"
                  stroke-width="{float(width)+0.9}"
                  stroke-dasharray="10 8"
                  stroke-linecap="round" opacity="0.95">
              <animate attributeName="stroke-dashoffset" from="36" to="0" dur="0.95s" repeatCount="indefinite"/>
            </path>
            '''

        return f'''
        <path d="{d}" fill="none" stroke="{base}" stroke-width="{width}" opacity="{opacity}" {marker}/>
        {overlay}
        '''

    def connect_lr(a, b, mid_x, active=False, width="2.4", base=None, opacity="0.9"):
        return add_elbow(
            [
                right_center(a),
                (mid_x, right_center(a)[1]),
                (mid_x, left_center(b)[1]),
                left_center(b),
            ],
            active=active,
            width=width,
            base=base or PURPLE_SOFT,
            opacity=opacity,
        )

    def connect_tb(a, b, mid_y, active=False, width="2.4", base=None, opacity="0.9"):
        return add_elbow(
            [
                bottom_center(a),
                (bottom_center(a)[0], mid_y),
                (top_center(b)[0], mid_y),
                top_center(b),
            ],
            active=active,
            width=width,
            base=base or PURPLE_SOFT,
            opacity=opacity,
        )

    # input chain
    for i in range(len(input_nodes) - 1):
        n1 = input_nodes[i]
        n2 = input_nodes[i + 1]
        line_parts.append(
            add_elbow(
                [
                    bottom_center(n1),
                    (bottom_center(n1)[0], (bottom_center(n1)[1] + top_center(n2)[1]) / 2),
                    (top_center(n2)[0], (bottom_center(n1)[1] + top_center(n2)[1]) / 2),
                    top_center(n2),
                ],
                active=(current_running_id == n2["id"]),
                width="2.6",
                base=PURPLE_SOFT,
            )
        )

    # redis -> core
    r = all_nodes["redis"]
    c = core_node
    line_parts.append(
        connect_lr(
            r,
            c,
            mid_x=338,
            active=current_running_id == "worker",
            width="2.8",
            base="#A78BFA",
        )
    )

    # core -> parser (top)
    p = task_nodes["parser_llm"]
    line_parts.append(
        connect_tb(
            c,
            p,
            mid_y=275,
            active=current_running_id == "parser_llm",
            width="2.8",
            base="#A78BFA",
        )
    )

    # core -> itinerary
    i = task_nodes["itinerary_llm"]
    line_parts.append(
        connect_lr(
            c,
            i,
            mid_x=820,
            active=current_running_id == "itinerary_llm",
            width="2.8",
            base="#A78BFA",
        )
    )

    # core -> geocode
    g = task_nodes["geocode"]
    line_parts.append(
        connect_lr(
            c,
            g,
            mid_x=820,
            active=current_running_id == "geocode",
            width="2.8",
            base="#A78BFA",
        )
    )

    # core -> map
    m = task_nodes["map"]
    line_parts.append(
        connect_tb(
            c,
            m,
            mid_y=520,
            active=current_running_id == "map",
            width="2.8",
            base="#A78BFA",
        )
    )

    # minimal collaboration lines
    line_parts.append(
        connect_lr(
            p,
            i,
            mid_x=790,
            width="1.8",
            base=PURPLE_PALE,
            opacity="0.75",
        )
    )
    line_parts.append(
        connect_lr(
            g,
            m,
            mid_x=790,
            width="1.8",
            base=PURPLE_PALE,
            opacity="0.75",
        )
    )

    # outputs
    # itinerary -> itinerary output
    line_parts.append(
        connect_lr(
            i,
            output_nodes[0],
            mid_x=1128,
            active=current_running_id == "itinerary_llm",
            width="2.4",
            base="#A78BFA",
        )
    )

    # itinerary -> guide output
    line_parts.append(
        connect_lr(
            i,
            output_nodes[1],
            mid_x=1128,
            active=current_running_id == "itinerary_llm",
            width="2.0",
            base=PURPLE_PALE,
            opacity="0.85",
        )
    )

    # geocode/map -> map output
    line_parts.append(
        connect_lr(
            g,
            output_nodes[2],
            mid_x=1128,
            active=current_running_id in {"geocode", "map"},
            width="2.4",
            base="#A78BFA",
        )
    )

    # -------------------------------------------------
    # Node render
    # -------------------------------------------------
    node_parts = []

    def build_runtime_node(node, title_size=13.5, desc_size=10):
        step = step_by_id.get(node["id"], {"id": node["id"], "status": "pending"})
        c = colors(node["id"])
        is_running = step.get("status") == "running"

        glow = ""
        if is_running:
            glow = f'''
            <rect x="{node["x"]-4}" y="{node["y"]-4}" rx="20" ry="20"
                  width="{node["w"]+8}" height="{node["h"]+8}"
                  fill="none" stroke="{PURPLE_MID}" stroke-width="3.5" opacity="0.22">
              <animate attributeName="opacity" values="0.14;0.62;0.14" dur="1.4s" repeatCount="indefinite"/>
            </rect>
            '''

        s = service_style(step.get("service", ""))
        service_width = min(node["w"] - 26, max(110, len(step.get("service", "")) * 6 + 22))

        return f'''
        <g>
          {glow}
          <rect x="{node["x"]}" y="{node["y"]}" rx="18" ry="18" width="{node["w"]}" height="{node["h"]}"
                fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="2.8"/>
          <text x="{node["x"] + 14}" y="{node["y"] + 27}"
                font-family="Arial, sans-serif" font-size="{title_size}" font-weight="700" fill="{c["text"]}">
            {html.escape(step.get("icon", "•"))} {html.escape(step.get("title", node["id"]))}
          </text>
          <text x="{node["x"] + 14}" y="{node["y"] + 48}"
                font-family="Arial, sans-serif" font-size="{desc_size}" fill="{c["text"]}" opacity="0.92">
            {html.escape(step.get("desc", ""))}
          </text>
          <rect x="{node["x"] + 14}" y="{node["y"] + node["h"] - 32}" rx="10" ry="10"
                width="{service_width}" height="19"
                fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="1.1"/>
          <text x="{node["x"] + 21}" y="{node["y"] + node["h"] - 18}"
                font-family="Arial, sans-serif" font-size="9.4" font-weight="700" fill="{s["text"]}">
            {html.escape(step.get("service", ""))}
          </text>
        </g>
        '''

    def build_core_node(node):
        step = step_by_id.get(node["id"], {"id": node["id"], "status": "pending"})
        c = colors(node["id"])
        is_running = step.get("status") == "running"

        glow = ""
        if is_running:
            glow = f'''
            <rect x="{node["x"]-6}" y="{node["y"]-6}" rx="28" ry="28"
                  width="{node["w"]+12}" height="{node["h"]+12}"
                  fill="none" stroke="{PURPLE_MID}" stroke-width="4.5" opacity="0.22">
              <animate attributeName="opacity" values="0.14;0.62;0.14" dur="1.4s" repeatCount="indefinite"/>
            </rect>
            '''

        return f'''
        <g>
          {glow}
          <rect x="{node["x"]}" y="{node["y"]}" rx="28" ry="28" width="{node["w"]}" height="{node["h"]}"
                fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="3.2"/>
          <text x="{node["x"] + 24}" y="{node["y"] + 42}"
                font-family="Arial, sans-serif" font-size="21" font-weight="700" fill="{c["text"]}">
            🤖 AI Travel Agent Mission
          </text>
          <text x="{node["x"] + 24}" y="{node["y"] + 72}"
                font-family="Arial, sans-serif" font-size="12.6" fill="{c["text"]}" opacity="0.92">
            Goal-driven orchestration for trip planning
          </text>
          <text x="{node["x"] + 24}" y="{node["y"] + 102}"
                font-family="Arial, sans-serif" font-size="11.2" fill="{c["text"]}">
            Dispatches, coordinates, validates, and merges sub-task results
          </text>
          <rect x="{node["x"] + 24}" y="{node["y"] + 116}" rx="12" ry="12"
                width="220" height="24" fill="#FFFFFF" stroke="{PURPLE_MID}" stroke-width="1.15"/>
          <text x="{node["x"] + 34}" y="{node["y"] + 132}"
                font-family="Arial, sans-serif" font-size="10" font-weight="700" fill="{PURPLE_TEXT}">
            Python worker on Scaleway Kapsule
          </text>
        </g>
        '''

    def build_output_node(node):
        return f'''
        <g>
          <rect x="{node["x"]}" y="{node["y"]}" rx="18" ry="18" width="{node["w"]}" height="{node["h"]}"
                fill="#FCFDFE" stroke="{PURPLE_PALE}" stroke-width="1.5"/>
          <text x="{node["x"] + 14}" y="{node["y"] + 28}"
                font-family="Arial, sans-serif" font-size="12.8" font-weight="700" fill="#1F1738">
            {html.escape(node["title"])}
          </text>
          <text x="{node["x"] + 14}" y="{node["y"] + 49}"
                font-family="Arial, sans-serif" font-size="10.3" fill="{SLATE_TEXT}">
            {html.escape(node["desc"])}
          </text>
        </g>
        '''

    for n in input_nodes:
        node_parts.append(build_runtime_node(n))

    node_parts.append(build_core_node(core_node))

    for n in task_nodes.values():
        node_parts.append(build_runtime_node(n))

    for n in output_nodes:
        node_parts.append(build_output_node(n))

    svg = f"""
    <svg viewBox="0 0 1360 720" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow" markerWidth="9" markerHeight="9" refX="7.5" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L8,3 z" fill="{PURPLE_SOFT}" />
        </marker>
      </defs>

      <rect x="0" y="0" width="1360" height="720" fill="{PANEL_BG}" rx="28" ry="28"/>

      <!-- Header -->
      <rect x="26" y="18" width="1308" height="86" rx="22" ry="22" fill="{HEADER_BG}" stroke="{BORDER_LIGHT}" stroke-width="1.1"/>
      <text x="48" y="50" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#1F1738">
        AI Agent Mission Board
      </text>
      <text x="48" y="76" font-family="Arial, sans-serif" font-size="12" fill="{SLATE_TEXT}">
        Center-orchestrated workflow across user input, agent sub-tasks, managed services, and outputs
      </text>

      <rect x="1032" y="33" width="276" height="56" rx="18" ry="18" fill="#FFFFFF" stroke="{PURPLE_PALE}" stroke-width="1.1"/>
      <text x="1051" y="56" font-family="Arial, sans-serif" font-size="12.5" font-weight="700" fill="#1F1738">
        Status: {html.escape(mission_state)}
      </text>
      <text x="1051" y="78" font-family="Arial, sans-serif" font-size="11" fill="{SLATE_MUTED}">
        Current task: {html.escape(mission_current)} · Total elapsed: {total_elapsed:.1f}s
      </text>

      <!-- Labels -->
      <text x="80" y="220" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#1F1738">
        Input Flow
      </text>
      <text x="80" y="239" font-family="Arial, sans-serif" font-size="11" fill="{SLATE_MUTED}">
        User entry, API submission, and async job state
      </text>

      <text x="1165" y="225" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#1F1738">
        Generated Outputs
      </text>
      <text x="1165" y="243" font-family="Arial, sans-serif" font-size="11" fill="{SLATE_MUTED}">
        Final artifacts returned by the mission
      </text>

      <!-- Dependency pills -->
      <rect x="84" y="668" width="470" height="30" rx="15" ry="15" fill="#FAF5FF" stroke="{PURPLE_PALE}" stroke-width="1.0"/>
      <text x="100" y="687" font-family="Arial, sans-serif" font-size="10.4" fill="{PURPLE_TEXT}">
        Managed on Scaleway: Streamlit · FastAPI · Kapsule · Managed Redis · Generative APIs
      </text>

      <rect x="575" y="668" width="300" height="30" rx="15" ry="15" fill="#FAF5FF" stroke="{PURPLE_PALE}" stroke-width="1.0"/>
      <text x="591" y="687" font-family="Arial, sans-serif" font-size="10.4" fill="{PURPLE_TEXT}">
        External: Geocoding API · Map data
      </text>

      {''.join(line_parts)}
      {''.join(node_parts)}
    </svg>
    """
    st.components.v1.html(svg, height=height, scrolling=False)

def render_step_timeline(steps: list[dict]):
    steps = normalize_steps_with_meta(steps)

    if not steps:
        st.info("No runtime stages available yet.")
        return

    # Soft purple palette
    PURPLE = "#7C3AED"
    PURPLE_MID = "#8B5CF6"
    PURPLE_SOFT = "#C4B5FD"
    PURPLE_PALE = "#EDE9FE"
    PURPLE_BG = "#FAF5FF"
    TEXT_DARK = "#1F1738"
    TEXT_MUTED = "#6B7280"
    BORDER = "#E9DDFB"
    GRID = "#EEE7FB"
    FAILED = "#DC2626"
    RUNNING = "#A78BFA"
    PENDING = "#D1D5DB"

    agent_task_ids = {"parser_llm", "itinerary_llm", "geocode", "map"}
    platform_ids = {"ui", "api", "redis", "worker"}

    ordered_steps = sorted(steps, key=lambda s: s.get("order", 0))

    total_duration = sum(step.get("duration", 0) for step in ordered_steps)
    if total_duration <= 0:
        total_duration = 1.0

    timeline_width = 100.0
    label_col = 28.0
    status_col = 10.0
    chart_col = 62.0

    cumulative = 0.0
    enriched_steps = []

    for step in ordered_steps:
        duration = max(float(step.get("duration", 0) or 0), 0.0)
        start_pct = (cumulative / total_duration) * timeline_width
        width_pct = (duration / total_duration) * timeline_width if duration > 0 else 1.2

        if duration > 0:
            width_pct = max(width_pct, 2.2)
        else:
            width_pct = 1.4

        status = step.get("status", "pending")
        if status == "done":
            bar_color = PURPLE_MID
            bar_fill = PURPLE_PALE
        elif status == "running":
            bar_color = RUNNING
            bar_fill = "#F3E8FF"
        elif status == "failed":
            bar_color = FAILED
            bar_fill = "#FEE2E2"
        else:
            bar_color = PENDING
            bar_fill = "#F3F4F6"

        enriched_steps.append(
            {
                **step,
                "start_pct": start_pct,
                "width_pct": width_pct,
                "bar_color": bar_color,
                "bar_fill": bar_fill,
            }
        )
        cumulative += duration

    def fmt_time(value: float) -> str:
        if value < 0.1:
            return "<0.1s"
        return f"{value:.1f}s"

    def build_group_html(title: str, filtered_steps: list[dict]) -> str:
        if not filtered_steps:
            return ""

        tick_count = 5
        tick_labels = [round((total_duration / tick_count) * i, 1) for i in range(tick_count + 1)]

        ticks_html = "".join(
            f"""
<div style="text-align:{'left' if idx == 0 else ('right' if idx == len(tick_labels)-1 else 'center')}; font-size:10.5px; color:{TEXT_MUTED};">
  {label}s
</div>
"""
            for idx, label in enumerate(tick_labels)
        )

        rows_html = []
        for step in filtered_steps:
            status = step.get("status", "pending")
            status_label = status.upper()
            icon = {
                "done": "✅",
                "running": "🟣",
                "failed": "❌",
                "pending": "⚪",
            }.get(status, "⚪")

            animated_overlay = ""
            if status == "running":
                animated_overlay = f"""
<div style="
  position:absolute;
  left:{step['start_pct']}%;
  top:8px;
  width:{step['width_pct']}%;
  height:18px;
  border-radius:999px;
  background: repeating-linear-gradient(
    135deg,
    rgba(124,58,237,0.18) 0px,
    rgba(124,58,237,0.18) 8px,
    rgba(139,92,246,0.35) 8px,
    rgba(139,92,246,0.35) 16px
  );
  background-size:32px 32px;
  animation:ganttFlow 1s linear infinite;
  pointer-events:none;
"></div>
"""

            rows_html.append(
                f"""
<div style="
  display:grid;
  grid-template-columns:{label_col}% {status_col}% {chart_col}%;
  align-items:center;
  gap:10px;
  padding:10px 0;
  border-top:1px solid #F1F5F9;
">
  <div>
    <div style="font-size:14px; font-weight:700; color:{TEXT_DARK};">
      {icon} {html.escape(step["title"])}
    </div>
    <div style="font-size:11px; color:{TEXT_MUTED}; margin-top:3px;">
      {html.escape(step["service"])}
    </div>
  </div>

  <div style="text-align:right;">
    <div style="font-size:11px; font-weight:700; color:{TEXT_DARK};">
      {status_label}
    </div>
    <div style="font-size:11px; color:{TEXT_MUTED}; margin-top:2px;">
      {fmt_time(step.get("duration", 0))}
    </div>
  </div>

  <div>
    <div style="
      position:relative;
      height:34px;
      border-radius:12px;
      background:
        repeating-linear-gradient(
          to right,
          #FFFFFF 0%,
          #FFFFFF calc(20% - 1px),
          {GRID} calc(20% - 1px),
          {GRID} 20%
        );
      border:1px solid #EEE7FB;
      overflow:hidden;
    ">
      <div style="
        position:absolute;
        left:{step['start_pct']}%;
        top:8px;
        width:{step['width_pct']}%;
        height:18px;
        border-radius:999px;
        background:{step['bar_fill']};
        border:1.5px solid {step['bar_color']};
        box-sizing:border-box;
      "></div>
      {animated_overlay}
    </div>
  </div>
</div>
"""
            )

        return f"""
<div style="
  border:1px solid {BORDER};
  border-radius:18px;
  padding:16px 18px 10px 18px;
  margin-bottom:18px;
  background:{PURPLE_BG};
">
  <div style="font-size:16px; font-weight:700; color:{TEXT_DARK}; margin-bottom:10px;">
    {html.escape(title)}
  </div>

  <div style="
    display:grid;
    grid-template-columns:{label_col}% {status_col}% {chart_col}%;
    gap:10px;
    padding:0 0 8px 0;
    align-items:end;
  ">
    <div style="font-size:11px; font-weight:700; color:{TEXT_MUTED};">Stage</div>
    <div style="font-size:11px; font-weight:700; color:{TEXT_MUTED}; text-align:right;">Status</div>
    <div>
      <div style="display:grid; grid-template-columns:repeat(6, 1fr); margin-bottom:6px;">
        {ticks_html}
      </div>
    </div>
  </div>

  {''.join(rows_html)}
</div>
"""

    platform_steps = [s for s in enriched_steps if s["id"] in platform_ids]
    agent_steps = [s for s in enriched_steps if s["id"] in agent_task_ids]

    full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: white;
  }}

  @keyframes ganttFlow {{
    from {{ background-position: 0 0; }}
    to {{ background-position: 32px 0; }}
  }}
</style>
</head>
<body>
  {build_group_html("Agent sub-tasks timeline", agent_steps)}
  {build_group_html("Platform runtime timeline", platform_steps)}
</body>
</html>
"""

    estimated_height = 220 + 72 * max(len(agent_steps) + len(platform_steps), 1)
    st.components.v1.html(full_html, height=estimated_height, scrolling=False)

st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="🌍",
    layout="wide",
)

# ---------- session state ----------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "latest_session_preferences" not in st.session_state:
    st.session_state.latest_session_preferences = {}

if "latest_parsed_request" not in st.session_state:
    st.session_state.latest_parsed_request = {}

if "latest_weather_summary" not in st.session_state:
    st.session_state.latest_weather_summary = {}

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "current_job_id" not in st.session_state:
    st.session_state.current_job_id = None

if "current_job_status" not in st.session_state:
    st.session_state.current_job_status = None

if "current_job_type" not in st.session_state:
    st.session_state.current_job_type = None

if "current_arch_steps" not in st.session_state:
    st.session_state.current_arch_steps = []

if "current_arch_step" not in st.session_state:
    st.session_state.current_arch_step = None

if "last_instruction" not in st.session_state:
    st.session_state.last_instruction = ""

if "refine_input_value" not in st.session_state:
    st.session_state.refine_input_value = ""

if "pending_refine_value" not in st.session_state:
    st.session_state.pending_refine_value = None

session_id = st.session_state.session_id

# ---------- header ----------
st.markdown(
    """
<div style="padding: 10px 0 20px 0">
    <h1 style="margin-bottom:0">🌍 AI Travel Planner</h1>
    <p style="color: #9aa0a6; font-size:14px; margin-top:8px;">
        Plan smarter trips with AI — personalized, contextual, and instant.
    </p>
    <p style="font-size:12px; color:#6b7280; margin-top:4px;">
        🚀 Powered by Scaleway — Generative AI • Kubernetes • Redis
    </p>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("⚙️ How it works"):
    st.markdown(
        """
- User intent is parsed and normalized with LLM
- Session memory is stored in Redis
- Async orchestration runs on Kapsule
- Itineraries are generated with Scaleway Generative API
- Locations are geocoded for map rendering
- Existing trips can be refined without regenerating everything from scratch
"""
    )

st.divider()

# ---------- sidebar ----------
with st.sidebar:
    st.header("Trip Context")

    st.subheader("Session")
    st.code(session_id[:8], language=None)

    st.subheader("Session Memory")
    st.caption("Stored long-term preferences from previous interactions.")

    if st.session_state.latest_session_preferences:
        prefs = st.session_state.latest_session_preferences
        prefs_style = prefs.get("travel_style", "—")
        prefs_interests = ", ".join(prefs.get("interests", [])) or "—"
        prefs_pace = prefs.get("pace", "—")

        st.markdown(
            f"""
**Style:** {prefs_style}  
**Interests:** {prefs_interests}  
**Pace:** {prefs_pace}
"""
        )
    else:
        st.info("No saved preferences for this session yet.")

    st.subheader("Trip Overview")
    if st.session_state.latest_parsed_request:
        parsed = st.session_state.latest_parsed_request
        req_city = parsed.get("city", "—")
        req_days = parsed.get("duration_days", "—")
        req_style = parsed.get("trip_style", "—")
        req_interests = ", ".join(parsed.get("interests", [])) or "—"

        st.markdown(
            f"""
**Destination:** {req_city}  
**Duration:** {req_days} days  
**Style:** {req_style}  
**Interests:** {req_interests}
"""
        )
    else:
        st.caption("Trip details will appear here after generation.")

    st.subheader("Weather Forecast")
    daily = st.session_state.latest_weather_summary.get("daily", [])

    if daily:
        weather_cols = st.columns(len(daily))
        for i, day in enumerate(daily):
            icon = get_weather_icon(day.get("weather_code", 0))
            temp_min = day.get("temp_min", "")
            temp_max = day.get("temp_max", "")
            date = day.get("date", "")

            with weather_cols[i]:
                st.markdown(
                    f"""
<div style="text-align:center; padding:8px 4px; border:1px solid rgba(250,250,250,0.08); border-radius:12px;">
    <div style="font-size:11px; color:#9aa0a6;">{date}</div>
    <div style="font-size:24px; margin:4px 0;">{icon}</div>
    <div style="font-size:12px;">{temp_min}° → {temp_max}°</div>
</div>
""",
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Weather will appear here after generation.")

# ---------- input ----------
with st.container():
    col1, col2 = st.columns([4, 1])

    with col1:
        query = st.text_input(
            "Describe your trip",
            "Plan a 2-day food trip in Paris with local restaurants",
        )

    with col2:
        st.markdown("### Session")
        st.code(session_id[:8], language=None)

st.divider()

# ---------- submit ----------
if st.button("✨ Plan my trip", use_container_width=True):
    if not API_URL:
        st.error("API_URL is not configured.")
        st.stop()

    try:
        submit_response = submit_plan_trip(API_URL, query, session_id)
    except Exception:
        st.error("API server is not reachable. Start FastAPI first.")
        st.stop()

    if submit_response.status_code != 200:
        st.error(f"Agent failed to submit job: {submit_response.text}")
        st.stop()

    submit_data = submit_response.json()
    st.session_state.current_job_id = submit_data["job_id"]
    st.session_state.current_job_status = "pending"
    st.session_state.current_job_type = submit_data.get("job_type", "plan_trip")
    st.session_state.current_arch_steps = []
    st.session_state.current_arch_step = None
    st.rerun()

# ---------- polling / result ----------
if st.session_state.current_job_id:
    job_id = st.session_state.current_job_id

    top_col1, top_col2, top_col3 = st.columns(3)
    top_col1.metric("Job Status", st.session_state.current_job_status or "pending")
    top_col2.metric("Job ID", job_id[:8])
    top_col3.metric("Session", session_id[:8])

    status_box = st.empty()

    try:
        job_response = requests.get(f"{API_URL}/jobs/{job_id}", timeout=15)
    except Exception as e:
        status_box.error(f"Failed to fetch job status: {e}")
        st.stop()

    if job_response.status_code != 200:
        status_box.error(f"Failed to fetch job status: {job_response.text}")
        st.stop()

    job_data = job_response.json()
    status = job_data.get("status", "unknown")
    st.session_state.current_job_status = status
    st.session_state.current_arch_steps = job_data.get("steps", [])
    st.session_state.current_arch_step = job_data.get("current_step")

    job_type = st.session_state.current_job_type or "plan_trip"

    if st.session_state.current_arch_steps:
        with st.expander("Live architecture workflow", expanded=True):
            render_architecture_summary(
                st.session_state.current_arch_steps,
                st.session_state.current_arch_step,
            )
            st.markdown("#### Runtime architecture")
            render_architecture_svg(st.session_state.current_arch_steps, height=700)
            st.markdown("#### Stage latency view")
            render_step_timeline(st.session_state.current_arch_steps)

    if status == "pending":
        if job_type == "refine_trip":
            status_box.info("⏳ Refinement submitted. Waiting for worker...")
        else:
            status_box.info("⏳ Job submitted. Waiting for worker...")
        time.sleep(1)
        st.rerun()

    elif status == "running":
        if job_type == "refine_trip":
            status_box.info("⚙️ Worker is refining your itinerary...")
        else:
            status_box.info("⚙️ Worker is generating your itinerary...")
        time.sleep(1)
        st.rerun()

    elif status == "failed":
        status_box.error(f"❌ Job failed: {job_data.get('error', 'unknown error')}")
        st.session_state.current_job_id = None
        st.session_state.current_job_status = None
        st.session_state.current_job_type = None

    elif status == "completed":
        if job_type == "refine_trip":
            status_box.success("✅ Trip updated!")
        else:
            status_box.success("✅ Trip ready!")

        data = job_data.get("result", {})
        parsed_request = data.get("parsed_request", {})
        session_preferences = data.get("session_preferences", {})
        weather_summary = data.get("weather_summary", {})

        st.session_state.latest_parsed_request = parsed_request
        st.session_state.latest_session_preferences = session_preferences
        st.session_state.latest_weather_summary = weather_summary
        st.session_state.latest_result = data
        st.session_state.current_job_id = None
        st.session_state.current_job_status = None
        st.session_state.current_job_type = None
        st.rerun()

# ---------- render latest result ----------
if st.session_state.latest_result:
    data = st.session_state.latest_result
    parsed_request = data.get("parsed_request", {})
    raw_plan = data.get("raw_plan", {})
    travel_guide = data.get("travel_guide", "")
    trace = data.get("trace", [])
    refinement_history = data.get("refinement_history", [])
    latest_instruction = data.get("last_instruction", "")
    completed_arch_steps = st.session_state.current_arch_steps or [
        {"id": "ui", "label": "UI", "status": "done"},
        {"id": "api", "label": "FastAPI", "status": "done"},
        {"id": "redis", "label": "Redis", "status": "done"},
        {"id": "worker", "label": "Worker", "status": "done"},
        {"id": "parser_llm", "label": "Parser LLM", "status": "done"},
        {"id": "itinerary_llm", "label": "Itinerary LLM", "status": "done"},
        {"id": "geocode", "label": "Geocode", "status": "done"},
        {"id": "map", "label": "Map Render", "status": "done"},
    ]

    req_city = parsed_request.get("city", "—")
    req_days = parsed_request.get("duration_days", "—")

    st.success(f"✨ Your {req_days}-day trip in {req_city} is ready!")

    tabs = st.tabs(["📍 Itinerary", "🗺️ Map", "📖 Guide", "🧠 Reasoning", "🏗️ Architecture Live"])

    with tabs[0]:
        st.subheader("💬 Refine current trip")
        st.caption("This updates only the current itinerary. It does not overwrite your long-term session preferences.")

        if latest_instruction:
            st.info(f"Last refinement: {latest_instruction}")

        if st.session_state.pending_refine_value is not None:
            st.session_state.refine_input_value = st.session_state.pending_refine_value
            st.session_state.pending_refine_value = None

        refine_col1, refine_col2 = st.columns([5, 1])

        with refine_col1:
            st.text_input(
                "Modify this itinerary",
                key="refine_input_value",
                placeholder="e.g. Add more cafes, make it more romantic, avoid museums",
            )

        with refine_col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            refine_clicked = st.button("Refine", use_container_width=True)

        chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)

        if chip_col1.button("☕ More cafes", use_container_width=True):
            st.session_state.pending_refine_value = "Add more cafes and coffee spots"
            st.rerun()

        if chip_col2.button("❤️ More romantic", use_container_width=True):
            st.session_state.pending_refine_value = "Make the itinerary more romantic"
            st.rerun()

        if chip_col3.button("🏛️ Less museums", use_container_width=True):
            st.session_state.pending_refine_value = "Remove museums and focus on other experiences"
            st.rerun()

        if chip_col4.button("🚶 Less walking", use_container_width=True):
            st.session_state.pending_refine_value = "Reduce walking and make the trip more relaxed"
            st.rerun()

        if refine_clicked:
            instruction = st.session_state.refine_input_value.strip()

            if not instruction:
                st.warning("Please enter a refinement instruction.")
            elif not API_URL:
                st.error("API_URL is not configured.")
            else:
                try:
                    refine_response = submit_refine_trip(API_URL, session_id, instruction)
                except Exception:
                    st.error("API server is not reachable. Start FastAPI first.")
                    st.stop()

                if refine_response.status_code != 200:
                    st.error(f"Refinement failed to submit: {refine_response.text}")
                else:
                    refine_data = refine_response.json()
                    st.session_state.current_job_id = refine_data["job_id"]
                    st.session_state.current_job_status = "pending"
                    st.session_state.current_job_type = refine_data.get("job_type", "refine_trip")
                    st.session_state.last_instruction = instruction
                    st.rerun()

        if refinement_history:
            with st.expander("Refinement history"):
                for idx, item in enumerate(refinement_history, start=1):
                    st.write(f"{idx}. {item}")

        st.divider()

        icon_map = {
            "food": "🍽️",
            "culture": "🎨",
            "party": "🍸",
            "romantic": "❤️",
            "chill": "🌿",
            "family": "👨‍👩‍👧‍👦",
            "llm": "📍",
        }

        for day, places in raw_plan.items():
            st.markdown(f"## {day}")

            for idx, place in enumerate(places, start=1):
                name = place.get("name", "Unknown place")
                address = place.get("address", "")
                tags = place.get("tags", {})
                theme = tags.get("theme") or tags.get("source", "llm")
                icon = icon_map.get(theme, "📍")

                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])

                    with c1:
                        st.markdown(f"### {idx}. {icon} {name}")
                        if address:
                            st.caption(f"📍 {address}")

                    with c2:
                        st.markdown(f"**#{idx}**")
                        st.caption(theme)

    with tabs[1]:
        st.subheader("🗺️ Travel Map")
        if data.get("map_html"):
            st.components.v1.html(data["map_html"], height=500)
        else:
            st.warning("Map is unavailable for this request.")

    with tabs[2]:
        st.markdown(travel_guide)

    with tabs[3]:
        for step in trace:
            st.write(f"• {step}")

    with tabs[4]:
        st.subheader("🏗️ Architecture Live")
        st.caption("This view maps each workflow stage to its Scaleway managed service or runtime component.")

        render_architecture_summary(completed_arch_steps)
        st.markdown("#### Runtime architecture")
        render_architecture_svg(completed_arch_steps, height=700)
        st.markdown("#### Stage latency view")
        render_step_timeline(completed_arch_steps)