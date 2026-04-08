"""
AI Agent — Zero-Knowledge Verification Report Generator.

Pipeline
────────
1. Fetch all owned, non-fork repositories for the authenticated GitHub user.
2. Score each repository by recent activity (commits, size, language breadth).
3. Select the top 3 most active repositories for deep analysis.
4. Collect detailed metrics per repo:
     - Language distribution (bytes, from GitHub Linguist)
     - Commit frequency (last 90 days + last 12 months via GitHub Stats API)
     - Code complexity proxies (repo size, language count, open issues)
5. Build a structured prompt and call the Gemini API (gemini-2.0-flash).
6. Parse the JSON response into a VerificationReport.

Zero-knowledge constraints
──────────────────────────
- No file content is ever fetched or stored.
- No commit messages, author names, or email addresses are collected.
- The GitHub token is accepted as a parameter, used in-memory, and
  never written to a log or returned to the caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import google.generativeai as genai
from github import Github, GithubException
from github.Repository import Repository
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import VerificationReport

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

TOP_N_REPOS = 3           # Number of repos to deep-analyze
CANDIDATE_LIMIT = 100     # Max repos fetched before scoring
DEEP_ANALYSIS_LIMIT = 20  # Max repos for deep analysis (API calls); pre-sorted by recency
STATS_RETRY_SLEEP = 3     # Seconds to wait if GitHub stats API returns 202
STATS_MAX_RETRIES = 3     # Retry attempts for the stats endpoint

# Weeks to consider "recent" (GitHub participation stats are weekly)
RECENT_WEEKS = 13         # ≈ 90 days

# Languages that are markup/template/config — excluded from skill language list
# because they don't reflect programming depth
_EXCLUDED_LANGUAGES = {
    "HTML", "CSS", "XSLT", "XML", "Markdown", "SVG", "SCSS", "Less",
    "Makefile", "Dockerfile", "Shell", "Batchfile", "PowerShell",
    "INI", "TOML", "YAML", "JSON",
}

GEMINI_MODEL = "gemini-flash-latest"


# ── Internal data container ───────────────────────────────────────────────────

@dataclass
class RepoMetrics:
    """
    All metadata collected for a single repository.
    No field ever contains file content, commit messages, or email addresses.
    """
    name: str
    languages: dict[str, int] = field(default_factory=dict)   # language → bytes
    top_language: str = "Unknown"
    language_count: int = 0
    commit_count_90d: int = 0    # commits in last ~90 days (13 weekly buckets)
    commit_count_1yr: int = 0    # commits in last 52 weeks
    repo_size_kb: int = 0        # GitHub-reported repo size
    activity_score: float = 0.0  # composite score used for ranking
    topics: list[str] = field(default_factory=list)
    open_issues_count: int = 0
    has_ci: bool = False         # inferred from topics / description keywords


# ── Step 1 & 2: Fetch and rank repositories ───────────────────────────────────

def _compute_activity_score(metrics: RepoMetrics) -> float:
    """
    Composite activity score for ranking.

    Weights (tuned to surface regularly-maintained codebases):
      - Recent commit density  : highest weight (active work matters most)
      - Annual commit volume   : breadth of contribution history
      - Language diversity     : signals architectural breadth
      - Repo size              : proxy for codebase maturity
    """
    return (
        metrics.commit_count_90d  * 10.0   # recent activity is most important
        + metrics.commit_count_1yr * 2.0
        + metrics.language_count   * 3.0
        + metrics.repo_size_kb     * 0.001
    )


def _get_participation_stats(repo: Repository) -> tuple[int, int]:
    """
    Fetch weekly commit participation from GitHub Stats API.

    Returns (commit_count_90d, commit_count_1yr).

    The GitHub Stats API may return 202 while it computes the data;
    we retry up to STATS_MAX_RETRIES times.
    """
    for attempt in range(STATS_MAX_RETRIES):
        try:
            stats = repo.get_stats_participation()
            if stats is None:
                # GitHub is still computing — wait and retry
                if attempt < STATS_MAX_RETRIES - 1:
                    logger.debug(
                        "Stats not ready for %s (attempt %d), retrying in %ds…",
                        repo.name, attempt + 1, STATS_RETRY_SLEEP,
                    )
                    time.sleep(STATS_RETRY_SLEEP)
                    continue
                # Exhausted retries — return zero counts rather than failing
                return 0, 0

            # `stats.all` is a list of 52 weekly commit totals (oldest → newest)
            weekly_counts: list[int] = stats.all or []
            commit_count_1yr  = sum(weekly_counts)
            commit_count_90d  = sum(weekly_counts[-RECENT_WEEKS:])
            return commit_count_90d, commit_count_1yr

        except GithubException as exc:
            if exc.status == 202:
                # API is computing — treat like a None response
                if attempt < STATS_MAX_RETRIES - 1:
                    time.sleep(STATS_RETRY_SLEEP)
                    continue
                return 0, 0
            # Any other GitHub error: skip stats but don't abort
            logger.warning("Stats API error for %s: %s", repo.name, exc)
            return 0, 0

    return 0, 0


def _collect_repo_metrics(repo: Repository) -> RepoMetrics:
    """
    Collect all analysis-relevant metadata for a single repository.

    Called in a thread (blocking I/O — PyGithub is synchronous).
    """
    metrics = RepoMetrics(name=repo.name)

    # ── Languages ─────────────────────────────────────────────────────────────
    try:
        metrics.languages = repo.get_languages() or {}
    except GithubException:
        metrics.languages = {}

    if metrics.languages:
        metrics.top_language  = max(metrics.languages, key=metrics.languages.__getitem__)
        metrics.language_count = len(metrics.languages)

    # ── Participation stats ───────────────────────────────────────────────────
    metrics.commit_count_90d, metrics.commit_count_1yr = _get_participation_stats(repo)

    # ── Basic metadata ────────────────────────────────────────────────────────
    metrics.repo_size_kb     = repo.size  # GitHub reports in KB
    metrics.open_issues_count = repo.open_issues_count

    try:
        metrics.topics = repo.get_topics() or []
    except GithubException:
        metrics.topics = []

    # ── CI heuristic (inferred from topics, no file access) ──────────────────
    ci_keywords = {"ci", "cd", "github-actions", "actions", "devops", "pipeline"}
    metrics.has_ci = bool(ci_keywords & {t.lower() for t in metrics.topics})

    # ── Activity score ────────────────────────────────────────────────────────
    metrics.activity_score = _compute_activity_score(metrics)

    return metrics


def _fetch_top_repos_sync(github_token: str) -> tuple[str, list[RepoMetrics]]:
    """
    Synchronous worker: fetches repos, ranks them, and returns the top N.

    Returns (github_username, top_metrics_list).
    Intended to be run via asyncio.to_thread to avoid blocking the event loop.
    """
    client = Github(github_token, per_page=100)
    try:
        user = client.get_user()
        github_username = user.login
        logger.info("Fetching repositories for GitHub user: %s", github_username)

        # Collect candidate repos: owned + all org repos
        seen: set[int] = set()
        candidates: list[Repository] = []

        def _add_repo(repo: Repository) -> None:
            if repo.id in seen or repo.fork:
                return
            seen.add(repo.id)
            candidates.append(repo)

        for repo in user.get_repos(type="owner", sort="pushed"):
            _add_repo(repo)

        for org in user.get_orgs():
            try:
                for repo in org.get_repos():
                    _add_repo(repo)
                    if len(candidates) >= CANDIDATE_LIMIT:
                        break
            except GithubException:
                continue

        candidates = sorted(candidates, key=lambda r: r.pushed_at or r.created_at, reverse=True)[:CANDIDATE_LIMIT]

        if not candidates:
            logger.warning("No owned non-fork repos found for %s", github_username)
            return github_username, []

        # Collect metrics for top candidates only (sorted by recency, limit API calls)
        all_metrics: list[RepoMetrics] = []
        for repo in candidates[:DEEP_ANALYSIS_LIMIT]:
            try:
                m = _collect_repo_metrics(repo)
                all_metrics.append(m)
                logger.debug(
                    "Repo %s: score=%.1f  commits_90d=%d  languages=%d",
                    repo.name, m.activity_score, m.commit_count_90d, m.language_count,
                )
            except Exception as exc:
                logger.warning("Skipping repo %s due to error: %s", repo.name, exc)

        # Return top N by activity score
        top = sorted(all_metrics, key=lambda m: m.activity_score, reverse=True)[:TOP_N_REPOS]
        logger.info(
            "Top %d repos for %s: %s",
            len(top), github_username, [m.name for m in top],
        )
        return github_username, top

    finally:
        client.close()


def _fetch_repo_list_sync(github_token: str) -> tuple[str, list[dict]]:
    """
    Fast repo listing for the configure step — skips participation stats.
    Returns (github_username, list of repo dicts).
    """
    from app.models.schemas import RepoInfo
    client = Github(github_token, per_page=100)
    try:
        user = client.get_user()
        github_username = user.login

        seen: set[int] = set()
        all_repos: list[Repository] = []

        def _add(repo: Repository) -> None:
            if repo.id in seen or repo.fork:
                return
            seen.add(repo.id)
            all_repos.append(repo)

        for repo in user.get_repos(type="owner", sort="pushed"):
            _add(repo)

        orgs = list(user.get_orgs())
        logger.info("Orgs found for %s: %s", github_username, [o.login for o in orgs])

        for org in orgs:
            try:
                for repo in org.get_repos():
                    _add(repo)
            except GithubException as e:
                logger.warning("Could not fetch repos for org %s: %s", org.login, e)
                continue

        all_repos = sorted(all_repos, key=lambda r: r.pushed_at or r.created_at, reverse=True)

        repos = []
        for repo in all_repos:
            try:
                languages = list((repo.get_languages() or {}).keys())
            except GithubException:
                languages = []

            top_language = languages[0] if languages else "Unknown"
            is_org = repo.owner.login != github_username

            repos.append(RepoInfo(
                name=repo.name,
                top_language=top_language,
                languages=languages,
                commit_count_90d=0,
                repo_size_kb=repo.size,
                is_org=is_org,
            ))

        return github_username, repos
    finally:
        client.close()


async def get_repo_list(github_token: str) -> tuple[str, list]:
    """Public async wrapper for the configure step."""
    return await asyncio.to_thread(_fetch_repo_list_sync, github_token)


# ── Step 3: Build the Gemini prompt ──────────────────────────────────────────

def _format_repo_block(m: RepoMetrics) -> str:
    """Render one repo's metrics as a readable text block for the prompt."""
    lang_breakdown = ", ".join(
        f"{lang} ({bytes_count:,} bytes)"
        for lang, bytes_count in sorted(m.languages.items(), key=lambda x: x[1], reverse=True)
    ) or "No language data"

    return f"""
Repository: {m.name}
  Primary language   : {m.top_language}
  Language breakdown : {lang_breakdown}
  Distinct languages : {m.language_count}
  Commits (last 90d) : {m.commit_count_90d}
  Commits (last 1yr) : {m.commit_count_1yr}
  Repo size          : {m.repo_size_kb:,} KB
  Open issues        : {m.open_issues_count}
  Topics             : {", ".join(m.topics) if m.topics else "none"}
  CI detected        : {"yes" if m.has_ci else "no"}
""".strip()


_VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "skill_level": {
            "type": "string",
            "enum": ["Junior", "Mid-Level", "Senior", "Principal"],
            "description": "Overall seniority inferred from commit volume, language breadth, and codebase maturity",
        },
        "top_language": {
            "type": "string",
            "description": "The single most-used language by byte volume across the analyzed repos",
        },
        "security_score": {
            "type": "integer",
            "description": (
                "0-100 score reflecting maintenance hygiene: "
                "consistent commit frequency (freshness), language safety profile, "
                "use of CI/CD, and issue responsiveness"
            ),
        },
        "confidence": {
            "type": "string",
            "enum": ["Low", "Medium", "High"],
            "description": "How strongly the available data supports the assessment",
        },
        "languages_detected": {
            "type": "array",
            "items": {"type": "string"},
            "description": "All languages found across the top 3 repos, ordered by total byte volume",
        },
        "commit_frequency": {
            "type": "string",
            "description": "Human-readable average, e.g. '28 commits/month across top 3 repos'",
        },
        "complexity_rating": {
            "type": "string",
            "enum": ["Low", "Medium", "High", "Very High"],
            "description": "Estimated code complexity based on repo size, language count, and commit volume",
        },
        "repos_analyzed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Names of the repositories that were analyzed",
        },
        "reasoning": {
            "type": "string",
            "description": "2-4 sentence explanation of the skill_level and security_score decisions",
        },
    },
    "required": [
        "skill_level",
        "top_language",
        "security_score",
        "confidence",
        "languages_detected",
        "commit_frequency",
        "complexity_rating",
        "repos_analyzed",
        "reasoning",
    ],
}


