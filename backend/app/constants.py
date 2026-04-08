# ── Agent Analyzer (app/services/agent_analyzer.py) ──────────────────────────

TOP_N_REPOS = 3           # Number of repos to deep-analyze
CANDIDATE_LIMIT = 100     # Max repos fetched before scoring
DEEP_ANALYSIS_LIMIT = 20  # Max repos for deep analysis; pre-sorted by recency
STATS_RETRY_SLEEP = 3     # Seconds to wait if GitHub stats API returns 202
STATS_MAX_RETRIES = 3     # Retry attempts for the stats endpoint
RECENT_WEEKS = 13         # Weeks considered "recent" for participation stats

# ── JWT Validator (app/middleware/jwt_validator.py) ───────────────────────────

JWKS_TTL = 3600           # Refresh JWKS every hour to pick up Auth0 key rotations
