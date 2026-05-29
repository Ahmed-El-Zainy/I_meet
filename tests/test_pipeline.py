"""
Pipeline unit tests — mock heavy ML models, test logic and data flow.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

KEY = "a" * 64


# ── Ingestion ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingest_unsupported_file_type():
    from fastapi import HTTPException
    from src.pipeline.ingestion import ingest_upload

    mock_file = MagicMock()
    mock_file.filename = "recording.exe"
    mock_file.read = MagicMock(return_value=b"data")

    with pytest.raises(HTTPException) as exc:
        await ingest_upload(MagicMock(), mock_file, None, "client_a",
                            "Test", ["Alice"], None)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_ingest_creates_db_records(tmp_path, monkeypatch):
    from src.pipeline.ingestion import ingest_upload

    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", KEY)

    mock_file = MagicMock()
    mock_file.filename = "meeting.mp4"
    mock_file.read = MagicMock(return_value=b"fake audio")

    mock_db = MagicMock()
    created = {}

    def fake_create_meeting(db, meeting_id, client_id, title_enc, participants_enc, meeting_date=None):
        created["meeting_id"] = meeting_id
        created["client_id"] = client_id
        return MagicMock(meeting_id=meeting_id)

    monkeypatch.setattr("src.pipeline.ingestion.crud.create_meeting", fake_create_meeting)
    monkeypatch.setattr("src.pipeline.ingestion.crud.create_status", lambda *a: None)

    result = await ingest_upload(
        mock_db, mock_file, "test-id", "client_a",
        "My Meeting", ["Alice", "Bob"], None,
        upload_dir=str(tmp_path),
    )

    assert result["meeting_id"] == "test-id"
    assert created["client_id"] == "client_a"


# ── Summarization ─────────────────────────────────────────────────────────────

def test_summarize_returns_required_keys(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    expected = {
        "executive_summary": "Summary.",
        "key_discussion_points": ["Point 1"],
        "decisions_made": [],
        "action_items": [],
        "open_questions": [],
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(expected)

    with patch("src.pipeline.summarization.OpenAI", return_value=mock_client):
        from src.pipeline.summarization import summarize
        result = summarize({"segments": [{"start": 0, "end": 5, "speaker": "S0", "text": "Hello"}]})

    for key in expected:
        assert key in result


# ── Sentiment ─────────────────────────────────────────────────────────────────

def test_sentiment_output_schema(monkeypatch):
    mock_scores = [[
        {"label": "positive", "score": 0.7},
        {"label": "neutral", "score": 0.2},
        {"label": "negative", "score": 0.1},
    ]]

    with patch("src.pipeline.sentiment._get_pipeline") as mock_pipe:
        mock_pipe.return_value = MagicMock(return_value=mock_scores)
        from src.pipeline.sentiment import analyze
        result = analyze({
            "segments": [{"start": 0, "end": 10, "speaker": "S0", "text": "Great meeting!"}],
            "duration_seconds": 10,
        })

    assert "overall" in result
    assert "per_speaker" in result
    assert "notable_moments" in result
    assert set(result["overall"].keys()) == {"positive", "neutral", "negative"}


# ── PDF generation ────────────────────────────────────────────────────────────

def test_pdf_generates_bytes(monkeypatch):
    with patch("src.pipeline.pdf_generator.HTML") as mock_html:
        mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
        from src.pipeline.pdf_generator import generate_pdf
        result = generate_pdf(
            "Test Meeting", "2026-01-01", ["Alice"], "client_a",
            {"executive_summary": "Summary", "key_discussion_points": [],
             "decisions_made": [], "action_items": [], "open_questions": []},
            {"overall": {"positive": 0.5, "neutral": 0.3, "negative": 0.2}},
            [{"start": 0, "end": 5, "speaker": "S0", "text": "Hello"}],
        )
    assert result == b"%PDF-1.4 fake"
