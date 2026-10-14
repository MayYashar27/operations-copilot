import { useState } from 'react'
import type { HourlyActivity } from '../../api/types'
import { ACTIVITY_METRICS, type ActivityMetric } from './activityMetrics'
import { formatNumber } from '../../lib/format'
import { ChartTooltip, TooltipRow } from './ChartTooltip'
import { niceScale, useElementWidth } from './useElementWidth'

const HEIGHT = 264 // includes the x-axis band
const MARGIN = { top: 16, right: 12, bottom: 30, left: 34 }

/** Today's hours against the typical hour, with a crosshair and value tooltip. */
export function ShiftActivityChart({ hours, metric }: { hours: HourlyActivity[]; metric: ActivityMetric }) {
  const [containerRef, width] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<number | null>(null)
  const spec = ACTIVITY_METRICS[metric]

  const plotWidth = Math.max(0, width - MARGIN.left - MARGIN.right)
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const values = hours.flatMap((h) => [spec.today(h) ?? 0, spec.typical(h) ?? 0])
  const { max, step } = niceScale(Math.max(...values, 1) * 1.08)

  const band = hours.length ? plotWidth / hours.length : 0
  const cx = (i: number) => MARGIN.left + band * (i + 0.5)
  const y = (value: number) => MARGIN.top + plotHeight - (value / max) * plotHeight
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step)
  const barWidth = Math.min(18, band * 0.36)

  const linePath = (pick: (h: HourlyActivity) => number | null) =>
    hours
      .map((h, i) => ({ v: pick(h), i }))
      .filter((p): p is { v: number; i: number } => p.v !== null)
      .map((p, k) => `${k === 0 ? 'M' : 'L'}${cx(p.i).toFixed(1)},${y(p.v).toFixed(1)}`)
      .join(' ')

  const todayLine = linePath(spec.today)
  const areaPath = todayLine
    ? `${todayLine} L${cx(hours.length - 1).toFixed(1)},${y(0)} L${cx(0).toFixed(1)},${y(0)} Z`
    : ''
  const typicalLine = linePath(spec.typical)

  const active = hovered !== null ? hours[hovered] : null
  const fmt = (v: number | null) => (v === null ? '—' : formatNumber(v, spec.digits))

  return (
    <div ref={containerRef} className="relative select-none" style={{ height: HEIGHT }} onMouseLeave={() => setHovered(null)}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label={`${spec.label} by hour, today versus typical`}>
          {ticks.map((tick) => (
            <g key={tick}>
              <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)}
                className={tick === 0 ? 'stroke-chart-axis' : 'stroke-chart-grid'} />
              <text x={MARGIN.left - 10} y={y(tick)} dy="0.32em" textAnchor="end" className="fill-ink-3 text-[11px] tabular">
                {formatNumber(tick, step < 1 ? 1 : 0)}
              </text>
            </g>
          ))}

          {/* Crosshair column behind the marks */}
          {hovered !== null && (
            <rect x={MARGIN.left + band * hovered} y={MARGIN.top} width={band} height={plotHeight}
              className="fill-hover" />
          )}

          {spec.form === 'bar'
            ? hours.map((h, i) => {
                const value = spec.today(h) ?? 0
                const top = y(value)
                const x = cx(i) - barWidth / 2
                const r = Math.min(4, (y(0) - top) / 2, barWidth / 2)
                const d = `M${x},${y(0)} V${top + r} Q${x},${top} ${x + r},${top} H${x + barWidth - r} Q${x + barWidth},${top} ${x + barWidth},${top + r} V${y(0)} Z`
                return (
                  <path key={h.hour} style={{ d: `path('${d}')` }}
                    className={`transition-[d,opacity] duration-300 ease-out ${h.above_threshold ? 'fill-chart-unusual' : 'fill-chart-today'}`}
                    opacity={hovered === null || hovered === i ? 1 : 0.55} />
                )
              })
            : (
              <>
                <path d={areaPath} className="fill-chart-today/8" />
                <path d={todayLine} fill="none" strokeWidth={2.25} strokeLinejoin="round" strokeLinecap="round"
                  className="stroke-chart-today" />
              </>
            )}

          {/* Typical: a quiet reference line with small markers */}
          <path d={typicalLine} fill="none" strokeWidth={2} strokeLinejoin="round" className="stroke-chart-typical" />
          {hours.map((h, i) => {
            const v = spec.typical(h)
            return v === null ? null : (
              <circle key={h.hour} cx={cx(i)} cy={y(v)} r={hovered === i ? 4 : 2.75}
                className="fill-surface stroke-chart-typical transition-[r]" strokeWidth={2} />
            )
          })}

          {spec.form === 'line' && hovered !== null && spec.today(hours[hovered]) !== null && (
            <circle cx={cx(hovered)} cy={y(spec.today(hours[hovered])!)} r={4.5}
              className="fill-chart-today stroke-surface" strokeWidth={2} />
          )}

          {hours.map((h, i) => (
            <text key={h.hour} x={cx(i)} y={HEIGHT - 9} textAnchor="middle"
              className={`text-[11px] tabular ${hovered === i ? 'fill-ink font-medium' : 'fill-ink-3'}`}>
              {band < 48 ? h.hour.slice(0, 2) : h.hour.slice(0, 5)}
            </text>
          ))}

          {/* Hit targets: whole columns, much larger than the marks */}
          {hours.map((h, i) => (
            <rect key={h.hour} x={MARGIN.left + band * i} y={MARGIN.top} width={band} height={plotHeight + MARGIN.bottom}
              fill="transparent" onMouseEnter={() => setHovered(i)} />
          ))}
        </svg>
      )}

      {active && hovered !== null && (
        <ChartTooltip x={cx(hovered)} y={Math.max(MARGIN.top + 56, y(Math.max(spec.today(active) ?? 0, spec.typical(active) ?? 0)))} containerWidth={width}>
          <p className="mb-1 text-[11.5px] text-ink-3 tabular">{active.hour.replace('-', ' – ')}</p>
          <TooltipRow swatch={active.above_threshold && metric === 'requests' ? 'bg-chart-unusual' : 'bg-chart-today'}
            label="Today" value={`${fmt(spec.today(active))} ${spec.unit}`} />
          <TooltipRow swatch="bg-chart-typical" label="Typical" value={`${fmt(spec.typical(active))} ${spec.unit}`} />
          {metric === 'requests' && active.above_threshold && (
            <p className="mt-1 text-[11.5px] font-medium text-chart-unusual-ink">Unusual hour</p>
          )}
        </ChartTooltip>
      )}
    </div>
  )
}
