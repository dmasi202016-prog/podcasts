"""FastAPI application entrypoint."""

import re
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from podcast_shorts.api.dependencies import is_postgres_backend, set_checkpointer
from podcast_shorts.api.routes import router
from podcast_shorts.config import settings

logger = structlog.get_logger()

# Resolve project root paths for static file serving
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_OUTPUT_DIR = _PROJECT_ROOT / "output"
_ASSETS_DIR = _PROJECT_ROOT / "assets"


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------

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


def _build_origin_regex(origins: set[str]) -> str | None:
    """Build a regex that matches configured origins AND their subdomains.

    For example, "https://my-app.vercel.app" generates a pattern that also
    matches Vercel preview URLs like "https://my-app-git-xxx.vercel.app".
    """
    patterns: list[str] = []
    for origin in origins:
        if "vercel.app" in origin:
            # Match any *.vercel.app URL (production + preview deployments)
            patterns.append(r"https://[a-zA-Z0-9\-]+\.vercel\.app")
        elif "railway.app" in origin:
            # Match any *.railway.app URL
            patterns.append(r"https://[a-zA-Z0-9\-]+\.up\.railway\.app")
    if not patterns:
        return None
    # Deduplicate and combine
    unique = list(set(patterns))
    return "^(" + "|".join(unique) + ")$"


_ALLOWED_ORIGINS = _get_allowed_origins()
_ORIGIN_REGEX = _build_origin_regex(_ALLOWED_ORIGINS)


class FixCorsOriginMiddleware(BaseHTTPMiddleware):
    """Ensure Access-Control-Allow-Origin is set for cross-origin requests.

    Handles both exact-match origins and regex-matched origins (e.g. Vercel previews).
    """

    def __init__(self, app: ASGIApp, allowed_origins: set[str], origin_regex: str | None = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.origin_pattern = re.compile(origin_regex) if origin_regex else None

    def _is_allowed(self, origin: str) -> bool:
        if origin in self.allowed_origins:
            return True
        if self.origin_pattern and self.origin_pattern.match(origin):
            return True
        return False

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin and self._is_allowed(origin):
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — initialize and cleanup resources."""
    logger.info(
        "app.startup",
        allowed_origins=sorted(_ALLOWED_ORIGINS),
        origin_regex=_ORIGIN_REGEX,
    )

    if is_postgres_backend():
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        # Supabase uses PgBouncer (transaction mode) which doesn't support
        # prepared statements. prepare_threshold=0 disables them.
        pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            kwargs={"prepare_threshold": 0, "autocommit": True},
        )
        await pool.open()
        try:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            set_checkpointer(saver)
            logger.info("app.checkpointer", backend="postgres")
            yield
        finally:
            await pool.close()
    else:
        from langgraph.checkpoint.memory import InMemorySaver

        saver = InMemorySaver()
        set_checkpointer(saver)
        logger.info("app.checkpointer", backend="memory")
        yield

    logger.info("app.shutdown")


app = FastAPI(
    title="Podcast Shorts Generator",
    description="AI-powered podcast shorts generation platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — allow_origin_regex covers Vercel preview URLs automatically
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_ALLOWED_ORIGINS),
    allow_origin_regex=_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Ensure Access-Control-Allow-Origin header is always set (fixes some CORS edge cases)
app.add_middleware(FixCorsOriginMiddleware, allowed_origins=_ALLOWED_ORIGINS, origin_regex=_ORIGIN_REGEX)

app.include_router(router)

# Static file serving for output and assets
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files/output", StaticFiles(directory=str(_OUTPUT_DIR)), name="output")
app.mount("/files/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
