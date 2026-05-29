from src.rag.embeddings import embed_texts
from src.rag.vector_store import search


def retrieve(query: str, client_id: str, top_k: int = 5) -> list[dict]:
    """Embed query and retrieve top_k chunks scoped to client_id.

    Raises ValueError if client_id is missing — never falls back to unfiltered search.
    """
    if not client_id:
        raise ValueError("client_id required for retrieval")
    vector = embed_texts([query], is_query=True)[0]
    return search(vector, client_id, top_k)
