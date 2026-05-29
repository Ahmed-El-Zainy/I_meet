import os
from typing import Any

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(
            os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-large"),
            device=os.environ.get("EMBEDDING_DEVICE", "cpu"),
        )
    return _model


def embed_texts(texts: list[str], is_query: bool = False) -> list[list[float]]:
    """Embed a list of texts. E5 models require 'query: ' / 'passage: ' prefix."""
    prefix = "query: " if is_query else "passage: "
    prefixed = [prefix + t for t in texts]
    return _get_model().encode(prefixed, normalize_embeddings=True).tolist()


def _chunk_transcript(segments: list[dict], max_tokens: int = 400, overlap: int = 50) -> list[dict]:
    """Chunk by speaker turn, respecting max_tokens (approx by word count)."""
    chunks = []
    buf_words = []
    buf_speaker = None
    buf_start = None

    def flush():
        if buf_words:
            chunks.append({
                "text": " ".join(buf_words),
                "speaker": buf_speaker,
                "timestamp_start": buf_start,
                "chunk_type": "transcript",
            })

    for seg in segments:
        words = seg["text"].split()
        if buf_speaker != seg["speaker"] or len(buf_words) + len(words) > max_tokens:
            flush()
            buf_words = buf_words[-overlap:] if buf_words else []
            buf_speaker = seg["speaker"]
            buf_start = seg["start"]
        buf_words.extend(words)

    flush()
    return chunks


def embed_meeting(meeting_id: str, client_id: str, title: str, meeting_date: str,
                  transcript: dict[str, Any], summary: dict[str, Any]):
    """Chunk transcript + summary sections, embed, and store in Qdrant."""
    from src.rag.vector_store import upsert_chunks

    chunks = []

    # Transcript chunks
    for c in _chunk_transcript(transcript["segments"]):
        c.update({"meeting_id": meeting_id, "client_id": client_id,
                  "meeting_title": title, "meeting_date": meeting_date})
        chunks.append(c)

    # Summary section chunks
    for section, chunk_type in [
        ("executive_summary", "summary"),
        ("action_items", "action_items"),
        ("decisions_made", "summary"),
        ("key_discussion_points", "summary"),
        ("open_questions", "summary"),
    ]:
        val = summary.get(section)
        if not val:
            continue
        text = val if isinstance(val, str) else "\n".join(
            str(item) if not isinstance(item, dict) else
            " | ".join(str(v) for v in item.values())
            for item in val
        )
        chunks.append({
            "meeting_id": meeting_id, "client_id": client_id,
            "meeting_title": title, "meeting_date": meeting_date,
            "chunk_type": chunk_type, "speaker": None,
            "timestamp_start": None, "text": text,
        })

    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts, is_query=False)
    upsert_chunks(chunks, vectors)
