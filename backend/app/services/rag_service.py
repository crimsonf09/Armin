from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings

_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=10,
        )
    return _client


def ensure_qdrant_collection() -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == settings.qdrant_collection for c in collections)
    if exists:
        return

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=models.VectorParams(
            size=settings.qdrant_vector_size,
            distance=models.Distance.COSINE,
        ),
    )


def close_qdrant_client() -> None:
    global _client
    if _client is not None:
        _client.close()
    _client = None
