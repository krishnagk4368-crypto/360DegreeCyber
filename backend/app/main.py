from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import engine
from app.models.models import Base
from app.routers.tester import router as tester_router
from app.routers.auth import router as auth_router

app = FastAPI(title="360 Cybersecurity Backend (Tester)")

# Create tables on startup (simple for beginners; later use Alembic)
Base.metadata.create_all(bind=engine)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(auth_router)
app.include_router(tester_router)
