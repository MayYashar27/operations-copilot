import { useId, useState } from 'react'
import { useElementWidth } from './useElementWidth'

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

/**
 * Tiny trend line for a KPI card. A line shows change rather than magnitude,
 * so it scales to the data range (unlike bars, which must start at zero).
 * The current day is marked; hovering reads any day's value.
 */
export function Sparkline({ points, format, height = 36 }: SparklineProps) {
  const [ref, width] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<number | null>(null)
  const gradientId = useId()

  const values = points.map((p) => p.value).filter((v): v is number => v !== null)
  const low = Math.min(...values)
  const high = Math.max(...values)
  // Never zoom in so far that a tiny difference (200 vs 199) looks dramatic:
  // the visible range is at least 15% of the value, centered on the data.
  const span = Math.max(high - low, Math.abs(high) * 0.15, 1)
  const min = low - (span - (high - low)) / 2
  const pad = 4
  const x = (i: number) => (points.length > 1 ? pad + (i / (points.length - 1)) * (width - pad * 2) : width / 2)
  const y = (v: number) => pad + (1 - (v - min) / span) * (height - pad * 2)

  const coords = points.map((p, i) => (p.value === null ? null : { x: x(i), y: y(p.value) }))
  const line = coords
    .filter((c): c is { x: number; y: number } => c !== null)
    .map((c, k) => `${k ? 'L' : 'M'}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(' ')
  const area = line ? `${line} L${x(points.length - 1)},${height} L${x(0)},${height} Z` : ''

  const markIndex = hovered ?? points.findIndex((p) => p.highlight)
  const mark = markIndex >= 0 ? coords[markIndex] : null
  const active = hovered !== null ? points[hovered] : null

  return (
    <div>
      <div ref={ref} className="relative" style={{ height }} onMouseLeave={() => setHovered(null)}>
        {width > 0 && (
          <svg width={width} height={height} aria-hidden>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="var(--color-chart-today)" stopOpacity="0.22" />
                <stop offset="1" stopColor="var(--color-chart-today)" stopOpacity="0" />
              </linearGradient>
            </defs>
            <path d={area} fill={`url(#${gradientId})`} />
            <path d={line} fill="none" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" className="stroke-chart-today" />
            {mark && <circle cx={mark.x} cy={mark.y} r={3.5} className="fill-chart-today stroke-surface" strokeWidth={2} />}
            {points.map((p, i) => (
              <rect key={p.key} x={x(i) - width / points.length / 2} y={0} width={width / points.length} height={height}
                fill="transparent" onMouseEnter={() => setHovered(i)} />
            ))}
          </svg>
        )}
      </div>
      <p className="mt-1 h-4 text-[11px] text-ink-3 tabular">
        {active ? (
          <>
            {active.label} · <span className="font-semibold text-ink-2">{active.value === null ? '—' : format(active.value)}</span>
          </>
        ) : (
          `${points.length}-day trend`
        )}
      </p>
    </div>
  )
}
