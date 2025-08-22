from fastapi import Header, HTTPException
from app.auth.security import decode_token
from app.core.config import settings

def require_role(required: str):
    def dep(authorization: str = Header(None)):
        # Dev skip: allow requests without JWT if SKIP_AUTH is true
        if settings.SKIP_AUTH and settings.DEV_ASSUME_TESTER_ID:
            return {"sub": settings.DEV_ASSUME_TESTER_ID, "role": required}

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing token")
        token = authorization.split(" ", 1)[1]
        payload = decode_token(token)
        if payload.get("role") != required:
            raise HTTPException(status_code=403, detail="Forbidden")
        return payload
    return dep
