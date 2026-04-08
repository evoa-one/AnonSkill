"""
Agent router – protected endpoints for AI agent operations.

Endpoints
─────────
POST /agent/analyze
    Metadata-only skill report (languages, architecture patterns).

POST /agent/verify
    AI-powered verification report.  Fetches the top 3 most active repos,
    collects quantitative metrics, and calls Gemini to produce a structured
    VerificationReport JSON.

GET /agent/vault/status
    Returns {connected: true/false} — whether a GitHub token is stored in
    Token Vault for the authenticated user.

Token Vault flow
─────────────────
Every protected endpoint uses get_auth_context() which returns both the
user's sub and the raw Auth0 access token.  The access token is passed
directly to get_github_token_from_vault() as the subject_token for the
Token Exchange grant — Auth0 uses it to look up and decrypt the stored
GitHub token without any M2M application or Management API call.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.jwt_validator import AuthContext, get_auth_context
from app.models.schemas import SkillReport, VerificationReport, VerifyRequest
from app.services import token_store
from app.services.agent_analyzer import generate_verification_report, get_repo_list
from app.services.github_client import build_skill_report
from app.services.token_vault import get_github_token_from_vault

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])


# ── Helper: resolve GitHub token with standard error mapping ──────────────────


async def _resolve_github_token(auth: AuthContext) -> str:
    """
    Look up the stored refresh token for this user, then exchange it via
    Auth0 Token Vault to get the GitHub access token.
    """
    refresh_token = token_store.get(auth.user_id)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No session found. Please re-authenticate via /oauth/github/authorize.",
        )
    try:
        return await get_github_token_from_vault(refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Token Vault exchange failed for user %s: %s", auth.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve GitHub token from Auth0 Token Vault.",
        ) from exc


# ── GET /agent/repos ──────────────────────────────────────────────────────────


@router.get(
    "/repos",
    response_model=dict,
    summary="List repos available for verification",
)
async def list_repos(
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    github_token = await _resolve_github_token(auth)
    try:
        github_username, repos = await get_repo_list(github_token)
    except Exception as exc:
        logger.error("Failed to fetch repo list for user %s: %s", auth.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch repositories from GitHub.",
        ) from exc
    finally:
        github_token = ""
    return {
        "github_username": github_username,
        "repos": [r.model_dump() for r in repos],
    }


# ── POST /agent/analyze ───────────────────────────────────────────────────────


@router.post(
    "/analyze",
    response_model=SkillReport,
    summary="Analyze GitHub repositories and return a metadata skill report",
    description=(
        "Protected endpoint – requires a valid Auth0 Bearer token.\n\n"
        "Returns detected languages, architecture patterns, and per-repo summaries. "
        "No LLM is involved; no raw source code is ever returned."
    ),
)
async def analyze_skills(
    auth: AuthContext = Depends(get_auth_context),
    max_repos: int = 30,
) -> SkillReport:
    """Vault token exchange → scan repos → return SkillReport."""
    logger.info("Metadata skill analysis requested for user: %s", auth.user_id)
    github_token = await _resolve_github_token(auth)

    try:
        report = await build_skill_report(github_token=github_token, max_repos=max_repos)
    except Exception as exc:
        logger.error("GitHub analysis failed for user %s: %s", auth.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API call failed. The token may have been revoked.",
        ) from exc
    finally:
        github_token = ""  # noqa: S105  # removes local reference; GC handles memory

    logger.info(
        "Skill report done for %s: %d repos, %d skills.",
        auth.user_id,
        report.total_repos_analyzed,
        len(report.detected_skills),
    )
    return report


# ── POST /agent/verify ────────────────────────────────────────────────────────


@router.post(
    "/verify",
    response_model=VerificationReport,
    summary="Generate an AI-powered zero-knowledge skill verification report",
    description=(
        "Protected endpoint – requires a valid Auth0 Bearer token.\n\n"
        "**Pipeline:**\n"
        "1. Exchanges the Auth0 Bearer token for the GitHub token via **Token Vault**.\n"
        "2. Fetches all owned non-fork repositories; selects the **top 3 by activity**.\n"
        "3. Collects quantitative metrics: language distribution, commit frequency "
        "(90-day + annual), repo size, CI signals.\n"
        "4. Sends the metrics to **Gemini** — no source code — and receives a "
        "structured `VerificationReport` JSON.\n\n"
        "The GitHub token is overwritten in memory after Step 3. "
        "Raw source code, commit messages, and email addresses are **never** collected."
    ),
)
async def verify_skills(
    body: VerifyRequest = VerifyRequest(),
    auth: AuthContext = Depends(get_auth_context),
) -> VerificationReport:
    """
    Full AI verification pipeline:
      Token Vault exchange → top-3 repo metrics → Gemini → VerificationReport
    """
    logger.info(
        "AI verification requested for user: %s  excluded_languages: %s",
        auth.user_id,
        body.excluded_languages,
    )
    github_token = await _resolve_github_token(auth)

    try:
        report = await generate_verification_report(
            github_token=github_token,
            excluded_languages=set(body.excluded_languages),
            excluded_repos=set(body.excluded_repos),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Verification pipeline failed for user %s: %s", auth.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Verification pipeline failed. Check GitHub token and Gemini API key.",
        ) from exc
    except Exception as exc:
        logger.error(
            "Unexpected error in verify_skills for user %s: %s",
            auth.user_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during verification.",
        ) from exc
    finally:
        github_token = ""  # noqa: S105  # removes local reference; GC handles memory

    logger.info(
        "Verification report done for %s: skill=%s  score=%d  confidence=%s",
        auth.user_id,
        report.skill_level,
        report.security_score,
        report.confidence,
    )
    return report


# ── GET /agent/vault/status ───────────────────────────────────────────────────


@router.get(
    "/vault/status",
    summary="Check whether a GitHub token is stored in Token Vault",
    description=(
        "Returns `{connected: true}` if the Token Exchange succeeds, "
        "`{connected: false}` if no GitHub token is stored for this user."
    ),
)
async def vault_status(
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, bool]:
    """Lightweight GitHub connection check. Does NOT return the token."""
    token = ""
    try:
        stored = token_store.get(auth.user_id)
        if not stored:
            return {"connected": False}
        token = await get_github_token_from_vault(stored)
        connected = bool(token)
    except ValueError:
        connected = False
    except RuntimeError as exc:
        logger.error("Vault status check failed for user %s: %s", auth.user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Auth0 Token Vault.",
        ) from exc
    finally:
        token = ""  # noqa: S105

    return {"connected": connected}
