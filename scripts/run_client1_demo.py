"""
Process Client 1 Meeting 1 end-to-end and print final results.
Run inside API/worker container:
    python -m scripts.run_client1_demo
"""
from __future__ import annotations

import json
import os
import sys
import uuid

AUDIO = "/app/data/sample_meetings/client_a_meeting_1.wav"
MEETING_ID = os.environ.get("DEMO_MEETING_ID", "client1-meeting-1")
CLIENT_ID = "client_a"


def _fallback_summary(transcript: dict) -> dict:
    """Structured summary without OpenAI when API key is missing."""
    segments = transcript.get("segments", [])
    texts = [s.get("text", "") for s in segments if s.get("text")]
    preview = " ".join(texts[:8])[:500]
    speakers = sorted({s.get("speaker", "?") for s in segments})
    return {
        "executive_summary": (
            f"Meeting with {len(segments)} segments and speakers {', '.join(speakers)}. "
            f"Preview: {preview[:300]}..."
        ),
        "key_discussion_points": texts[:5] if texts else ["No transcript segments captured."],
        "decisions_made": [],
        "action_items": [],
        "open_questions": [],
        "_note": "Generated with local fallback (set OPENAI_API_KEY for LLM summary).",
    }


def summarize(transcript: dict) -> dict:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or key.startswith("<"):
        return _fallback_summary(transcript)
    from src.pipeline.summarization import summarize as llm_summarize
    return llm_summarize(transcript)


def main() -> int:
    if not os.path.exists(AUDIO):
        print(f"ERROR: missing {AUDIO}", file=sys.stderr)
        return 1

    from src.db.session import SessionLocal
    from src.db import crud
    from src.security.encryption import encrypt_field, encrypt_bytes, decrypt_field
    from src.security.key_management import get_field_key, get_file_key

    db = SessionLocal()
    field_key = get_field_key()
    file_key = get_file_key()

    title = "Client 1 — Meeting 1"
    participants = ["Speaker 1", "Speaker 2"]
    title_enc = encrypt_field(title, field_key)
    participants_enc = encrypt_field(json.dumps(participants), field_key)

    existing = crud.get_meeting(db, MEETING_ID)
    if not existing:
        crud.create_meeting(db, MEETING_ID, CLIENT_ID, title_enc, participants_enc, None)
        crud.create_status(db, MEETING_ID)
    else:
        crud.set_status(db, MEETING_ID, "queued")

    print(f"Processing: {AUDIO}")
    print(f"Meeting ID: {MEETING_ID}")

    try:
        crud.set_status(db, MEETING_ID, "transcribing")
        print("Step 1/6: Transcription (Whisper + diarization)...")
        from src.pipeline.transcription import transcribe
        transcript = transcribe(AUDIO)
        print(f"  -> {len(transcript['segments'])} segments, {transcript['duration_seconds']}s")

        crud.update_meeting_transcript(
            db, MEETING_ID,
            encrypt_field(json.dumps(transcript, ensure_ascii=False), field_key),
            transcript["duration_seconds"],
            transcript["language_mix"],
        )

        crud.set_status(db, MEETING_ID, "summarizing")
        print("Step 2/6: Summarization...")
        summary = summarize(transcript)

        crud.update_meeting_summary(
            db, MEETING_ID,
            encrypt_field(json.dumps(summary, ensure_ascii=False), field_key),
        )

        print("Step 3/6: Sentiment...")
        from src.pipeline.sentiment import analyze
        sentiment = analyze(transcript)
        crud.update_meeting_sentiment(
            db, MEETING_ID,
            encrypt_field(json.dumps(sentiment, ensure_ascii=False), field_key),
        )

        crud.set_status(db, MEETING_ID, "generating_pdf")
        print("Step 4/6: PDF...")
        from src.pipeline.pdf_generator import generate_pdf
        pdf_bytes = b""
        try:
            pdf_bytes = generate_pdf(
                title, "2026-05-31", participants, CLIENT_ID,
                summary, sentiment, transcript["segments"],
            )
        except Exception as pdf_exc:
            print(f"  PDF skipped: {pdf_exc}")

        if pdf_bytes:
            crud.set_status(db, MEETING_ID, "encrypting")
            print("Step 5/6: Encrypt PDF...")
            ct, iv_hex = encrypt_bytes(pdf_bytes, file_key)
            pdf_dir = os.environ.get("ENCRYPTED_PDF_DIR", "/app/storage/pdfs")
            os.makedirs(pdf_dir, exist_ok=True)
            artifact_id = str(uuid.uuid4())
            file_path = os.path.join(pdf_dir, f"{artifact_id}.enc")
            with open(file_path, "wb") as f:
                f.write(ct)
            crud.create_artifact(db, artifact_id, MEETING_ID, "pdf", file_path, iv_hex)
        else:
            artifact_id = None
            print("Step 5/6: Skipped PDF storage")

        crud.set_status(db, MEETING_ID, "embedding")
        print("Step 6/6: Embeddings...")
        from src.rag.embeddings import embed_meeting
        embed_meeting(MEETING_ID, CLIENT_ID, title, "2026-05-31", transcript, summary)

        crud.set_status(db, MEETING_ID, "complete")
        print("\n=== FINAL RESULTS ===\n")
        print(json.dumps({
            "meeting_id": MEETING_ID,
            "client_id": CLIENT_ID,
            "title": title,
            "status": "complete",
            "language_mix": transcript.get("language_mix"),
            "duration_seconds": transcript.get("duration_seconds"),
            "transcript_sample": transcript["segments"][:5],
            "summary": summary,
            "sentiment_overall": sentiment.get("overall"),
            "sentiment_per_speaker": {
                k: v.get("overall") for k, v in sentiment.get("per_speaker", {}).items()
            },
            "pdf_bytes": len(pdf_bytes),
            "pdf_artifact": artifact_id,
        }, ensure_ascii=False, indent=2))
        return 0

    except Exception as exc:
        crud.set_status(db, MEETING_ID, "failed", error=str(exc))
        print(f"\nFAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
