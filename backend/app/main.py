"""
FastAPI application entry point.

Startup order:
  1. Load settings from .env (via app/config.py, imported transitively)
  2. Configure structured logging
  3. Create the FastAPI app with metadata
  4. Register CORS middleware (frontend origin only)
  5. Mount routers:
       /oauth  → GitHub OAuth flow + Auth0 callback
       /agent  → Protected AI agent endpoints
       /health → Liveness probe
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import agent, oauth


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info(
        "AnonSkill API started.  Auth0 domain: %s  Audience: %s",
        settings.auth0_domain,
        settings.auth0_audience,
    )
    yield


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    lifespan=lifespan,
    title="AnonSkill API",
    description=(
        "Analyzes a user's private GitHub repositories via Auth0 Token Vault "
        "and returns structured skill assessments — no raw source code, no PII."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ──────────────────────────────────────────────────────────────────────
# Only the known frontend origin is allowed.
# Adjust `allow_origins` for staging / production deployments.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(oauth.router)
app.include_router(agent.router)


# ── Health probe ──────────────────────────────────────────────────────────────


@app.get("/health", tags=["Infra"], summary="Liveness probe")
def health() -> dict[str, str]:
    """Returns 200 OK as long as the process is running."""
    return {"status": "ok"}
