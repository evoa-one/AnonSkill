"""
Auth0 Token Vault service.

How Token Vault works (Auth0 for AI Agents)
────────────────────────────────────────────
1. The user authenticates via Auth0's Universal Login using the GitHub social
   connection.  Auth0 completes the OAuth dance with GitHub and stores the
   resulting GitHub access token encrypted in Token Vault.

2. The backend calls the Token Exchange endpoint (POST /oauth/token) using
   a special grant type, presenting:
     - Its own client_id + client_secret  (the Regular Web App registered in Auth0)
     - The user's Auth0 access_token      (subject_token — proves the user's identity)
     - The connection name                (e.g. "github")

3. Auth0 decrypts the stored GitHub token and returns it in the response.
   The GitHub token never passes through the frontend.

Token Exchange grant type
──────────────────────────
  urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token

Required Auth0 dashboard configuration
────────────────────────────────────────
  1. Applications → {Your App} → Advanced Settings → Grant Types
     ☑ Token Exchange  (adds the grant above)
  2. Authentication → Social → GitHub → Enable Token Vault
     Toggle "Token Vault" on for the GitHub connection.

Security properties
────────────────────
- The GitHub token lives only in memory during the request.
- It is never logged, stored, or returned to the caller.
- No M2M application or Management API token is required.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Token Exchange grant type identifier defined by Auth0 for AI Agents
_TOKEN_EXCHANGE_GRANT = (
    "urn:auth0:params:oauth:grant-type:"
    "token-exchange:federated-connection-access-token"
)
_SUBJECT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:refresh_token"
_REQUESTED_TOKEN_TYPE = (
    "http://auth0.com/oauth/token-type/federated-connection-access-token"
)


async def get_github_token_from_vault(user_access_token: str) -> str:
    """
    Exchange the user's Auth0 access token for their stored GitHub token
    via the Auth0 Token Vault token exchange endpoint.

    Args:
        user_access_token: The Auth0 Bearer token that arrived on the request.
                           Auth0 uses it to identify the user and decrypt their
                           stored GitHub token from Token Vault.

    Returns:
        str: The raw GitHub OAuth access token.

    Raises:
        ValueError:   The user has not connected GitHub, or Token Vault is not
                      enabled for this connection / application.
        RuntimeError: The Token Vault API call failed unexpectedly.
    """
    payload = {
        "client_id":            settings.auth0_client_id,
        "client_secret":        settings.auth0_client_secret,
        "grant_type":           _TOKEN_EXCHANGE_GRANT,
        "subject_token":        user_access_token,
        "subject_token_type":   _SUBJECT_TOKEN_TYPE,
        "requested_token_type": _REQUESTED_TOKEN_TYPE,
        "connection":           settings.github_connection_name,
    }

    logger.debug(
        "Requesting GitHub token from Auth0 Token Vault (connection: %s).",
        settings.github_connection_name,
    )

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"https://{settings.auth0_domain}/oauth/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code == 200:
        github_token: str = response.json()["access_token"]
        logger.debug("GitHub token retrieved successfully from Token Vault.")
        return github_token

    error_body = response.json() if response.content else {}
    error_code  = error_body.get("error", "")
    error_desc  = error_body.get("error_description", "")

    logger.error(
        "Token Vault exchange failed. Status: %s  Error: %s  Description: %s",
        response.status_code,
        error_code,
        error_desc,
    )

    # 400 / 403 with access_denied typically means the user hasn't connected
    # GitHub yet, or the Token Vault grant type is not enabled on the app.
    if (
        response.status_code in (400, 401, 403)
        or error_code in ("access_denied", "federated_connection_refresh_token_not_found")
    ):
        raise ValueError(
            "GitHub token not found in Token Vault. "
            "The user needs to complete the GitHub Connected Account flow."
        )

    raise RuntimeError(
        f"Auth0 Token Vault returned an unexpected error: "
        f"{response.status_code} — {error_code}: {error_desc}"
    )
