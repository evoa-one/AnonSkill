"""
In-memory store mapping Auth0 user sub → refresh token.

The refresh token is captured during the OAuth callback and used later
as the subject_token for the Auth0 Token Vault token exchange.

Keeping the refresh token server-side means it never travels to the
frontend, which is the correct security posture.

Note: this store is reset on server restart. For production, use Redis
or another persistent store with TTL.
"""

import logging

logger = logging.getLogger(__name__)

_store: dict[str, str] = {}  # sub → refresh_token


def save(sub: str, refresh_token: str) -> None:
    """Store a refresh token for a user."""
    _store[sub] = refresh_token
    logger.debug("Refresh token stored for sub: %s", sub)


def get(sub: str) -> str | None:
    """Retrieve the stored refresh token for a user, or None."""
    return _store.get(sub)
