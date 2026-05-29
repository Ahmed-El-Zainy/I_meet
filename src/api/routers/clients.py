from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_client_id
from src.db.session import get_db
from src.db import crud
from src.security.encryption import decrypt_field
from src.security.key_management import get_field_key

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("/{client_id}/meetings")
def list_meetings(
    client_id: str,
    jwt_client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    if client_id != jwt_client_id:
        raise HTTPException(status_code=403, detail="Access denied")

    meetings = crud.get_meetings_for_client(db, client_id)
    key = get_field_key()
    return [
        {
            "meeting_id": m.meeting_id,
            "meeting_title": decrypt_field(m.meeting_title_enc, key),
            "meeting_date": str(m.meeting_date) if m.meeting_date else None,
            "duration_seconds": m.duration_seconds,
            "created_at": m.created_at,
        }
        for m in meetings
    ]
