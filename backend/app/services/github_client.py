"""
GitHub API client – zero-knowledge edition.

All methods in this module accept a raw GitHub access token and return
sanitized summaries.  Raw file content, commit diffs, email addresses,
and any other PII are stripped before returning data to callers.

We use PyGithub for typed access to the REST API and fall back to httpx
only for endpoints that PyGithub does not expose.
"""

import logging

import httpx
from github import Github, GithubException
from github.Repository import Repository

from app.models.schemas import RepoSummary, SkillReport

logger = logging.getLogger(__name__)


# ── Low-level helpers ─────────────────────────────────────────────────────────


def _make_github_client(access_token: str) -> Github:
    """
    Create an authenticated PyGithub client.

    The token is used only for this call and is never stored on the object
    after the analysis function returns.
    """
    return Github(access_token, per_page=100)


# ── Repository metadata ───────────────────────────────────────────────────────


def _summarize_repo(repo: Repository) -> RepoSummary:
    """
    Convert a PyGithub Repository into a zero-knowledge RepoSummary.

    Excluded on purpose:
    - Full clone URL (reveals username)
    - Commit messages (can contain PII)
    - Contributor list / email addresses
    - Raw file content
    """
    try:
        languages: dict[str, int] = repo.get_languages()
    except GithubException:
        languages = {}

    try:
        topics: list[str] = repo.get_topics()
    except GithubException:
        topics = []

    return RepoSummary(
        name=repo.name,
        primary_language=repo.language,
        languages=languages,
        topic_tags=topics,
        is_private=repo.private,
        star_count=repo.stargazers_count,
        fork_count=repo.forks_count,
    )


# ── Skill detection ───────────────────────────────────────────────────────────

_LANGUAGE_SKILL_MAP: dict[str, str] = {
    "Python": "Python",
    "TypeScript": "TypeScript",
    "JavaScript": "JavaScript",
    "Go": "Go",
    "Rust": "Rust",
    "Java": "Java",
    "Kotlin": "Kotlin",
    "Swift": "Swift",
    "C": "C",
    "C++": "C++",
    "C#": "C#",
    "Ruby": "Ruby",
    "PHP": "PHP",
    "Shell": "Shell scripting",
    "Dockerfile": "Docker",
    "HCL": "Terraform / IaC",
    "Bicep": "Azure Bicep / IaC",
}

_TOPIC_ARCHITECTURE_MAP: dict[str, str] = {
    "microservices": "Microservices",
    "event-driven": "Event-driven architecture",
    "serverless": "Serverless",
    "rest-api": "REST API design",
    "graphql": "GraphQL",
    "grpc": "gRPC",
    "machine-learning": "Machine Learning",
    "deep-learning": "Deep Learning",
    "llm": "Large Language Models",
    "rag": "Retrieval-Augmented Generation",
}


def _derive_skills(repos: list[RepoSummary]) -> tuple[list[str], list[str], list[str]]:
    """
    Derive skills, top languages, and architecture patterns from repo summaries.

    Returns:
        (detected_skills, top_languages, architecture_patterns)
    """
    # Aggregate language byte counts across all repos
    language_totals: dict[str, int] = {}
    for repo in repos:
        for lang, byte_count in repo.languages.items():
            language_totals[lang] = language_totals.get(lang, 0) + byte_count

    top_languages = [
        lang
        for lang, _ in sorted(language_totals.items(), key=lambda x: x[1], reverse=True)
        if lang in _LANGUAGE_SKILL_MAP
    ][:6]

    detected_skills = list({_LANGUAGE_SKILL_MAP[lang] for lang in top_languages})

    # Derive architecture patterns from topic tags
    all_topics = {tag.lower() for repo in repos for tag in repo.topic_tags}
    architecture_patterns = list(
        {pattern for topic_key, pattern in _TOPIC_ARCHITECTURE_MAP.items() if topic_key in all_topics}
    )

    return detected_skills, top_languages, architecture_patterns


# ── Public API ────────────────────────────────────────────────────────────────


async def build_skill_report(github_token: str, max_repos: int = 30) -> SkillReport:
    """
    Build a SkillReport by inspecting the authenticated user's repositories.

    The GitHub access token is used in-memory only and is not persisted,
    logged, or included in the returned SkillReport.

    Args:
        github_token: A valid GitHub OAuth access token retrieved from
                      Auth0 Token Vault.  Never log or return this value.
        max_repos:    Maximum number of repositories to inspect (default 30).
                      Capped to avoid excessively long API calls.

    Returns:
        SkillReport: Structured skill assessment with no raw code or PII.

    Raises:
        GithubException: If the GitHub API returns an error (e.g. token revoked).
        RuntimeError:    On unexpected failures.
    """
    client = _make_github_client(github_token)

    try:
        authenticated_user = client.get_user()
        github_username = authenticated_user.login
        logger.info("Building skill report for GitHub user: %s", github_username)

        # Fetch all repositories (owned, not forked) up to max_repos
        all_repos = authenticated_user.get_repos(type="owner", sort="updated")

        repo_summaries: list[RepoSummary] = []
        for repo in all_repos:
            if len(repo_summaries) >= max_repos:
                break
            if repo.fork:
                # Forks reflect others' skills, skip them
                continue
            try:
                summary = _summarize_repo(repo)
                repo_summaries.append(summary)
            except GithubException as exc:
                # A single inaccessible repo should not abort the whole analysis
                logger.warning("Skipping repo %s due to GitHub error: %s", repo.name, exc)

        detected_skills, top_languages, architecture_patterns = _derive_skills(repo_summaries)

        return SkillReport(
            github_username=github_username,
            total_repos_analyzed=len(repo_summaries),
            detected_skills=detected_skills,
            top_languages=top_languages,
            architecture_patterns=architecture_patterns,
            repo_summaries=repo_summaries,
            raw_code_included=False,  # enforced: we never fetch file content
        )

    finally:
        # Explicitly close the underlying connection pool
        client.close()


async def fetch_repo_languages_raw(github_token: str, repo_full_name: str) -> dict[str, int]:
    """
    Fetch the language breakdown for a single repository using httpx.

    This is an alternative to PyGithub for callers that need a lighter-weight
    dependency or want to reuse an existing httpx.AsyncClient.

    Args:
        github_token:   GitHub OAuth access token.
        repo_full_name: "{owner}/{repo}", e.g. "octocat/Hello-World".

    Returns:
        dict mapping language name → byte count.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/languages"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=10) as http:
        response = await http.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
