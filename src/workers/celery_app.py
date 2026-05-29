import os
import json
import uuid

from celery import Celery

from src.db.session import SessionLocal
from src.db import crud
from src.security.encryption import encrypt_field, encrypt_bytes
from src.security.key_management import get_field_key, get_file_key

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
app = Celery("workers", broker=redis_url, backend=redis_url)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"


@app.task(bind=True, max_retries=2)
def process_meeting(self, meeting_id: str, audio_path: str):
    db = SessionLocal()
    try:
        field_key = get_field_key()
        file_key = get_file_key()

        # ── 1. Transcription ──────────────────────────────────────────────────
        crud.set_status(db, meeting_id, "transcribing")
        from src.pipeline.transcription import transcribe
        transcript = transcribe(audio_path)

        transcript_enc = encrypt_field(json.dumps(transcript, ensure_ascii=False), field_key)
        crud.update_meeting_transcript(
            db, meeting_id, transcript_enc,
            transcript["duration_seconds"], transcript["language_mix"]
        )

        # ── 2. Summarization ──────────────────────────────────────────────────
        crud.set_status(db, meeting_id, "summarizing")
        from src.pipeline.summarization import summarize
        summary = summarize(transcript)

        summary_enc = encrypt_field(json.dumps(summary, ensure_ascii=False), field_key)
        crud.update_meeting_summary(db, meeting_id, summary_enc)

        # ── 3. Sentiment ──────────────────────────────────────────────────────
        from src.pipeline.sentiment import analyze
        sentiment = analyze(transcript)

        sentiment_enc = encrypt_field(json.dumps(sentiment, ensure_ascii=False), field_key)
        crud.update_meeting_sentiment(db, meeting_id, sentiment_enc)

        # ── 4. PDF generation ─────────────────────────────────────────────────
        crud.set_status(db, meeting_id, "generating_pdf")
        meeting = crud.get_meeting(db, meeting_id)
        from src.security.encryption import decrypt_field
        title = decrypt_field(meeting.meeting_title_enc, field_key)
        participants = json.loads(decrypt_field(meeting.participants_enc, field_key))
        meeting_date = str(meeting.meeting_date) if meeting.meeting_date else ""

        from src.pipeline.pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(
            title, meeting_date, participants, meeting.client_id,
            summary, sentiment, transcript["segments"]
        )

        # ── 5. Encrypt & store PDF ────────────────────────────────────────────
        crud.set_status(db, meeting_id, "encrypting")
        ct, iv_hex = encrypt_bytes(pdf_bytes, file_key)

        pdf_dir = os.environ.get("ENCRYPTED_PDF_DIR", "/app/storage/pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        artifact_id = str(uuid.uuid4())
        file_path = os.path.join(pdf_dir, f"{artifact_id}.enc")
        with open(file_path, "wb") as f:
            f.write(ct)

        crud.create_artifact(db, artifact_id, meeting_id, "pdf", file_path, iv_hex)

        # ── 6. Embeddings ─────────────────────────────────────────────────────
        crud.set_status(db, meeting_id, "embedding")
        from src.rag.embeddings import embed_meeting
        embed_meeting(meeting_id, meeting.client_id, title, meeting_date, transcript, summary)

        crud.set_status(db, meeting_id, "complete")

    except Exception as exc:
        crud.set_status(db, meeting_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()
