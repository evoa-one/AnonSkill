"""
OAuth router – GitHub social login via Auth0.

Endpoints
─────────
GET  /oauth/github/authorize
    Constructs and returns the Auth0 authorization URL.

GET  /oauth/callback
    Receives the authorization code from Auth0, exchanges it for tokens,
    and redirects the user back to the frontend.

GET  /oauth/github/connect
    Initiates the Token Vault Connected Account flow via Auth0's My Account API.
    Returns {connect_url} — frontend must redirect the browser there.

GET  /oauth/github/connect/callback
    Receives the connect_code after GitHub authorization and completes
    the Connected Account registration, storing the GitHub token in Token Vault.

How Auth0 Token Vault is populated
────────────────────────────────────
Token Vault storage does NOT happen automatically during login. It requires a
separate "Connect Account" flow via Auth0's My Account API:

  1. GET /oauth/github/connect  → calls POST /me/v1/connected-accounts/connect
     → returns connect_uri → browser is redirected there
  2. User authorizes on GitHub
  3. GET /oauth/github/connect/callback  → calls POST /me/v1/connected-accounts/complete
     → Auth0 stores the GitHub token in Token Vault

After this flow, GET /agent/vault/status returns {connected: true} and
agent endpoints can use Token Vault to retrieve the GitHub token.
"""

import hashlib
import base64
import logging
import secrets
import urllib.parse
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.middleware.jwt_validator import AuthContext, get_auth_context
from app.models.schemas import AuthorizeResponse, TokenResponse
from app.services import token_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth", tags=["OAuth"])

# ── Simple in-process state stores (replace with Redis in production) ──────────
_pending_states: dict[str, bool] = {}

# Maps state → {user_sub, auth_session, code_verifier, redirect_uri}
_pending_connect_states: dict[str, dict[str, Any]] = {}


# ── Step 1: Build authorization URL ──────────────────────────────────────────


@router.get(
    "/github/authorize",
    response_model=AuthorizeResponse,
    summary="Initiate GitHub OAuth flow via Auth0",
    description=(
        "Generates a one-time state token and returns the Auth0 authorization URL. "
        "The frontend must redirect the browser to `authorization_url`. "
        "Auth0 will handle the GitHub OAuth dance and store the resulting "
        "GitHub access token in Token Vault automatically."
    ),
)
def initiate_github_oauth() -> AuthorizeResponse:
    """
    Build the Auth0 /authorize URL that starts the GitHub social login.

    Query parameters sent to Auth0:
    - response_type=code       → Authorization Code flow (most secure)
    - client_id                → Our web-app client registered in Auth0
    - redirect_uri             → Must match "Allowed Callback URLs" in the Auth0 dashboard
    - scope                    → openid + profile so we get a proper ID token back
    - connection=github        → Force Auth0 to use the GitHub social connection
    - access_type=offline      → Request a refresh token so Auth0 can refresh the GitHub token
    - state                    → Random token to prevent CSRF on the callback
    """
    state = secrets.token_urlsafe(32)
    _pending_states[state] = True

    # Prune states older than the 200 most recent to avoid unbounded growth.
    # In production, store states in Redis with a TTL of ~10 minutes.
    if len(_pending_states) > 200:
        oldest_key = next(iter(_pending_states))
        del _pending_states[oldest_key]

    params = {
        "response_type": "code",
        "client_id": settings.auth0_client_id,
        "redirect_uri": settings.callback_url,
        "scope": "openid profile email offline_access",
        "audience": settings.auth0_audience,
        "connection": settings.github_connection_name,
        "prompt": "login",
        "state": state,
    }

    query_string = urllib.parse.urlencode(params)
    authorization_url = f"https://{settings.auth0_domain}/authorize?{query_string}"

    logger.debug("Authorization URL generated (state=%s…)", state[:8])
    return AuthorizeResponse(authorization_url=authorization_url, state=state)


# ── Step 2: Handle the callback from Auth0 ────────────────────────────────────


