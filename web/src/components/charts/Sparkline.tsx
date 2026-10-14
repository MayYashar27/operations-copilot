import { useState } from 'react'

export interface SparkPoint {
  key: string
  label: string
  value: number | null
  highlight?: boolean
}

interface SparklineProps {
  points: SparkPoint[]
  format: (value: number) => string
  height?: number
}

/** Tiny bar trend for a KPI tile. The current day is highlighted; hover reads values. */
export function Sparkline({ points, format, height = 30 }: SparklineProps) {
  const [hovered, setHovered] = useState<number | null>(null)
  const values = points.map((p) => p.value ?? 0)
  // Bars always start at zero; a truncated baseline would exaggerate changes.
  const max = Math.max(...values, 1)

  const active = hovered !== null ? points[hovered] : null

  return (
    <div className="relative">
      <div className="flex items-end gap-[3px]" style={{ height }} onMouseLeave={() => setHovered(null)}>
        {points.map((point, i) => {
          const ratio = (point.value ?? 0) / max
          return (
            <div
              key={point.key}
              className="flex h-full flex-1 cursor-default items-end"
              onMouseEnter={() => setHovered(i)}
            >
              <div
                className={`w-full rounded-t-[2px] transition-colors ${
                  point.highlight ? 'bg-chart-today' : hovered === i ? 'bg-ink-3' : 'bg-chart-muted'
                }`}
                style={{ height: `${Math.max(2, ratio * 100)}%` }}
              />
            </div>
          )
        })}
      </div>
      <p className="mt-1.5 h-4 text-[11px] text-ink-3 tabular">
        {active ? (
          <>
            {active.label} · <span className="font-medium text-ink-2">{active.value === null ? '—' : format(active.value)}</span>
          </>
        ) : (
          `${points.length}-day trend`
        )}
      </p>
    </div>
  )
}
