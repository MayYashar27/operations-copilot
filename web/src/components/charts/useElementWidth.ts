import { useLayoutEffect, useRef, useState } from 'react'

/** Track an element's width so SVG charts can draw at real pixel size. */
export function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)

  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    // Measure once immediately; the observer handles later resizes.
    setWidth(Math.floor(element.getBoundingClientRect().width))
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return [ref, width] as const
}

/** A "nice" axis maximum and tick step (1, 2, 2.5, 5 × 10^n). */
export function niceScale(maxValue: number, tickCount = 4): { max: number; step: number } {
  if (maxValue <= 0) return { max: tickCount, step: 1 }
  const rough = maxValue / tickCount
  const magnitude = 10 ** Math.floor(Math.log10(rough))
  const normalized = rough / magnitude
  const factor = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10
  const step = factor * magnitude
  return { max: Math.ceil(maxValue / step) * step, step }
}
