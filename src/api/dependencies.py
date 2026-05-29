from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.security.auth import decode_token

_bearer = HTTPBearer()


def get_current_client_id(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Extract and validate client_id from JWT. Never trust request body."""
    return decode_token(creds.credentials)


def verified_meeting(
    meeting_id: str,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Return meeting only if it belongs to the authenticated client."""
    from src.db.crud import get_meeting
    meeting = get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.client_id != client_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return meeting
