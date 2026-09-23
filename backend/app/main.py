import asyncio
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import Base, engine
from app.migrations import run_startup_migrations
from app.routers import auth, settings, checks, admin
from app.security_headers import SecurityHeadersMiddleware
from app.error_handling import unhandled_exception_handler
from app.body_size_limit import BodySizeLimitMiddleware
from app.event_bus import bus

load_dotenv()

Base.metadata.create_all(bind=engine)
run_startup_migrations(engine)

app = FastAPI(title="FraudLens API")


@app.on_event("startup")
async def _bind_event_bus_loop():
    # See app/event_bus.py — needed so publish() calls made from sync
    # request-handler threads can safely hand events to SSE subscribers
    # living on this loop.
    bus.bind_loop(asyncio.get_running_loop())

app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(checks.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"service": "FraudLens API", "status": "running"}


@app.get("/health")
def health_check():
    from sqlalchemy import text
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}
    finally:
        db.close()
