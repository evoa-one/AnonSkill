"""
Auth0 JWT validation middleware.

Every protected endpoint uses `get_auth_context()` as a FastAPI dependency.
The dependency:
  1. Extracts the Bearer token from the Authorization header
  2. Fetches Auth0's public JWKS (cached per process lifetime)
  3. Verifies the token's signature, expiry, audience, and issuer
  4. Returns an AuthContext with both the user's `sub` and the raw access token

The raw access token is kept because the Token Vault token exchange requires
it as the `subject_token` — Auth0 uses it to look up and decrypt the stored
GitHub token.
"""

from dataclasses import dataclass
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings


@dataclass(frozen=True)
class AuthContext:
    """
    Validated identity extracted from the Auth0 JWT.

    Attributes:
        user_id:      Auth0 sub claim, e.g. "github|12345678".
        access_token: The raw Bearer token — passed to Token Vault as subject_token.
    """
    user_id: str
    access_token: str


# ── JWKS helpers ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _fetch_jwks() -> dict:
    """Download Auth0's JWKS once and cache it for the process lifetime."""
    jwks_url  = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    response  = httpx.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


def _get_rsa_key(token: str) -> dict:
    """Match the JWT's `kid` header to a key in the JWKS."""
    jwks              = _fetch_jwks()
    unverified_header = jwt.get_unverified_header(token)

    for key in jwks["keys"]:
        if key["kid"] == unverified_header.get("kid"):
            return {"kty": key["kty"], "kid": key["kid"],
                    "use": key["use"], "n": key["n"], "e": key["e"]}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No matching signing key found for this token.",
    )


# ── FastAPI dependency ────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer()


def get_auth_context(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> AuthContext:
    """
    FastAPI dependency — validates the Auth0 JWT and returns an AuthContext.

    Raises:
        HTTPException 401: Token missing, malformed, expired, or untrusted.
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        rsa_key = _get_rsa_key(token)
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.auth0_client_id,  # id_token audience is the client_id
            issuer=f"https://{settings.auth0_domain}/",
        )
        user_id: str = payload.get("sub", "")
        if not user_id:
            raise credentials_exception
        return AuthContext(user_id=user_id, access_token=token)

    except JWTError:
        raise credentials_exception