def _build_prompt(github_username: str, metrics: list[RepoMetrics]) -> str:
    """
    Build the structured analysis prompt for Gemini.

    The prompt does not include any source code or PII — only the quantitative
    metrics collected from the GitHub API.
    """
    repo_blocks = "\n\n".join(_format_repo_block(m) for m in metrics)

    return f"""
You are a senior software engineer performing a zero-knowledge technical skill verification.

You have been given repository metadata (no source code, no commit messages, no author information)
from the top 3 most active GitHub repositories belonging to the user "{github_username}".

Your task is to analyse this metadata and produce a structured JSON verification report.

─── ASSESSMENT RULES ───────────────────────────────────────────────────────────
1. Base your assessment ONLY on the quantitative metrics below — no assumptions.
2. skill_level rubric:
     Junior    → < 6 months of consistent commits OR < 3 languages OR tiny repos
     Mid-Level → 6–24 months of activity, 3–6 languages, moderate repo sizes
     Senior    → 2+ years of activity signals, 5+ languages, large/complex repos
     Principal → Exceptional breadth, very high commit volume, 8+ languages
3. security_score (0–100):
     +20  if commit_count_90d > 10  (active maintenance)
     +20  if commit_count_1yr > 50  (sustained contribution)
     +20  if CI detected in at least one repo
     +20  if language_count >= 4    (defensive diversity)
     +20  if open_issues_count < 20 (responsive to issues)
     Deduct points for stale repos (commit_count_90d == 0) or very high open issues.
4. confidence:
     Low    → only 1 repo with data, or all commit counts are 0
     Medium → 2 repos with reasonable data
     High   → all 3 repos have commit history and language data
─── REPOSITORY METRICS ─────────────────────────────────────────────────────────
{repo_blocks}
─────────────────────────────────────────────────────────────────────────────────

Return a single JSON object matching the schema. No markdown, no explanation outside the JSON.
""".strip()


