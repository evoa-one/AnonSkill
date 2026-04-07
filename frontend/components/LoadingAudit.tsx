'use client'

import { useEffect, useState } from 'react'

const STEPS = [
  'Connecting to Auth0 Token Vault…',
  'Retrieving GitHub access token…',
  'Fetching repository metadata…',
  'Ranking top 3 active repositories…',
  'Analyzing commit patterns and languages…',
  'Running AI assessment with Gemini…',
  'Compiling verification report…',
]

export default function LoadingAudit({ mode = 'verifying' }: { mode?: 'loading' | 'verifying' }) {
  const [completedSteps, setCompletedSteps] = useState<number>(0)
  const [dots, setDots] = useState('.')

  // Advance one step every ~1.4 s (realistic pacing for the ~8 s API call)
  useEffect(() => {
    if (completedSteps >= STEPS.length - 1) return
    const timer = setTimeout(
      () => setCompletedSteps((s) => s + 1),
      1400,
    )
    return () => clearTimeout(timer)
  }, [completedSteps])

  // Animate the trailing dots on the active step
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? '.' : d + '.'))
    }, 400)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col items-center gap-10 animate-fade-in">
      {/* Pulsing orb */}
      <div className="relative flex items-center justify-center w-24 h-24">
        <div className="absolute inset-0 rounded-full bg-cyan-500/10 animate-ping" />
        <div className="absolute inset-2 rounded-full bg-cyan-500/15 animate-pulse-slow" />
        <div className="relative w-14 h-14 rounded-full bg-slate-900 border border-cyan-500/40 flex items-center justify-center glow-cyan">
          <svg
            className="w-7 h-7 text-cyan-400 animate-spin-slow"
            fill="none"
            viewBox="0 0 24 24"
          >
            <path
              d="M12 3v3m0 12v3M3 12h3m12 0h3m-2.636-6.364-2.121 2.121M8.757 15.243l-2.121 2.121m0-14.849 2.121 2.121M15.243 15.243l2.121 2.121"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* Headline */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold text-slate-100">
          {mode === 'loading'
            ? `Fetching your repositories${dots}`
            : `AI Agent is verifying your skills${dots}`}
        </h2>
        <p className="text-slate-400 text-sm">
          {mode === 'loading'
            ? 'Connecting to GitHub via Auth0 Token Vault…'
            : 'Only metadata is processed — your source code is never read.'}
        </p>
      </div>

      {/* Step list — only shown during verification */}
      {mode === 'verifying' && (
        <div className="w-full max-w-sm space-y-3">
          {STEPS.map((step, i) => {
            const isDone    = i < completedSteps
            const isActive  = i === completedSteps
            const isPending = i > completedSteps

            return (
              <div
                key={step}
                className={`
                  flex items-center gap-3 text-sm transition-all duration-500
                  ${isPending ? 'opacity-30' : 'opacity-100'}
                `}
              >
                <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                  {isDone && (
                    <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24">
                      <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                  {isActive && (
                    <svg className="w-4 h-4 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="60 100" strokeLinecap="round" />
                    </svg>
                  )}
                  {isPending && (
                    <div className="w-4 h-4 rounded-full border border-slate-700" />
                  )}
                </div>
                <span className={isDone ? 'text-emerald-400' : isActive ? 'text-cyan-300' : 'text-slate-500'}>
                  {step}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {/* Trust badge */}
      <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-500">
        <svg className="w-3.5 h-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
            clipRule="evenodd"
          />
        </svg>
        Token secured by Auth0 Token Vault
      </div>
    </div>
  )
}
