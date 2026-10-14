import type { ReactNode } from 'react'

interface ChartTooltipProps {
  /** Anchor point in the chart container's pixel space. */
  x: number
  y: number
  containerWidth: number
  children: ReactNode
}

/** Floating value card for charts. Flips to stay inside the container. */
export function ChartTooltip({ x, y, containerWidth, children }: ChartTooltipProps) {
  const alignRight = x > containerWidth - 170
  const alignLeft = x < 90
  const translateX = alignRight ? '-100%' : alignLeft ? '0%' : '-50%'

  return (
    <div
      role="status"
      className="pointer-events-none absolute z-10 min-w-[132px] animate-fade rounded-lg border border-line bg-surface/95 px-3 py-2 text-[12px] shadow-pop backdrop-blur"
      style={{ left: x, top: y, transform: `translate(${translateX}, calc(-100% - 10px))` }}
    >
      {children}
    </div>
  )
}

export function TooltipRow({ swatch, label, value }: { swatch?: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      {swatch && <span aria-hidden className={`size-2 shrink-0 rounded-full ${swatch}`} />}
      <span className="text-ink-2">{label}</span>
      <span className="ml-auto pl-3 font-semibold text-ink tabular">{value}</span>
    </div>
  )
}
