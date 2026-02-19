"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from podcast_shorts.api.dependencies import get_checkpointer
from podcast_shorts.api.routes import router
from podcast_shorts.config import settings

logger = structlog.get_logger()

# Resolve project root paths for static file serving
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_DIR = _PROJECT_ROOT / "output"
_ASSETS_DIR = _PROJECT_ROOT / "assets"


class FixCorsOriginMiddleware(BaseHTTPMiddleware):
    """Ensure Access-Control-Allow-Origin is set for cross-origin requests."""

    def __init__(self, app: ASGIApp, allowed_origins: set[str]):
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and origin in self.allowed_origins:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — initialize and cleanup resources."""
    logger.info("app.startup")
    checkpointer = get_checkpointer()
    async with checkpointer:
        yield
    logger.info("app.shutdown")


app = FastAPI(
    title="Podcast Shorts Generator",
    description="AI-powered podcast shorts generation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for Next.js frontend
_DEFAULT_ORIGINS = {
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
}


def _get_allowed_origins() -> set[str]:
    origins = set(_DEFAULT_ORIGINS)
    if settings.allowed_origins:
        origins.update(o.strip() for o in settings.allowed_origins.split(",") if o.strip())
    return origins


_ALLOWED_ORIGINS = _get_allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Ensure Access-Control-Allow-Origin is always set (fixes some CORS edge cases)
app.add_middleware(FixCorsOriginMiddleware, allowed_origins=_ALLOWED_ORIGINS)

app.include_router(router)

# Static file serving for output and assets
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files/output", StaticFiles(directory=str(_OUTPUT_DIR)), name="output")
app.mount("/files/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
