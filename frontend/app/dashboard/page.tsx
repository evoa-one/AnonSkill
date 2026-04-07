'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import LoadingAudit from '@/components/LoadingAudit'
import VerificationCard from '@/components/VerificationCard'
import { checkVaultStatus, initiateGitHubConnect, fetchVerificationReport, fetchRepos } from '@/lib/api'
import type { RepoInfo, VerificationReport } from '@/lib/types'

const COMMON_LANGUAGES = [
  'JavaScript', 'TypeScript', 'Python', 'Java', 'Go', 'Rust', 'C', 'C++',
  'C#', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB',
  'Vue', 'HTML', 'CSS', 'SCSS', 'XSLT', 'XML', 'Shell', 'Dockerfile',
]

const DEFAULT_EXCLUDED = new Set<string>()

type State =
  | { phase: 'loading' }
  | { phase: 'step-languages'; token: string; repos: RepoInfo[] }
  | { phase: 'step-repos';     token: string; repos: RepoInfo[] }
  | { phase: 'verifying' }
  | { phase: 'success'; report: VerificationReport }
  | { phase: 'error';   message: string }

export default function DashboardPage() {
  const router = useRouter()
  const [state, setState] = useState<State>({ phase: 'loading' })
  const [excluded, setExcluded] = useState<Set<string>>(new Set(DEFAULT_EXCLUDED))
  const [excludedRepos, setExcludedRepos] = useState<Set<string>>(new Set())

  useEffect(() => {
    const fragment        = window.location.hash.slice(1)
    const params          = new URLSearchParams(fragment)
    const tokenFromFragment = params.get('access_token')
    const token           = tokenFromFragment ?? sessionStorage.getItem('auth_token')

    if (!token) {
      router.replace('/')
      return
    }

    sessionStorage.setItem('auth_token', token)
    window.history.replaceState(null, '', '/dashboard')

    let cancelled = false

    async function run() {
      try {
        const { connected } = await checkVaultStatus(token!)
        if (cancelled) return

        if (!connected) {
          const { connect_url } = await initiateGitHubConnect(token!)
          if (cancelled) return
          window.location.href = connect_url
          return
        }

        const { repos } = await fetchRepos(token!)
        if (!cancelled) setState({ phase: 'step-languages', token: token!, repos })
      } catch (err: unknown) {
        if (cancelled) return
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred.'
        setState({ phase: 'error', message })
      }
    }

    run()
    return () => { cancelled = true }
  }, [router])

  async function runVerification(token: string) {
    setState({ phase: 'verifying' })
    try {
      sessionStorage.removeItem('auth_token')
      const report = await fetchVerificationReport(token, Array.from(excluded), Array.from(excludedRepos))
      setState({ phase: 'success', report })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred.'
      setState({ phase: 'error', message })
    }
  }

  function toggleLanguage(lang: string) {
    setExcluded(prev => {
      const next = new Set(prev)
      if (next.has(lang)) next.delete(lang)
      else next.add(lang)
      return next
    })
  }

  function toggleRepo(name: string) {
    setExcludedRepos(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  // ── Loading / Verifying ───────────────────────────────────────────────────

  if (state.phase === 'loading' || state.phase === 'verifying') {
    return (
      <div className="min-h-screen bg-mesh bg-dots flex flex-col items-center justify-center px-6 py-16">
        <LoadingAudit mode={state.phase === 'verifying' ? 'verifying' : 'loading'} />
      </div>
    )
  }

  // ── Step 1: Languages ─────────────────────────────────────────────────────

  if (state.phase === 'step-languages') {
    // Collect all unique languages across all repos
    const allLangs = Array.from(
      new Set(state.repos.flatMap(r => r.languages))
    ).sort()

    return (
      <div className="min-h-screen bg-mesh bg-dots flex flex-col items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl space-y-5 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-6 rounded-full bg-cyan-500 text-slate-950 text-xs font-bold flex items-center justify-center">1</div>
              <div className="w-12 h-0.5 bg-slate-700" />
              <div className="w-6 h-6 rounded-full bg-slate-700 text-slate-400 text-xs font-bold flex items-center justify-center">2</div>
            </div>
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-slate-100">Verify Your Skills</h2>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Step 1 — Exclude Languages</p>
            <p className="text-sm text-slate-400">
              Remove languages that don't reflect your engineering skills (markup, config, etc).
              Repos will be scored based on the remaining languages.
            </p>
          </div>

          <div className="glass rounded-2xl p-5 space-y-3">
            <p className="text-xs text-slate-500 uppercase tracking-widest">
              Your Languages ({allLangs.length - excluded.size} of {allLangs.length} included)
            </p>
            <div className="flex flex-wrap gap-2">
              {allLangs.map((lang) => {
                const isExcluded = excluded.has(lang)
                return (
                  <button
                    key={lang}
                    onClick={() => toggleLanguage(lang)}
                    className={`
                      px-3 py-1.5 rounded-lg text-sm font-medium border transition-all duration-150
                      ${isExcluded
                        ? 'bg-slate-800/50 text-slate-500 border-slate-700/50 line-through'
                        : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/25 hover:bg-cyan-500/20'
                      }
                    `}
                  >
                    {lang}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-slate-600">Click to exclude. Strikethrough = excluded.</p>
          </div>

          <button
            onClick={() => setState({ ...state, phase: 'step-repos' })}
            className="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-colors duration-150"
          >
            Next: Choose Repositories →
          </button>
        </div>
      </div>
    )
  }

  // ── Step 2: Repos ─────────────────────────────────────────────────────────

  if (state.phase === 'step-repos') {
    // Filter each repo's language list by excluded langs, then sort by remaining lang count
    const reposWithFilteredLangs = state.repos.map(r => ({
      ...r,
      languages: r.languages.filter(l => !excluded.has(l)),
      top_language: r.languages.find(l => !excluded.has(l)) ?? 'Unknown',
    })).sort((a, b) => b.languages.length - a.languages.length)

    const includedCount = reposWithFilteredLangs.filter(r => !excludedRepos.has(r.name)).length

    return (
      <div className="min-h-screen bg-mesh bg-dots flex flex-col items-center justify-center px-6 py-16">
        <div className="w-full max-w-2xl space-y-5 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex items-center gap-1.5">
              <div className="w-6 h-6 rounded-full bg-slate-700 text-slate-400 text-xs font-bold flex items-center justify-center">1</div>
              <div className="w-12 h-0.5 bg-cyan-500" />
              <div className="w-6 h-6 rounded-full bg-cyan-500 text-slate-950 text-xs font-bold flex items-center justify-center">2</div>
            </div>
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-bold text-slate-100">Verify Your Skills</h2>
            <p className="text-xs text-slate-500 uppercase tracking-widest mb-1">Step 2 — Choose Repositories</p>
            <p className="text-sm text-slate-400">
              Deselect repos you don't want included. Top 3 by activity will be analyzed.
            </p>
          </div>

          <div className="glass rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500 uppercase tracking-widest">Repositories</p>
              <p className="text-xs text-slate-500">{includedCount} of {state.repos.length} selected</p>
            </div>
            <div className="grid grid-cols-2 gap-2 max-h-[480px] overflow-y-auto pr-1">
              {reposWithFilteredLangs.map((repo) => {
                const isExcluded = excludedRepos.has(repo.name)
                return (
                  <button
                    key={repo.name}
                    onClick={() => toggleRepo(repo.name)}
                    className={`
                      w-full flex items-center justify-between px-4 py-2.5 rounded-xl border text-left transition-all duration-150
                      ${isExcluded
                        ? 'bg-slate-800/30 border-slate-800 opacity-40'
                        : 'bg-slate-900/50 border-slate-700 hover:border-slate-600'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isExcluded ? 'bg-slate-600' : 'bg-emerald-400'}`} />
                      <span className={`text-sm font-medium truncate ${isExcluded ? 'text-slate-500 line-through' : 'text-slate-100'}`}>
                        {repo.name}
                      </span>
                      {repo.is_org && (
                        <span className="text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded flex-shrink-0">org</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      {repo.languages.slice(0, 2).map(l => (
                        <span key={l} className="text-xs text-slate-500">{l}</span>
                      ))}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => setState({ ...state, phase: 'step-languages' })}
              className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium border border-slate-700 transition-colors duration-150"
            >
              ← Back
            </button>
            <button
              onClick={() => runVerification(state.token)}
              disabled={includedCount === 0}
              className="flex-1 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 font-semibold text-sm transition-colors duration-150"
            >
              Run Verification → (top 3 of {includedCount})
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── Error ──────────────────────────────────────────────────────────────────

  if (state.phase === 'error') {
    return (
      <div className="min-h-screen bg-mesh bg-dots flex flex-col items-center justify-center px-6 py-16 gap-6 animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
            />
          </svg>
        </div>

        <div className="text-center space-y-2">
          <h2 className="text-xl font-semibold text-slate-100">Verification Failed</h2>
          <p className="text-sm text-slate-400 max-w-sm">{state.message}</p>
        </div>

        <button
          onClick={() => router.push('/')}
          className="px-6 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 border border-slate-700 text-sm font-medium transition-colors duration-150"
        >
          ← Back to Home
        </button>
      </div>
    )
  }

  // ── Success ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-mesh bg-dots">
      {/* Minimal nav */}
      <nav className="sticky top-0 z-10 border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-100 transition-colors duration-150"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Back
          </button>

          <div className="flex items-center gap-2 text-xs text-emerald-400">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Verified
          </div>
        </div>
      </nav>

      {/* Report */}
      <div className="max-w-5xl mx-auto px-6 py-12 flex flex-col items-center gap-8">
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-slate-100">
            Your Skill Verification is Ready
          </h1>
          <p className="text-sm text-slate-400">
            Generated from repository metadata only — no source code was read.
          </p>
        </div>

        <VerificationCard
          report={state.report}
          onReset={() => router.push('/')}
        />
      </div>
    </div>
  )
}
