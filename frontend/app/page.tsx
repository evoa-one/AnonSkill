import ConnectButton from '@/components/ConnectButton'

const ZK_STEPS = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.955 11.955 0 003 12c0 6.627 5.373 12 12 12s12-5.373 12-12c0-1.999-.487-3.888-1.348-5.553A11.956 11.956 0 0012 2.764z" />
      </svg>
    ),
    title: 'Token Vault, not source code',
    description:
      'Auth0 Token Vault stores your GitHub token server-side. Your repos are accessed only to read language stats and commit counts — never file content.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
      </svg>
    ),
    title: 'AI reads patterns, not code',
    description:
      'Gemini analyzes commit frequency, language distribution, and repo activity — quantitative signals only. It produces a skill score without seeing a single function.',
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    title: 'You get a signed report',
    description:
      'The output is a structured JSON report — skill level, security score, top languages — that you can share with employers or embed in your portfolio.',
  },
]

const FEATURES = [
  { label: 'Private repos supported',  icon: '🔒' },
  { label: 'No code ever exposed',      icon: '🛡️' },
  { label: 'AI-powered assessment',     icon: '🤖' },
  { label: 'Instant JSON report',       icon: '⚡' },
]

export default function HomePage() {
  return (
    <main className="min-h-screen bg-mesh bg-dots">
      {/* Nav */}
      <nav className="sticky top-0 z-10 border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <div className="w-6 h-6 rounded-md bg-cyan-500 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-slate-950" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
            </div>
            AnonSkill
          </div>
          <span className="text-xs text-slate-500 hidden sm:block">
            Powered by Auth0 Token Vault · Gemini
          </span>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-24 pb-20 text-center space-y-8">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-300 font-medium">
          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          Auth0 for AI Agents Hackathon
        </div>

        {/* Headline */}
        <h1 className="text-5xl sm:text-6xl font-extrabold leading-tight tracking-tight text-slate-50">
          Your Skills.{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-violet-400">
            Verified.
          </span>
          <br />
          Without Exposing Your Code.
        </h1>

        <p className="max-w-xl mx-auto text-lg text-slate-400 leading-relaxed">
          Connect your GitHub account. Our AI agent analyzes your{' '}
          <span className="text-slate-300">private repositories</span> using only
          metadata — commit patterns, language usage, and activity signals — and
          generates a{' '}
          <span className="text-slate-300">cryptographically-trusted skill report</span>.
        </p>

        {/* CTA */}
        <div className="pt-2">
          <ConnectButton />
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
          {FEATURES.map((f) => (
            <div
              key={f.label}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-sm text-slate-400"
            >
              <span>{f.icon}</span>
              {f.label}
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="text-center mb-12 space-y-2">
          <p className="text-xs text-slate-500 uppercase tracking-widest">How it works</p>
          <h2 className="text-2xl font-bold text-slate-100">Zero-Knowledge by Design</h2>
          <p className="text-slate-400 text-sm max-w-lg mx-auto">
            Three guarantees that ensure your intellectual property stays yours.
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-4">
          {ZK_STEPS.map((step, i) => (
            <div
              key={step.title}
              className="glass rounded-2xl p-6 space-y-4 hover:border-slate-700 transition-colors duration-200"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  {step.icon}
                </div>
                <span className="text-xs font-medium text-slate-500">Step {i + 1}</span>
              </div>
              <h3 className="font-semibold text-slate-100">{step.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Report preview mockup */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <div className="text-center mb-10 space-y-2">
          <p className="text-xs text-slate-500 uppercase tracking-widest">What you get</p>
          <h2 className="text-2xl font-bold text-slate-100">A Verifiable Skill Report</h2>
        </div>

        <div className="relative glass rounded-2xl p-6 overflow-hidden">
          {/* Blur overlay with CTA */}
          <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950 via-slate-950/80 to-transparent z-10 flex items-end justify-center pb-6">
            <ConnectButton />
          </div>

          {/* Mock report */}
          <div className="grid sm:grid-cols-3 gap-4 blur-sm select-none pointer-events-none">
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Skill Level</p>
              <span className="px-4 py-2 rounded-xl text-lg font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">Senior</span>
            </div>
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Security Score</p>
              <p className="text-4xl font-bold text-emerald-400">85 <span className="text-sm text-slate-500">/ 100</span></p>
            </div>
            <div className="bg-slate-900 rounded-xl p-4 border border-slate-800">
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-2">Top Language</p>
              <p className="text-2xl font-bold text-slate-100">Python</p>
            </div>
            <div className="sm:col-span-3 bg-slate-900 rounded-xl p-4 border border-slate-800">
              <p className="text-xs text-slate-500 uppercase tracking-widest mb-3">Languages Detected</p>
              <div className="flex gap-2">
                {['Python', 'TypeScript', 'Go', 'Dockerfile', 'Shell'].map((l) => (
                  <span key={l} className="px-3 py-1 rounded-lg text-sm bg-slate-800 text-slate-400 border border-slate-700">{l}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 py-8">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600">
          <p>Built for the Auth0 for AI Agents Hackathon</p>
          <p>
            Zero source code is read at any point during analysis.
          </p>
        </div>
      </footer>
    </main>
  )
}
