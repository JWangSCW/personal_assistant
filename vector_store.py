import os
import math
import requests
from dotenv import load_dotenv

load_dotenv()

SCW_SECRET_KEY = os.getenv("SCW_SECRET_KEY")
SCW_EMBEDDING_MODEL = os.getenv("SCW_EMBEDDING_MODEL", "bge-multilingual-gemma2")
SCW_EMBEDDING_API_URL = "https://api.scaleway.ai/v1/embeddings"

documents = []
vectors = []


def get_embedding(text: str) -> list[float]:
    if not SCW_SECRET_KEY:
        raise ValueError("SCW_SECRET_KEY missing in .env")

    payload = {
        "model": SCW_EMBEDDING_MODEL,
        "input": text,
    }

    headers = {
        "Authorization": f"Bearer {SCW_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        SCW_EMBEDDING_API_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"Scaleway Embeddings API returned non-JSON response: "
            f"status={response.status_code}, body={response.text}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Scaleway Embeddings API error: status={response.status_code}, body={data}"
        )

    if "data" not in data or not data["data"]:
        raise RuntimeError(f"Unexpected embedding response format: {data}")

    return data["data"][0]["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def add_document(text: str):
    embedding = get_embedding(text)
    documents.append(text)
    vectors.append(embedding)


def add_documents(texts: list[str]):
    for text in texts:
        add_document(text)


def clear_store():
    documents.clear()
    vectors.clear()


def search(query: str, top_k: int = 3) -> list[str]:
    if not documents:
        return []

    q = get_embedding(query)

    scores = []
    for i, v in enumerate(vectors):
        score = cosine_similarity(q, v)
        scores.append((score, documents[i]))

    scores.sort(key=lambda x: x[0], reverse=True)

    return [doc for _, doc in scores[:top_k]]