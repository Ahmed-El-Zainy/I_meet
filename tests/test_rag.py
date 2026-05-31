"""
RAG retrieval + chatbot tests.
"""
import pytest
from unittest.mock import patch, MagicMock


# ── Retriever ─────────────────────────────────────────────────────────────────

def test_retriever_requires_client_id():
    from src.rag.retriever import retrieve
    with pytest.raises(ValueError):
        retrieve("query", client_id="")


def test_retriever_calls_search_with_filter(monkeypatch):
    captured = {}

    def mock_search(query_vector, client_id, top_k):
        captured["client_id"] = client_id
        return [{"text": "chunk", "meeting_id": "m1", "meeting_title": "T",
                 "meeting_date": "2026-01-01", "client_id": client_id}]

    monkeypatch.setattr("src.rag.retriever.embed_texts", lambda texts, **kw: [[0.1] * 1024])
    monkeypatch.setattr("src.rag.retriever.search", mock_search)

    from src.rag.retriever import retrieve
    results = retrieve("test query", "client_a")
    assert captured["client_id"] == "client_a"
    assert len(results) == 1


# ── Chatbot refusal ───────────────────────────────────────────────────────────

def test_refusal_on_unknown_topic(monkeypatch):
    monkeypatch.setattr("src.rag.chatbot.retrieve", lambda *a, **kw: [])
    monkeypatch.setattr("src.rag.chatbot.load_history", lambda *a: [])

    from src.rag.chatbot import chat
    result = chat("What is the weather?", "client_a", "conv-1")
    assert "don't have information" in result["response"].lower()
    assert result["citations"] == []
    assert result["source_meeting_ids"] == []


def test_response_includes_citations(monkeypatch):
    chunks = [{
        "text": "Ahmed will prepare the report by Friday.",
        "meeting_id": "m1",
        "meeting_title": "Q1 Planning",
        "meeting_date": "2026-02-14",
        "client_id": "client_a",
    }]
    monkeypatch.setattr("src.rag.chatbot.retrieve", lambda *a, **kw: chunks)
    monkeypatch.setattr("src.rag.chatbot.load_history", lambda *a: [])
    monkeypatch.setattr("src.rag.chatbot.save_history", lambda *a: None)

    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value.choices[0].message.content = (
        "Ahmed will prepare the report. [Meeting: Q1 Planning, 2026-02-14]"
    )

    with patch("openai.OpenAI", return_value=mock_openai):
        import os
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "test"
        from src.rag.chatbot import chat
        result = chat("What are Ahmed's action items?", "client_a", "conv-2")

    assert len(result["citations"]) > 0
    assert "m1" in result["source_meeting_ids"]


def test_cross_meeting_synthesis(monkeypatch):
    """Multiple chunks from different meetings should all appear in source_meeting_ids."""
    chunks = [
        {"text": "Action: Ahmed to review budget.", "meeting_id": "m1",
         "meeting_title": "Meeting 1", "meeting_date": "2026-01-01", "client_id": "client_a"},
        {"text": "Action: Ahmed to send report.", "meeting_id": "m2",
         "meeting_title": "Meeting 2", "meeting_date": "2026-02-01", "client_id": "client_a"},
    ]
    monkeypatch.setattr("src.rag.chatbot.retrieve", lambda *a, **kw: chunks)
    monkeypatch.setattr("src.rag.chatbot.load_history", lambda *a: [])
    monkeypatch.setattr("src.rag.chatbot.save_history", lambda *a: None)

    mock_openai = MagicMock()
    mock_openai.chat.completions.create.return_value.choices[0].message.content = "Ahmed has two action items."

    with patch("openai.OpenAI", return_value=mock_openai):
        import os
        os.environ["LLM_PROVIDER"] = "openai"
        os.environ["OPENAI_API_KEY"] = "test"
        from src.rag.chatbot import chat
        result = chat("Summarize Ahmed's action items", "client_a", "conv-3")

    assert "m1" in result["source_meeting_ids"]
    assert "m2" in result["source_meeting_ids"]


def test_arabic_query(monkeypatch):
    """Arabic query should pass through embed + retrieve without error."""
    monkeypatch.setattr("src.rag.retriever.embed_texts", lambda texts, **kw: [[0.1] * 1024])
    monkeypatch.setattr("src.rag.retriever.search", lambda *a, **kw: [])

    from src.rag.retriever import retrieve
    result = retrieve("ما هي قرارات الاجتماع؟", "client_a")
    assert result == []
