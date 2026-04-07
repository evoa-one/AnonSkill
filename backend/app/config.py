"""
Application configuration loaded from environment variables.

All Auth0-related credentials are read from .env at startup.
No secret should ever be hardcoded in source files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Auth0 tenant ──────────────────────────────────────────────────────────
    # Example: dev-abc123.us.auth0.com  (no trailing slash, no https://)
    auth0_domain: str

    # The API identifier you registered in Auth0 → Applications → APIs
    # Example: https://anonSkill.example.com/api
    auth0_audience: str

    # ── Regular web-app client (used to drive the OAuth redirect for the user) ─
    auth0_client_id: str
    auth0_client_secret: str

    # ── Routing ───────────────────────────────────────────────────────────────
    # Must match one of the "Allowed Callback URLs" in your Auth0 application
    callback_url: str = "http://localhost:8000/oauth/callback"

    # Callback URL for the Token Vault Connected Account connect flow
    # Must also be added to "Allowed Callback URLs" in Auth0 dashboard
    connect_callback_url: str = "http://localhost:8000/oauth/github/connect/callback"

    # Frontend origin – used for CORS and final redirect after login
    frontend_url: str = "http://localhost:3000"

    # ── GitHub social connection name in Auth0 ────────────────────────────────
    # Check Auth0 Dashboard → Authentication → Social → GitHub → "Connection name"
    # Default is "github" unless you renamed it.
    github_connection_name: str = "github"

    # ── Gemini API ────────────────────────────────────────────────────────────
    # Google AI Studio → Get API Key → https://aistudio.google.com/app/apikey
    gemini_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton – import this object everywhere instead of instantiating again
settings = Settings()
