# AnonSkill

**Zero-knowledge GitHub skill verification powered by Auth0 Token Vault.**

Built for the [Authorized to Act: Auth0 for AI Agents Hackathon](https://auth0-for-ai-agents.devpost.com/).

AnonSkill lets developers prove their technical skills to employers without ever exposing source code. Auth0 Token Vault retrieves the GitHub token server-side; Gemini AI analyzes only repository metadata (commit patterns, language distribution, activity signals) and returns a structured verification report.

---

## How It Works

```
Browser                  Backend (FastAPI)              Auth0                  GitHub
  │                            │                          │                       │
  │── Click "Connect" ────────▶│                          │                       │
  │◀─ Auth0 authorize URL ─────│                          │                       │
  │── redirect ───────────────────────────────────────────▶│                       │
  │                            │                    GitHub OAuth                  │
  │                            │                    Connected Accounts flow       │
  │◀── auth code ─────────────────────────────────────────│                       │
  │── /oauth/callback ────────▶│                          │                       │
  │◀── access_token (fragment)─│                          │                       │
  │                            │                          │                       │
  │── Step 1: exclude langs ──▶│                          │                       │
  │── Step 2: choose repos ───▶│                          │                       │
  │── POST /agent/verify ─────▶│                          │                       │
  │                     Token Exchange grant              │                       │
  │                     (refresh token → GitHub token) ──▶│                       │
  │                            │◀── GitHub token ─────────│                       │
  │                            │── repo metadata only ──────────────────────────▶│
  │                            │◀── languages, commit stats ────────────────────│
  │                            │── Gemini AI analysis     │                       │
  │◀── VerificationReport ─────│                          │                       │
```

**Zero-knowledge guarantees:**
- No source code is ever fetched — only language byte counts, commit frequency, and repo size
- The GitHub token lives in memory only for the duration of one request
- No commit messages, email addresses, or contributor names are collected
- The GitHub token is never returned to the frontend or written to any log

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router) |
| Backend | Python 3.13 + FastAPI |
| Identity / Auth | Auth0 for AI Agents — Token Vault + Connected Accounts |
| AI Analysis | Google Gemini 2.0 Flash |
| GitHub API | PyGithub |
| JWT Validation | python-jose (RS256 + JWKS) |
| Infrastructure | GCP Cloud Run + Terraform |

---

## Auth0 Token Vault Integration

Token Vault storage requires a separate **Connected Account** flow via Auth0's My Account API — it does not happen automatically during login.

### Flow

1. `GET /oauth/github/connect` — backend calls `POST /me/v1/connected-accounts/connect` with PKCE, gets `connect_uri`
2. Browser is redirected to GitHub for authorization
3. `GET /oauth/github/connect/callback` — backend calls `POST /me/v1/connected-accounts/complete`, Auth0 stores the GitHub token in Token Vault
4. `GET /agent/vault/status` — confirms `{ connected: true }`
5. `POST /agent/verify` — backend uses Token Exchange grant to retrieve the GitHub token from Token Vault

### Required Auth0 Configuration

| Setting | Where |
|---|---|
| GitHub Social Connection → Token Vault | Authentication → Social → GitHub → Token Vault: **Enabled** |
| GitHub App (not OAuth App) | Required for refresh tokens; OAuth Apps do not issue refresh tokens |
| Grant Type: Token Exchange | Applications → {App} → Advanced Settings → Grant Types |
| My Account API | Applications → APIs → My Account API: **Enabled** |
| MRRT (Multi-Resource Refresh Tokens) | Applications → {App} → Advanced Settings → Enable MRRT |
| Authorized Party for My Account API | Applications → {App} → APIs → Authorize with `create:me:connected_accounts` scope |

---

## Repository Structure

```
.
├── backend/           # FastAPI app        → see backend/README.md
├── frontend/          # Next.js app        → see frontend/README.md
├── infra/             # Terraform (GCP)    → see infra/README.md
├── scripts/           # Build & deploy scripts
├── docker-compose.yml # Local development
├── nginx.conf         # Local reverse proxy (optional)
└── README.md
```

---

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.13+
- Auth0 account with Token Vault configured
- Google AI Studio API key (Gemini)
- GitHub App registered in Auth0

### Local Development

```bash
# Backend
cd backend
cp .env.example .env   # fill in all values
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend: http://localhost:3000  
Backend docs: http://localhost:8000/docs

### Local Development (Docker)

```bash
cp backend/.env.example backend/.env  # fill in all values
docker compose up --build
```

Frontend: http://localhost:3000  
Backend: http://localhost:8000

### Production (GCP Cloud Run)

See [infra/README.md](infra/README.md) for full deployment instructions.

```bash
# 1. Provision infrastructure
cd infra/envs/prod && terraform init && terraform apply

# 2. Build, push, and deploy
./scripts/build-and-push.sh prod
```
