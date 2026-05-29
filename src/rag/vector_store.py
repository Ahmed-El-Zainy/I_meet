import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)

_client = None
COLLECTION = os.environ.get("QDRANT_COLLECTION", "meetings")
VECTOR_SIZE = 1024  # multilingual-e5-large output dim


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            host=os.environ.get("QDRANT_HOST", "qdrant"),
            port=int(os.environ.get("QDRANT_PORT", 6333)),
        )
        # Create collection if it doesn't exist
        existing = [c.name for c in _client.get_collections().collections]
        if COLLECTION not in existing:
            _client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
    return _client


def upsert_chunks(chunks: list[dict], vectors: list[list[float]]):
    client = get_client()
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=vec, payload=chunk)
        for chunk, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=COLLECTION, points=points)


def search(query_vector: list[float], client_id: str, top_k: int = 5) -> list[dict]:
    if not client_id:
        raise ValueError("client_id required for retrieval")
    results = get_client().search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="client_id", match=MatchValue(value=client_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in results]
