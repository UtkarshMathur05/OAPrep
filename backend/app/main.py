"""FastAPI entrypoint. Routes are thin; logic belongs in app/services."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app import errors
from app.config import CORS_ORIGINS, GEMINI_API_KEY, USE_MOCK_AI
from app.api import memory, search, reconstruct, verify, problems, contribute

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Fail at boot, not on the first request during a demo."""
    if not USE_MOCK_AI and not GEMINI_API_KEY:
        raise RuntimeError(
            "USE_MOCK_AI=false but GEMINI_API_KEY is unset. Add the key to .env, "
            "or set USE_MOCK_AI=true to run on canned responses."
        )
    yield


app = FastAPI(title="Memoize API", version="0.1.0", lifespan=lifespan)

# Explicit origins, never "*" — credentials are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.register(app)


app.include_router(memory.router)
app.include_router(search.router)
app.include_router(reconstruct.router)
app.include_router(verify.router)
app.include_router(problems.router)
app.include_router(contribute.router)


@app.get("/health")
def health():
    return {"status": "ok", "mock_ai": USE_MOCK_AI, "ai_ready": bool(GEMINI_API_KEY)}


@app.get("/health/db")
def health_db():
    """Confirms the database is reachable and says how much corpus is loaded."""
    from app.db.database import healthcheck

    try:
        return {"status": "ok", **healthcheck()}
    except Exception as exc:  # noqa: BLE001 - a probe must report, not crash
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}")
