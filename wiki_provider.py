import requests

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"


def get_city_summary(city: str) -> str:
    try:
        url = WIKI_API + city
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return ""

        data = r.json()

        return data.get("extract", "")

    except Exception:
        return ""