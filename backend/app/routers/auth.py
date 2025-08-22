from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.models import User, Role
from app.auth.security import verify_password, create_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginIn(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(data: LoginIn):
    db: Session = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user.id, user.role.value)
    return {"access_token": token, "role": user.role.value}
