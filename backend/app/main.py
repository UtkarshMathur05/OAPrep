"""FastAPI entrypoint. Routes are thin; logic belongs in app/services."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.api import memory, search, reconstruct, verify, problems

app = FastAPI(title="Recollect API", version="0.1.0")

# Explicit origins, never "*" — credentials are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory.router)
app.include_router(search.router)
app.include_router(reconstruct.router)
app.include_router(verify.router)
app.include_router(problems.router)


@app.get("/health")
def health():
    return {"status": "ok"}
