'use client'

import ScoreGauge from './ScoreGauge'
import type { VerificationReport } from '@/lib/types'

interface Props {
  report: VerificationReport
  onReset: () => void
}

const SKILL_STYLES: Record<string, string> = {
  Junior:     'bg-blue-500/15   text-blue-300   border-blue-500/30',
  'Mid-Level':'bg-purple-500/15 text-purple-300 border-purple-500/30',
  Senior:     'bg-cyan-500/15   text-cyan-300   border-cyan-500/30',
  Principal:  'bg-amber-500/15  text-amber-300  border-amber-500/30',
}

const COMPLEXITY_STYLES: Record<string, string> = {
  Low:        'text-emerald-400',
  Medium:     'text-cyan-400',
  High:       'text-amber-400',
  'Very High':'text-red-400',
}

const CONFIDENCE_STYLES: Record<string, string> = {
  Low:   'bg-slate-800 text-slate-400',
  Medium:'bg-cyan-500/10 text-cyan-300',
  High:  'bg-emerald-500/10 text-emerald-300',
}

const LANG_COLORS = [
  'bg-cyan-500/15   text-cyan-300   border-cyan-500/25',
  'bg-violet-500/15 text-violet-300 border-violet-500/25',
  'bg-emerald-500/15 text-emerald-300 border-emerald-500/25',
  'bg-amber-500/15  text-amber-300  border-amber-500/25',
  'bg-rose-500/15   text-rose-300   border-rose-500/25',
  'bg-sky-500/15    text-sky-300    border-sky-500/25',
]

function Divider() {
  return <div className="border-t border-slate-800/80" />
}

function StatCard({
  label,
  value,
  sub,
  valueClass = 'text-slate-100',
}: {
  label: string
  value: string
  sub?: string
  valueClass?: string
}) {
  return (
    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-800 space-y-1">
      <p className="text-xs text-slate-500 uppercase tracking-widest">{label}</p>
      <p className={`text-lg font-semibold ${valueClass}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

export default function VerificationCard({ report, onReset }: Props) {
  const formattedDate = new Date(report.generated_at).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

  function handleDownload() {
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a   = document.createElement('a')
    a.href    = url
    a.download = `verification-report-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="w-full max-w-2xl animate-slide-up space-y-1">
      {/* Header */}
      <div className="glass rounded-2xl p-6 space-y-5">
        {/* Title row */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs text-slate-400 uppercase tracking-widest">
                Zero-Knowledge Verification
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-100">Verification Report</h2>
          </div>
          <span
            className={`
              inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border
              ${CONFIDENCE_STYLES[report.confidence]}
            `}
          >
            {report.confidence} Confidence
          </span>
        </div>

        <Divider />

        {/* Skill level + score + language row */}
        <div className="flex flex-wrap items-center justify-between gap-6">
          {/* Skill level badge */}
          <div className="space-y-2">
            <p className="text-xs text-slate-500 uppercase tracking-widest">Skill Level</p>
            <span
              className={`
                inline-flex items-center px-4 py-2 rounded-xl text-lg font-bold border
                ${SKILL_STYLES[report.skill_level] ?? SKILL_STYLES.Senior}
              `}
            >
              {report.skill_level}
            </span>
          </div>

          {/* Security score */}
          <div className="space-y-1 text-center">
            <p className="text-xs text-slate-500 uppercase tracking-widest">Security Score</p>
            <ScoreGauge score={report.security_score} size={110} />
          </div>

          {/* Top language */}
          <div className="space-y-2">
            <p className="text-xs text-slate-500 uppercase tracking-widest">Top Language</p>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-cyan-400" />
              <span className="text-xl font-bold text-slate-100">{report.top_language}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-1">
        <StatCard
          label="Commit Frequency"
          value={report.commit_frequency}
        />
        <StatCard
          label="Complexity"
          value={report.complexity_rating}
          valueClass={COMPLEXITY_STYLES[report.complexity_rating] ?? 'text-slate-100'}
        />
      </div>

      {/* Languages */}
      <div className="glass rounded-2xl p-5 space-y-3">
        <p className="text-xs text-slate-500 uppercase tracking-widest">Languages Detected</p>
        <div className="flex flex-wrap gap-2">
          {report.languages_detected.map((lang, i) => (
            <span
              key={lang}
              className={`
                inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium border
                ${LANG_COLORS[i % LANG_COLORS.length]}
              `}
            >
              {lang}
            </span>
          ))}
        </div>
      </div>

      {/* Repos analyzed */}
      <div className="glass rounded-2xl p-5 space-y-3">
        <p className="text-xs text-slate-500 uppercase tracking-widest">Repositories Analyzed</p>
        <div className="space-y-2">
          {report.repos_analyzed.map((repo) => (
            <div key={repo} className="flex items-center gap-2 text-sm text-slate-300">
              <svg
                className="w-4 h-4 text-slate-500 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 7a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
                />
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 11h8M8 15h5" />
              </svg>
              {repo}
              <span className="ml-auto text-xs text-slate-600">private</span>
            </div>
          ))}
        </div>
      </div>

      {/* AI Reasoning */}
      <div className="glass rounded-2xl p-5 space-y-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-violet-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
          </svg>
          <p className="text-xs text-slate-500 uppercase tracking-widest">AI Assessment</p>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{report.reasoning}</p>
      </div>

      {/* Footer */}
      <div className="glass rounded-2xl p-4 flex items-center justify-between gap-4">
        <p className="text-xs text-slate-500">
          Generated at{' '}
          <span className="text-slate-400">{formattedDate}</span>
        </p>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
              bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100
              border border-slate-700 transition-colors duration-150
            "
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1M8 12l4 4m0 0l4-4m-4 4V4" />
            </svg>
            Download JSON
          </button>

          <button
            onClick={onReset}
            className="
              inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
              bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-300
              border border-slate-800 transition-colors duration-150
            "
          >
            Run again
          </button>
        </div>
      </div>

      {/* Zero-knowledge trust note */}
      <div className="flex items-center justify-center gap-2 pt-1 text-xs text-slate-600">
        <svg className="w-3.5 h-3.5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
            clipRule="evenodd"
          />
        </svg>
        Zero source code was read during this analysis.
      </div>
    </div>
  )
}
