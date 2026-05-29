import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, status

_SECRET = os.environ.get("JWT_SECRET_KEY", "changeme")
_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60))


def create_token(client_id: str) -> str:
    payload = {
        "sub": client_id,
        "exp": datetime.utcnow() + timedelta(minutes=_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> str:
    """Validate JWT and return client_id. Raises HTTP 401 on failure."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        client_id: Optional[str] = payload.get("sub")
        if not client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return client_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