# ── Step 4: Call Gemini ───────────────────────────────────────────────────────

async def _call_gemini(
    github_username: str,
    metrics: list[RepoMetrics],
) -> VerificationReport:
    """
    Call the Gemini API with a structured prompt and parse the JSON response.

    Uses gemini-2.0-flash with response_mime_type="application/json" and an
    explicit response_schema to guarantee valid, parseable output.
    """
    genai.configure(api_key=settings.gemini_api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            temperature=0.2,          # Low temperature for consistent, factual output
            response_mime_type="application/json",
            response_schema=_VERIFICATION_SCHEMA,
        ),
    )

    prompt = _build_prompt(github_username, metrics)
    logger.debug("Sending analysis prompt to Gemini (%d chars).", len(prompt))

    # Gemini SDK is synchronous — run in a thread to avoid blocking the event loop
    response = await asyncio.to_thread(model.generate_content, prompt)

    raw_json: str = response.text
    logger.debug("Gemini raw response: %s", raw_json[:300])

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned invalid JSON: %s\nRaw: %s", exc, raw_json[:500])
        raise RuntimeError("Gemini returned a malformed JSON response.") from exc

    logger.info("Gemini parsed data: %s", data)
    try:
        return VerificationReport(
            skill_level=data["skill_level"],
            top_language=data["top_language"],
            security_score=int(data["security_score"]),
            confidence=data["confidence"],
            languages_detected=data.get("languages_detected", []),
            commit_frequency=data.get("commit_frequency", "N/A"),
            complexity_rating=data.get("complexity_rating", "Medium"),
            repos_analyzed=data.get("repos_analyzed", [m.name for m in metrics]),
            reasoning=data.get("reasoning", ""),
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
    except ValidationError as exc:
        logger.error("VerificationReport validation failed.\nData: %s\nErrors: %s", data, exc)
        raise RuntimeError(f"Gemini returned unexpected field values: {exc}") from exc


# ── Public entry point ────────────────────────────────────────────────────────

async def generate_verification_report(
    github_token: str,
    excluded_languages: set[str] | None = None,
    excluded_repos: set[str] | None = None,
) -> VerificationReport:
    """
    Full pipeline: Token Vault token → top repos → metrics → Gemini → VerificationReport.

    Args:
        github_token: A valid GitHub OAuth access token retrieved from Auth0 Token Vault.
                      Never logged, never returned to the caller.

    Returns:
        VerificationReport: Structured JSON assessment with skill_level, top_language,
                            security_score, and supporting metadata.

    Raises:
        ValueError:  No owned repositories found for the user.
        RuntimeError: GitHub API or Gemini API call failed.
    """
    excluded = (excluded_languages or set()) | _EXCLUDED_LANGUAGES
    excluded_repo_names = excluded_repos or set()

    # ── Phase 1: Fetch and rank repos (blocking I/O → run in thread) ──────────
    github_username, top_metrics = await asyncio.to_thread(
        _fetch_top_repos_sync, github_token
    )

    # Filter out user-excluded repos before ranking
    top_metrics = [m for m in top_metrics if m.name not in excluded_repo_names]

    if not top_metrics:
        raise ValueError(
            f"No owned non-fork repositories found for GitHub user '{github_username}'. "
            "Please create or push to at least one repository before requesting verification."
        )

    logger.info(
        "Analyzing top %d repos for %s: %s",
        len(top_metrics),
        github_username,
        [m.name for m in top_metrics],
    )

    # ── Filter excluded languages from each repo's metrics ───────────────────
    for m in top_metrics:
        m.languages = {k: v for k, v in m.languages.items() if k not in excluded}
        if m.languages:
            m.top_language = max(m.languages, key=m.languages.__getitem__)
            m.language_count = len(m.languages)
        else:
            m.top_language = "Unknown"
            m.language_count = 0

    # ── Phase 2: LLM analysis via Gemini ──────────────────────────────────────
    report = await _call_gemini(github_username, top_metrics)

    logger.info(
        "Verification report generated for %s: skill_level=%s  security_score=%d  confidence=%s",
        github_username,
        report.skill_level,
        report.security_score,
        report.confidence,
    )

    return report
