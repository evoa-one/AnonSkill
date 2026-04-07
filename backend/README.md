# Backend — FastAPI

Python FastAPI backend that integrates with **Auth0 Token Vault** to securely retrieve GitHub access tokens and generate zero-knowledge skill verification reports via Gemini AI.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                   # FastAPI app, CORS, router registration
│   ├── config.py                 # Settings loaded from .env (pydantic-settings)
│   ├── middleware/
│   │   └── jwt_validator.py      # RS256 JWT validation via Auth0 JWKS
│   ├── models/
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── routers/
│   │   ├── oauth.py              # OAuth flow + Connected Accounts endpoints
│   │   └── agent.py              # Protected agent endpoints
│   └── services/
│       ├── token_vault.py        # Auth0 Token Exchange grant (Token Vault read)
│       ├── agent_analyzer.py     # GitHub metadata collection + Gemini analysis
│       ├── github_client.py      # GitHub API calls (PyGithub)
│       └── token_store.py        # In-memory refresh token store (replace with Redis in prod)
├── Dockerfile
├── .env.example
├── requirements.txt
└── README.md
```

---

## API Reference

### OAuth Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/oauth/github/authorize` | Returns Auth0 authorization URL |
| `GET` | `/oauth/callback` | Receives auth code, exchanges for tokens, redirects to frontend |
| `GET` | `/oauth/github/connect` | Initiates Token Vault Connected Account flow |
| `GET` | `/oauth/github/connect/callback` | Completes Connected Account registration |

### Agent Endpoints (require Bearer token)

| Method | Path | Description |
|---|---|---|
| `GET` | `/agent/vault/status` | Returns `{ connected: true/false }` |
| `GET` | `/agent/repos` | Lists all accessible repos for the configure step |
| `POST` | `/agent/verify` | Runs full verification pipeline, returns `VerificationReport` |

### `POST /agent/verify` Request Body

```json
{
  "excluded_languages": ["HTML", "CSS", "XSLT"],
  "excluded_repos": ["old-project", "test-repo"]
}
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `AUTH0_DOMAIN` | Auth0 tenant domain, e.g. `dev-abc.us.auth0.com` |
| `AUTH0_AUDIENCE` | API identifier registered in Auth0 |
| `AUTH0_CLIENT_ID` | Web app client ID |
| `AUTH0_CLIENT_SECRET` | Web app client secret |
| `CALLBACK_URL` | OAuth callback URL (must match Auth0 Allowed Callback URLs) |
| `CONNECT_CALLBACK_URL` | Connected Account callback URL |
| `FRONTEND_URL` | Next.js origin, used for CORS and post-login redirect |
| `GITHUB_CONNECTION_NAME` | Auth0 connection name for GitHub (default: `github`) |
| `GEMINI_API_KEY` | Google AI Studio API key for Gemini |

---

## Auth0 Setup

### 1. Create a GitHub App (not OAuth App)

GitHub Apps issue refresh tokens; OAuth Apps do not. Token Vault requires refresh tokens.

- Go to GitHub → Settings → Developer Settings → GitHub Apps → New GitHub App
- Set callback to: `https://{your-auth0-domain}/login/callback`
- Enable **"Expire user authorization tokens"**
- Enable **"Request user authorization (OAuth) during installation"**
- Installation: **Any account**

### 2. Configure Auth0 GitHub Social Connection

> Authentication → Social → GitHub

- Set Client ID / Secret to your GitHub App credentials
- Enable **Token Vault**
- Permissions: `read:user`, `repo`, `public_repo`, `read:org`

### 3. Create a Regular Web Application

> Applications → Applications → Create Application → Regular Web Application

| Field | Value |
|---|---|
| Allowed Callback URLs | `http://localhost:8000/oauth/callback, http://localhost:8000/oauth/github/connect/callback` |
| Allowed Logout URLs | `http://localhost:3000` |
| Allowed Web Origins | `http://localhost:3000` |

Enable under Advanced Settings → Grant Types:
- **Token Exchange** (`urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token`)

Enable under Advanced Settings:
- **Allow Offline Access** (required for refresh tokens)
- **Multi-Resource Refresh Tokens (MRRT)**

### 4. Enable My Account API

> Applications → APIs → My Account API → Enable

Then authorize your app with `create:me:connected_accounts` and `read:me:connected_accounts` scopes.

### 5. Register an API

> Applications → APIs → Create API

| Field | Value |
|---|---|
| Identifier (audience) | e.g. `https://anon-skill.evoa.one/api` |
| Signing Algorithm | RS256 |

---

## Local Setup

```bash
cd backend
cp .env.example .env
# Fill in all values

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://localhost:8000/docs

---

## Security Notes

- GitHub token is retrieved server-side via Token Exchange grant — never sent to the frontend
- Token variable is overwritten in memory immediately after use
- JWT signature verified against Auth0 JWKS on every protected request
- One-time CSRF state token used on OAuth callback
- PKCE used in the Connected Account flow
- Only repository metadata is fetched — no file content, commit messages, or email addresses
