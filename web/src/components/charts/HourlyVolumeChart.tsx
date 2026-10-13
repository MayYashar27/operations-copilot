import { useState } from 'react'
import type { VolumeProfile } from '../../api/types'
import { niceScale, useElementWidth } from './useElementWidth'

const HEIGHT = 220 // includes the x-axis band
const MARGIN = { top: 18, right: 8, bottom: 28, left: 30 }

/** Requests per working hour; hours above the anomaly threshold are highlighted. */
export function HourlyVolumeChart({ profile }: { profile: VolumeProfile }) {
  const [containerRef, width] = useElementWidth<HTMLDivElement>()
  const [hovered, setHovered] = useState<number | null>(null)

  const hours = profile.hours
  const plotWidth = Math.max(0, width - MARGIN.left - MARGIN.right)
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const { max, step } = niceScale(Math.max(profile.threshold, ...hours.map((h) => h.requests)) * 1.08)

  const band = hours.length ? plotWidth / hours.length : 0
  const barWidth = Math.min(24, band * 0.42)
  const y = (value: number) => MARGIN.top + plotHeight - (value / max) * plotHeight
  const ticks = Array.from({ length: Math.round(max / step) + 1 }, (_, i) => i * step)
  const shortLabels = band < 52

  const active = hovered !== null ? hours[hovered] : null

  return (
    <div ref={containerRef} className="relative" style={{ height: HEIGHT }}>
      {width > 0 && (
        <svg width={width} height={HEIGHT} role="img" aria-label="Requests per hour bar chart">
          {/* Gridlines + y ticks */}
          {ticks.map((tick) => (
            <g key={tick}>
              <line
                x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)}
                className={tick === 0 ? 'stroke-chart-axis' : 'stroke-chart-grid'} strokeWidth={1}
              />
              <text x={MARGIN.left - 8} y={y(tick)} dy="0.32em" textAnchor="end" className="fill-ink-3 text-[11px] tabular">
                {tick}
              </text>
            </g>
          ))}

          {/* Bars, rounded at the data end and anchored to the baseline */}
          {hours.map((hour, i) => {
            const x = MARGIN.left + band * i + (band - barWidth) / 2
            const top = y(hour.requests)
            const height = y(0) - top
            const r = Math.min(4, height / 2, barWidth / 2)
            const path = `M${x},${y(0)} V${top + r} Q${x},${top} ${x + r},${top} H${x + barWidth - r} Q${x + barWidth},${top} ${x + barWidth},${top + r} V${y(0)} Z`
            return (
              <path
                key={hour.hour}
                d={path}
                className={`transition-opacity ${hour.above_threshold ? 'fill-chart-highlight' : 'fill-chart-bar'}`}
                opacity={hovered === null || hovered === i ? 1 : 0.45}
              />
            )
          })}

          {/* Threshold reference line */}
          <line
            x1={MARGIN.left} x2={width - MARGIN.right}
            y1={y(profile.threshold)} y2={y(profile.threshold)}
            className="stroke-ink-3" strokeWidth={1}
          />
          <text x={width - MARGIN.right} y={y(profile.threshold) - 6} textAnchor="end" className="fill-ink-2 text-[11px] font-medium">
            Unusual ≥ {Math.ceil(profile.threshold)}
          </text>

          {/* X labels */}
          {hours.map((hour, i) => (
            <text
              key={hour.hour}
              x={MARGIN.left + band * i + band / 2}
              y={HEIGHT - 8}
              textAnchor="middle"
              className={`text-[11px] tabular ${hovered === i ? 'fill-ink' : 'fill-ink-3'}`}
            >
              {shortLabels ? hour.hour.slice(0, 2) : hour.hour.slice(0, 5)}
            </text>
          ))}

          {/* Hit targets: the full column, larger than the bar */}
          {hours.map((hour, i) => (
            <rect
              key={hour.hour}
              x={MARGIN.left + band * i} y={MARGIN.top} width={band} height={plotHeight}
              fill="transparent"
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            />
          ))}
        </svg>
      )}

      {active && hovered !== null && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-line bg-surface px-3 py-2 shadow-pop"
          style={{ left: MARGIN.left + band * hovered + band / 2, top: Math.max(y(active.requests) - 8, 40) }}
        >
          <p className="text-[11.5px] text-ink-3 tabular">{active.hour.replace('-', ' – ')}</p>
          <p className="text-[13px] font-semibold text-ink">
            {active.requests} requests
          </p>
          {active.above_threshold && <p className="text-[11.5px] font-medium text-chart-highlight-ink">Above threshold</p>}
        </div>
      )}
    </div>
  )
}
