import { useId, useState } from 'react'
import { ChartTooltip, TooltipRow } from './ChartTooltip'
import { niceScale, useElementWidth } from './useElementWidth'

export interface TrendPoint {
  key: string
  label: string        // x-axis label
  tooltip: string      // full label in the tooltip
  value: number | null
  highlight?: boolean  // e.g. the report day
}

interface Props {
  points: TrendPoint[]
  format: (v: number) => string
  reference?: { value: number; label: string }
  height?: number
}

const MARGIN = { top: 14, right: 12, bottom: 28, left: 40 }

/** One series over time, with an optional reference line (e.g. team average). */
export function TrendLineChart({ points, format, reference, height = 220 }: Props) {
  const [ref, width] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<number | null>(null)
  const gradientId = useId()

  const plotW = Math.max(0, width - MARGIN.left - MARGIN.right)
  const plotH = height - MARGIN.top - MARGIN.bottom
  const values = points.map((p) => p.value ?? 0)
  const { max, step } = niceScale(Math.max(...values, reference?.value ?? 0, 1) * 1.1)
  const x = (i: number) => MARGIN.left + (points.length > 1 ? (i / (points.length - 1)) * plotW : plotW / 2)
  const y = (v: number) => MARGIN.top + plotH - (v / max) * plotH
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step)

  const present = points.map((p, i) => ({ p, i })).filter(({ p }) => p.value !== null)
  const line = present.map(({ p, i }, k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value!).toFixed(1)}`).join(' ')
  const area = present.length
    ? `${line} L${x(present[present.length - 1].i)},${y(0)} L${x(present[0].i)},${y(0)} Z`
    : ''
  const band = points.length ? plotW / Math.max(1, points.length - 1) : 0
  const active = hovered !== null ? points[hovered] : null

  return (
    <div ref={ref} className="relative select-none" style={{ height }} onMouseLeave={() => setHovered(null)}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Daily trend line chart">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="var(--color-chart-today)" stopOpacity="0.24" />
              <stop offset="1" stopColor="var(--color-chart-today)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(t)} y2={y(t)} className={t === 0 ? 'stroke-chart-axis' : 'stroke-chart-grid'} />
              <text x={MARGIN.left - 10} y={y(t)} dy="0.32em" textAnchor="end" className="fill-ink-3 text-[11px] tabular">
                {format(t)}
              </text>
            </g>
          ))}

          {reference && (
            <g>
              <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(reference.value)} y2={y(reference.value)}
                className="stroke-chart-typical" strokeWidth={1.5} />
              <text x={width - MARGIN.right} y={y(reference.value) - 6} textAnchor="end" className="fill-ink-2 text-[11px] font-semibold">
                {reference.label} {format(reference.value)}
              </text>
            </g>
          )}

          {hovered !== null && (
            <line x1={x(hovered)} x2={x(hovered)} y1={MARGIN.top} y2={MARGIN.top + plotH} className="stroke-accent/30" />
          )}

          <path d={area} fill={`url(#${gradientId})`} />
          <path d={line} fill="none" strokeWidth={2.25} strokeLinejoin="round" strokeLinecap="round" className="stroke-chart-today" />
          {present.map(({ p, i }) => (
            <circle key={p.key} cx={x(i)} cy={y(p.value!)} r={hovered === i || p.highlight ? 5 : 3}
              className={`stroke-surface transition-[r] ${p.highlight ? 'fill-accent-2' : 'fill-chart-today'}`} strokeWidth={2} />
          ))}

          {points.map((p, i) => (
            <text key={p.key} x={x(i)} y={height - 8} textAnchor="middle"
              className={`text-[10.5px] tabular ${hovered === i || p.highlight ? 'fill-ink font-semibold' : 'fill-ink-3'}`}>
              {p.label}
            </text>
          ))}

          {points.map((p, i) => (
            <rect key={p.key} x={x(i) - band / 2} y={MARGIN.top} width={band} height={plotH + MARGIN.bottom}
              fill="transparent" onMouseEnter={() => setHovered(i)} />
          ))}
        </svg>
      )}

      {active && hovered !== null && active.value !== null && (
        <ChartTooltip x={x(hovered)} y={Math.max(MARGIN.top + 40, y(active.value))} containerWidth={width}>
          <p className="mb-1 text-[11.5px] text-ink-3">{active.tooltip}</p>
          <TooltipRow swatch="bg-chart-today" label="Agent" value={format(active.value)} />
          {reference && <TooltipRow swatch="bg-chart-typical" label={reference.label} value={format(reference.value)} />}
        </ChartTooltip>
      )}
    </div>
  )
}
