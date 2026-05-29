import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_client_id, verified_meeting
from src.db.session import get_db
from src.db import crud
from src.security.encryption import decrypt_field, decrypt_bytes
from src.security.key_management import get_field_key, get_file_key
from src.pipeline.ingestion import ingest_upload
from src.workers.celery_app import process_meeting

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("/ingest")
async def ingest(
    recording_file: UploadFile = File(...),
    meeting_id: Optional[str] = Form(None),
    client_id: str = Form(...),
    meeting_title: str = Form(...),
    participants: str = Form(...),   # JSON array string
    meeting_date: Optional[str] = Form(None),
    jwt_client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    # JWT client_id always wins — ignore form client_id
    parsed_date = date.fromisoformat(meeting_date) if meeting_date else None
    parsed_participants = json.loads(participants)

    result = await ingest_upload(
        db, recording_file, meeting_id, jwt_client_id,
        meeting_title, parsed_participants, parsed_date,
    )
    process_meeting.delay(result["meeting_id"], result["raw_path"])
    return {"meeting_id": result["meeting_id"], "status": "queued"}


@router.get("/{meeting_id}/status")
def get_status(meeting=Depends(verified_meeting), db: Session = Depends(get_db)):
    status = crud.get_status(db, meeting.meeting_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return {
        "meeting_id": meeting.meeting_id,
        "status": status.status,
        "error_message": status.error_message,
        "started_at": status.started_at,
        "completed_at": status.completed_at,
    }


@router.get("/{meeting_id}/summary")
def get_summary(meeting=Depends(verified_meeting)):
    if not meeting.summary_enc:
        raise HTTPException(status_code=404, detail="Summary not ready")
    summary = json.loads(decrypt_field(meeting.summary_enc, get_field_key()))
    return summary


@router.get("/{meeting_id}/pdf")
def get_pdf(meeting=Depends(verified_meeting), db: Session = Depends(get_db)):
    artifact = crud.get_artifact(db, meeting.meeting_id, "pdf")
    if not artifact:
        raise HTTPException(status_code=404, detail="PDF not ready")
    with open(artifact.file_path, "rb") as f:
        ct = f.read()
    pdf_bytes = decrypt_bytes(ct, get_file_key(), artifact.file_iv)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{meeting.meeting_id}.pdf"'})
