import os
import json
from typing import Any

import redis

from src.rag.retriever import retrieve

_redis = None
HISTORY_TTL = 3600 * 24  # 24 h


def _get_redis():
    global _redis
    if _redis is None:
        _redis = redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
    return _redis


def _history_key(client_id: str, conversation_id: str) -> str:
    return f"{client_id}:{conversation_id}:history"


def load_history(client_id: str, conversation_id: str) -> list[dict]:
    raw = _get_redis().get(_history_key(client_id, conversation_id))
    return json.loads(raw) if raw else []


def save_history(client_id: str, conversation_id: str, history: list[dict]):
    key = _history_key(client_id, conversation_id)
    _get_redis().setex(key, HISTORY_TTL, json.dumps(history, ensure_ascii=False))


def clear_history(client_id: str, conversation_id: str):
    _get_redis().delete(_history_key(client_id, conversation_id))


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        label = f"[Meeting: {c.get('meeting_title', '?')}, {c.get('meeting_date', '?')}]"
        parts.append(f"[{i}] {label}\n{c['text']}")
    return "\n\n".join(parts)


def chat(message: str, client_id: str, conversation_id: str) -> dict[str, Any]:
    """
    Full RAG chat turn. Returns:
      {"response": str, "citations": list[str], "source_meeting_ids": list[str]}
    """
    chunks = retrieve(message, client_id, top_k=5)

    if not chunks:
        return {
            "response": "I don't have information about that in your meetings.",
            "citations": [],
            "source_meeting_ids": [],
        }

    context = _build_context(chunks)
    history = load_history(client_id, conversation_id)

    system = (
        f"You are a meeting assistant for {client_id}. "
        "Answer ONLY from the provided context. "
        "If the answer is not in the context, say so explicitly. "
        "Never mention other clients. "
        "Cite sources as [Meeting: <title>, <date>]."
    )

    messages = [{"role": "system", "content": system}]
    messages += history[-10:]  # last 5 turns
    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {message}",
    })

    provider = os.environ.get("LLM_PROVIDER", "openai")
    model = os.environ.get("LLM_MODEL", "gpt-4o")

    if provider == "openai":
        from openai import OpenAI
        resp = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).chat.completions.create(
            model=model, messages=messages, temperature=0.3
        )
        answer = resp.choices[0].message.content
    elif provider == "ollama":
        import requests
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        answer = r.json()["message"]["content"]
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")

    # Update history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})
    save_history(client_id, conversation_id, history)

    citations = list({
        f"[Meeting: {c.get('meeting_title', '?')}, {c.get('meeting_date', '?')}]"
        for c in chunks
    })
    source_ids = list({c.get("meeting_id") for c in chunks if c.get("meeting_id")})

    return {"response": answer, "citations": citations, "source_meeting_ids": source_ids}
