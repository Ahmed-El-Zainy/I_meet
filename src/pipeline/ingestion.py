import os
import uuid
import json
from datetime import date
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from src.db import crud
from src.security.encryption import encrypt_field
from src.security.key_management import get_field_key

ALLOWED_EXTENSIONS = {"mp3", "mp4", "wav", "m4a", "webm"}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def ingest_upload(
    db: Session,
    recording_file: UploadFile,
    meeting_id: str | None,
    client_id: str,
    meeting_title: str,
    participants: list[str],
    meeting_date: date | None,
    upload_dir: str = "/tmp/uploads",
) -> dict:
    if _ext(recording_file.filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    meeting_id = meeting_id or str(uuid.uuid4())
    os.makedirs(upload_dir, exist_ok=True)
    raw_path = os.path.join(upload_dir, f"{meeting_id}.{_ext(recording_file.filename)}")

    with open(raw_path, "wb") as f:
        f.write(await recording_file.read())

    key = get_field_key()
    title_enc = encrypt_field(meeting_title, key)
    participants_enc = encrypt_field(json.dumps(participants, ensure_ascii=False), key)

    crud.create_meeting(db, meeting_id, client_id, title_enc, participants_enc, meeting_date)
    crud.create_status(db, meeting_id)

    return {"meeting_id": meeting_id, "raw_path": raw_path, "status": "queued"}