@router.get(
    "/callback",
    response_class=RedirectResponse,
    summary="Auth0 callback – exchange code for tokens",
    description=(
        "Auth0 redirects here after the user grants GitHub access. "
        "This endpoint validates the state, exchanges the code for an "
        "Auth0 access_token, then redirects to the frontend dashboard."
    ),
)
async def oauth_callback(
    code: str | None = Query(
        None, description="One-time authorization code from Auth0"
    ),
    state: str | None = Query(None, description="State token echoed back by Auth0"),
    error: str | None = Query(
        None, description="Set by Auth0 if the user denied access"
    ),
    error_description: str | None = Query(None),
) -> RedirectResponse:
    """
    Exchange the Auth0 authorization code for an access token.

    On success, redirect to the frontend with the access_token in the URL fragment:
        http://localhost:3000/dashboard#access_token=...&token_type=Bearer

    Using the fragment (not a query parameter) ensures the token is never sent
    to the server in the Referer header or stored in server access logs.
    """
    # ── Guard: Auth0 returned an error (e.g. user denied, client not authorized) ─
    if error or not code:
        logger.warning(
            "Auth0 returned an error on callback: %s – %s", error, error_description
        )
        redirect_url = (
            f"{settings.frontend_url}/auth/error"
            f"?error={error or 'missing_code'}&description={error_description or ''}"
        )
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    # ── Guard: validate CSRF state token ─────────────────────────────────────
    if not state or state not in _pending_states:
        logger.error(
            "Unknown or replayed state token received on callback: %s", state[:8]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state token. Possible CSRF attempt.",
        )
    del _pending_states[state]  # One-time use

    # ── Exchange code for Auth0 tokens ────────────────────────────────────────
    token_response = await _exchange_code_for_tokens(code)

    # ── Redirect to frontend with the access token in the URL fragment ────────
    # The frontend extracts the token from the fragment and stores it in memory
    # (NOT in localStorage or cookies to minimise XSS risk).
    redirect_url = (
        f"{settings.frontend_url}/dashboard"
        f"#access_token={token_response.access_token}"
        f"&token_type={token_response.token_type}"
        f"&expires_in={token_response.expires_in}"
    )
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


# ── Step 3: Initiate GitHub Connected Account for Token Vault ─────────────────


@router.get(
    "/github/connect",
    summary="Initiate GitHub Token Vault connect flow",
    description=(
        "Requires a valid Auth0 Bearer token. "
        "Calls Auth0's My Account API to start the Connected Account flow. "
        "Returns {connect_url} — the frontend must redirect the browser to this URL."
    ),
)
async def initiate_github_connect(
    auth: AuthContext = Depends(get_auth_context),
) -> JSONResponse:
    my_account_token = await _get_my_account_token(auth.user_id)

    # PKCE
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )

    state = secrets.token_urlsafe(32)
    connect_callback = f"{settings.connect_callback_url}"

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://{settings.auth0_domain}/me/v1/connected-accounts/connect",
            json={
                "connection": settings.github_connection_name,
                "redirect_uri": connect_callback,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            },
            headers={"Authorization": f"Bearer {my_account_token}"},
        )

    if response.status_code != 201:
        logger.error("My Account API connect failed: %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to initiate GitHub connect: {response.json().get('detail', response.text)}",
        )

    data = response.json()
    ticket = data["connect_params"]["ticket"]
    connect_uri = data["connect_uri"]

    # Auth0 returns the base URI without the ticket — append it.
    separator = "&" if "?" in connect_uri else "?"
    connect_url = f"{connect_uri}{separator}ticket={ticket}"

    logger.info(
        "GitHub connect initiated for user: %s  connect_uri: %s",
        auth.user_id,
        connect_uri,
    )

    _pending_connect_states[state] = {
        "user_sub": auth.user_id,
        "auth_session": data["auth_session"],
        "code_verifier": code_verifier,
        "redirect_uri": connect_callback,
    }

    # Prune to avoid unbounded growth (same pattern as _pending_states)
    if len(_pending_connect_states) > 200:
        oldest_key = next(iter(_pending_connect_states))
        del _pending_connect_states[oldest_key]

    return JSONResponse({"connect_url": connect_url})


