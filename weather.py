import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather(lat: float, lon: float, days: int = 3) -> dict:
    response = requests.get(
        WEATHER_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "forecast_days": days,
            "timezone": "auto",
        },
        timeout=20,
    )
    data = response.json()

    if response.status_code != 200:
        raise RuntimeError(f"Weather API error: status={response.status_code}, body={data}")

    daily = data.get("daily", {})
    times = daily.get("time", [])
    codes = daily.get("weather_code", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])

    summary = []
    for i in range(min(len(times), days)):
        summary.append({
            "date": times[i],
            "weather_code": codes[i],
            "temp_max": tmax[i],
            "temp_min": tmin[i],
        })

    return {"daily": summary}