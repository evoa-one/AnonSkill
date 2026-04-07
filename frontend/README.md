# Frontend — Next.js

Next.js 14 (App Router) frontend for AnonSkill.

---

## Pages

| Route | Description |
|---|---|
| `/` | Landing page — explains zero-knowledge concept, renders "Connect GitHub" button |
| `/dashboard` | Full verification flow: vault check → 2-step configure → AI analysis → report |
| `/auth/error` | Error page shown when Auth0 returns an error on callback |

---

## Verification Flow (dashboard)

```
1. Extract access_token from URL fragment (post-login redirect)
        │
        ▼
2. GET /agent/vault/status
   ├── not connected → GET /oauth/github/connect → redirect to GitHub
   └── connected ──▶
        │
        ▼
3. GET /agent/repos  →  fetch all accessible repos
        │
        ▼
4. Step 1: User excludes languages
   (detected from actual repos, not a hardcoded list)
        │
        ▼
5. Step 2: User selects repos
   (filtered by excluded languages, sorted by activity)
        │
        ▼
6. POST /agent/verify  { excluded_languages, excluded_repos }
        │
        ▼
7. VerificationCard renders the report
```

---

## Component Map

```
components/
├── ConnectButton.tsx     # Calls GET /oauth/github/authorize → redirects to Auth0
├── LoadingAudit.tsx      # Animated loading state (two modes: loading / verifying)
├── ScoreGauge.tsx        # SVG arc gauge for the security score (0–100)
└── VerificationCard.tsx  # Full report: skill badge, score gauge, languages, AI reasoning
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000`) |

---

## Local Setup

```bash
cd frontend
npm install
npm run dev
```

App runs at http://localhost:3000.

The FastAPI backend must be running on port 8000.

---

## Security Notes

- `access_token` is stored only in `sessionStorage` (never `localStorage` or cookies)
- Token is cleared from `sessionStorage` immediately after verification completes
- Token is passed in the URL fragment (not query string) to avoid server logs
- No GitHub token or source code ever reaches the frontend