# ── Step 4: Complete GitHub Connected Account connection ──────────────────────


@router.get(
    "/github/connect/callback",
    response_class=RedirectResponse,
    summary="Complete GitHub Token Vault connect flow",
)
async def complete_github_connect(
    connect_code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    if state not in _pending_connect_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state."
        )

    connect_state = _pending_connect_states.pop(state)
    user_sub = connect_state["user_sub"]
    auth_session = connect_state["auth_session"]
    code_verifier = connect_state["code_verifier"]
    redirect_uri = connect_state["redirect_uri"]

    my_account_token = await _get_my_account_token(user_sub)

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://{settings.auth0_domain}/me/v1/connected-accounts/complete",
            json={
                "auth_session": auth_session,
                "connect_code": connect_code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Authorization": f"Bearer {my_account_token}"},
        )

    if response.status_code != 201:
        logger.error("My Account API complete failed: %s", response.text)
        return RedirectResponse(
            url=f"{settings.frontend_url}?error=connect_failed",
            status_code=status.HTTP_302_FOUND,
        )

    logger.info("GitHub Token Vault connected account stored for user: %s", user_sub)
    return RedirectResponse(
        url=f"{settings.frontend_url}/dashboard",
        status_code=status.HTTP_302_FOUND,
    )


async def _get_my_account_token(user_sub: str) -> str:
    """Use MRRT to exchange the stored refresh token for a My Account API access token."""
    refresh_token = token_store.get(user_sub)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No session found. Please re-authenticate via /oauth/github/authorize.",
        )

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://{settings.auth0_domain}/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.auth0_client_id,
                "client_secret": settings.auth0_client_secret,
                "refresh_token": refresh_token,
                "audience": f"https://{settings.auth0_domain}/me/",
                "scope": "create:me:connected_accounts read:me:connected_accounts",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        logger.error("Failed to get My Account API token: %s", response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to obtain My Account API access token.",
        )

    return response.json()["access_token"]


async def _exchange_code_for_tokens(code: str) -> TokenResponse:
    """
    Call Auth0's /oauth/token endpoint to exchange the authorization code.

    Args:
        code: One-time code received from Auth0 on the callback.

    Returns:
        TokenResponse containing the Auth0 access_token.

    Raises:
        HTTPException 502: If Auth0 returns an unexpected response.
    """
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.auth0_client_id,
        "client_secret": settings.auth0_client_secret,
        "code": code,
        "redirect_uri": settings.callback_url,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://{settings.auth0_domain}/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        logger.error(
            "Auth0 token exchange failed. Status: %s  Body: %s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange authorization code with Auth0.",
        )

    data = response.json()
    id_token = data.get("id_token") or data.get("access_token")
    refresh_token = data.get(
        "refresh_token"
    )  # Auth0 refresh token — subject_token for Token Vault

    # Store the Auth0 refresh token server-side for the Token Vault refresh-token exchange.
    # Requires a GitHub App (not OAuth App) — GitHub Apps issue refresh tokens.
    logger.info(
        "Token response keys: %s | id_token present: %s | refresh_token present: %s",
        list(data.keys()),
        bool(data.get("id_token")),
        bool(refresh_token),
    )
    if refresh_token:
        from jose import jwt as _jwt
        from app.services import token_store

        try:
            claims = _jwt.get_unverified_claims(id_token)
            sub = claims.get("sub", "")
            logger.info("Storing refresh_token for sub: %s", sub)
            if sub:
                token_store.save(sub, refresh_token)
        except Exception:
            logger.warning(
                "Could not extract sub from id_token to store refresh token."
            )

    return TokenResponse(
        access_token=id_token,
        token_type=data.get("token_type", "Bearer"),
        expires_in=int(data.get("expires_in", 86400)),
        refresh_token=None,  # never send refresh token to the frontend
    )
