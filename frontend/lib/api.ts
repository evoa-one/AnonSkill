import type { RepoInfo, VerificationReport } from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/**
 * Step 1 of the OAuth flow.
 * Asks the backend to build the Auth0 authorization URL, then redirects
 * the browser to it.  Auth0 will handle the GitHub OAuth dance and
 * redirect back to /oauth/callback on the backend, which in turn
 * redirects to /dashboard#access_token=...
 */
export async function initiateGitHubOAuth(): Promise<void> {
  const res = await fetch(`${API_URL}/oauth/github/authorize`)
  if (!res.ok) {
    throw new Error(`Failed to initiate OAuth flow: ${res.status}`)
  }
  const { authorization_url } = await res.json()
  window.location.href = authorization_url
}

/**
 * Fetch the list of repos available for verification (used in configure step).
 */
export async function fetchRepos(
  accessToken: string,
): Promise<{ github_username: string; repos: RepoInfo[] }> {
  const res = await fetch(`${API_URL}/agent/repos`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error(`Failed to fetch repos: ${res.status}`)
  return res.json()
}

/**
 * Check whether the user's GitHub token is stored in Auth0 Token Vault.
 */
export async function checkVaultStatus(
  accessToken: string,
): Promise<{ connected: boolean }> {
  const res = await fetch(`${API_URL}/agent/vault/status`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) throw new Error(`Vault status check failed: ${res.status}`)
  return res.json()
}

/**
 * Initiate the Token Vault Connected Account flow.
 * Returns connect_url — caller must redirect the browser there.
 */
export async function initiateGitHubConnect(
  accessToken: string,
): Promise<{ connect_url: string }> {
  const res = await fetch(`${API_URL}/oauth/github/connect`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail ?? `Connect failed: ${res.status}`)
  }
  return res.json()
}

/**
 * Step 2 of the flow — called from the dashboard after the access token
 * arrives in the URL fragment.
 *
 * Calls POST /agent/verify with the Auth0 Bearer token.
 * The backend retrieves the GitHub token from Token Vault and returns
 * a VerificationReport without ever exposing source code.
 */
export async function fetchVerificationReport(
  accessToken: string,
  excludedLanguages: string[] = [],
  excludedRepos: string[] = [],
): Promise<VerificationReport> {
  const res = await fetch(`${API_URL}/agent/verify`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      excluded_languages: excludedLanguages,
      excluded_repos: excludedRepos,
    }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail ?? `Verification failed: ${res.status}`)
  }

  return res.json() as Promise<VerificationReport>
}
