from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"


from wiki_provider import get_city_summary
import os


def load_city_knowledge(city: str) -> str:

    file_path = f"knowledge/{city.lower()}.txt"

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()

    wiki = get_city_summary(city)

    if wiki:
        return wiki

    return f"{city} is a major travel destination."