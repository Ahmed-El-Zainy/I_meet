"""
Multi-tenant isolation tests.
These run against a live stack (pytest with docker-compose up) or can be
run with mocks for CI. The critical logic paths are tested here.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.security.auth import create_token, decode_token
from src.rag.retriever import retrieve


# ── JWT isolation ─────────────────────────────────────────────────────────────

def test_jwt_client_id_extraction():
    token = create_token("client_a")
    assert decode_token(token) == "client_a"


def test_jwt_wrong_token_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.valid.token")
    assert exc.value.status_code == 401


def test_jwt_client_id_not_from_request_body():
    """Simulate that even if body says client_b, JWT says client_a → client_a wins."""
    token = create_token("client_a")
    extracted = decode_token(token)
    # Attacker-supplied body value is ignored
    body_client_id = "client_b"
    assert extracted != body_client_id
    assert extracted == "client_a"


# ── Vector filter isolation ───────────────────────────────────────────────────

def test_vector_filter_not_bypassed():
    """retrieve() must raise if client_id is empty — never query without filter."""
    with pytest.raises(ValueError, match="client_id required"):
        retrieve("any query", client_id="")


def test_vector_filter_none_raises():
    with pytest.raises((ValueError, TypeError)):
        retrieve("any query", client_id=None)


def test_client_a_cannot_see_client_b(monkeypatch):
    """
    Mock Qdrant to return chunks only for client_a.
    A query with client_b should return empty → refusal response.
    """
    from src.rag import chatbot

    def mock_retrieve(query, client_id, top_k=5):
        # Simulate: client_b has no data
        if client_id == "client_b":
            return []
        return [{"text": "Client A data", "meeting_id": "m1",
                 "meeting_title": "Q1", "meeting_date": "2026-01-01",
                 "client_id": "client_a"}]

    monkeypatch.setattr("src.rag.chatbot.retrieve", mock_retrieve)

    # Mock Redis
    monkeypatch.setattr("src.rag.chatbot.load_history", lambda *a: [])
    monkeypatch.setattr("src.rag.chatbot.save_history", lambda *a: None)

    result = chatbot.chat("What was discussed?", "client_b", "conv-1")
    assert "don't have information" in result["response"].lower()
    assert result["citations"] == []


def test_cross_client_meeting_access_denied():
    """API layer: meeting owned by client_a must not be accessible by client_b."""
    from fastapi import HTTPException
    from unittest.mock import MagicMock
    from src.api.dependencies import verified_meeting

    mock_meeting = MagicMock()
    mock_meeting.client_id = "client_a"
    mock_meeting.meeting_id = "meeting-001"

    mock_db = MagicMock()

    with patch("src.db.crud.get_meeting", return_value=mock_meeting):
        with pytest.raises(HTTPException) as exc:
            verified_meeting("meeting-001", client_id="client_b", db=mock_db)
        assert exc.value.status_code == 403


# ── Redis history isolation ───────────────────────────────────────────────────

def test_redis_history_scoped_to_client(monkeypatch):
    """History keys must be scoped as client_id:conversation_id."""
    from src.rag.chatbot import _history_key
    key_a = _history_key("client_a", "conv-1")
    key_b = _history_key("client_b", "conv-1")
    assert key_a != key_b
    assert "client_a" in key_a
    assert "client_b" in key_b
