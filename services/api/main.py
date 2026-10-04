import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from api.router import api_router
from core.security import jwt_secret
from db.database import async_session_maker, engine

@asynccontextmanager
async def lifespan(app):
    jwt_secret()
    if not os.getenv("DATABASE_URL") or not os.getenv("BOT_TOKEN"):
        raise RuntimeError("DATABASE_URL and BOT_TOKEN must be configured")
    yield
    await engine.dispose()

app = FastAPI(title="Kontur API", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")

@app.middleware("http")
async def no_private_cache(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/ready")
async def readiness():
    try:
        async with async_session_maker() as db:
            await db.execute(text("SELECT id FROM sessions LIMIT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
