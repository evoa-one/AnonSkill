'use client'

import { useEffect, useState } from 'react'

interface ScoreGaugeProps {
  score: number   // 0–100
  size?: number   // px, default 120
}

function scoreColor(score: number): { stroke: string; text: string; label: string } {
  if (score >= 80) return { stroke: '#10b981', text: 'text-emerald-400', label: 'Excellent' }
  if (score >= 60) return { stroke: '#06b6d4', text: 'text-cyan-400',    label: 'Good'      }
  if (score >= 40) return { stroke: '#f59e0b', text: 'text-amber-400',   label: 'Fair'      }
  return             { stroke: '#ef4444', text: 'text-red-400',           label: 'Low'       }
}

export default function ScoreGauge({ score, size = 120 }: ScoreGaugeProps) {
  const [animated, setAnimated] = useState(0)

  // Animate from 0 → score on mount
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(score), 100)
    return () => clearTimeout(timer)
  }, [score])

  const { stroke, text, label } = scoreColor(score)

  const radius      = 44
  const circumference = 2 * Math.PI * radius
  // We only draw 75% of the circle (270°) as the gauge arc
  const arcLength   = circumference * 0.75
  const dashOffset  = arcLength - (animated / 100) * arcLength

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox="0 0 100 100"
          className="-rotate-[135deg]"
        >
          {/* Track */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="#1e293b"
            strokeWidth="8"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Fill */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke={stroke}
            strokeWidth="8"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-2xl font-bold tabular-nums ${text}`}>
            {animated}
          </span>
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">
            / 100
          </span>
        </div>
      </div>

      <span className={`text-xs font-medium ${text}`}>{label}</span>
    </div>
  )
}
